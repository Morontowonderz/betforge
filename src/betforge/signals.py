"""Value-signal generation + mock alert adapters.

A signal fires when the ensemble's probability for a market beats the
de-vigged market implied probability by at least AlertRule.min_edge_pct AND
the odds fall within [min_odds, max_odds]. Each signal carries a ₦ stake
recommendation (flat cap by default, quarter-Kelly when enabled).

Responsible-use: the recommendation is capped to the configured 1% default
and never exceeds the 5% hard ceiling. Alerts go to MOCK channels only
(console + in-memory DB log) — there is deliberately no real-money or
third-party send path in this product.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .devig import market_from_1x2
from .models_engine import EnsembleResult, ensemble
from .normalization import Match
from .settings import AlertRule, BetforgeSettings
from .staking import kelly_fraction


@dataclass(frozen=True)
class Signal:
    fixture: str
    market: str
    model_p: float
    implied_p: float
    odds: float
    edge_pct: float
    stake_ngn: float
    confidence: str  # LOW/MEDIUM/HIGH
    status: str = "PENDING"  # PENDING/WON/LOST/VOID
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> dict[str, float | str]:
        return {
            "fixture": self.fixture,
            "market": self.market,
            "model_p": round(self.model_p, 4),
            "implied_p": round(self.implied_p, 4),
            "odds": round(self.odds, 3),
            "edge_pct": round(self.edge_pct, 2),
            "stake_ngn": round(self.stake_ngn, 2),
            "confidence": self.confidence,
            "status": self.status,
        }


class MockAlertBus:
    """In-memory alert sink (console + list) so tests/dashboard see the events."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def notify(self, channel: str, signal: Signal) -> dict[str, object]:
        event = {
            "channel": channel,
            "fixture": signal.fixture,
            "market": signal.market,
            "edge_pct": signal.edge_pct,
            "stake_ngn": signal.stake_ngn,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self.events.append(event)
        if channel == "console":
            print(f"[mock-alert:{channel}] {signal.fixture} {signal.market} edge={signal.edge_pct:.2f}% stake=₦{signal.stake_ngn:.2f}")
        return event


def _confidence(edge_pct: float) -> str:
    if edge_pct >= 10:
        return "HIGH"
    if edge_pct >= 7:
        return "MEDIUM"
    return "LOW"


def detect_signals(
    matches: Sequence[Match],
    *,
    rules: Sequence[AlertRule],
    settings: BetforgeSettings | None = None,
    history: Sequence[Match] | None = None,
) -> tuple[list[Signal], EnsembleResult | None]:
    """Evaluate upcoming/backtest fixtures against the alert rules.

    `history` (strict pre-kickoff) is used for the model when given so this
    also works on settled matches (the backtest path). When a match has no
    odds it is skipped. Returns signals filtered by edge+odds bounds.
    """
    settings = settings or BetforgeSettings.from_env()
    signals: list[Signal] = []
    last_ensemble: EnsembleResult | None = None
    for m in matches:
        prior = history if history is not None else []
        result = ensemble(m.home, m.away, prior)
        last_ensemble = result
        for rule in rules:
            market = rule.market
            model_p = result.p_over15 if market == "O1.5" else result.p_btts
            if not _has_odds(m):
                continue
            odds = _signal_odds(m, market)
            if odds is None or not (rule.min_odds <= odds <= rule.max_odds):
                continue
            implied = market_from_1x2([m.home_odds, m.draw_odds, m.away_odds])
            implied_p = implied.p_over15 if market == "O1.5" else implied.p_btts
            edge = (model_p - implied_p) * 100.0
            if edge >= rule.min_edge_pct:
                stake = _stake(settings, model_p, odds)
                signals.append(
                    Signal(
                        fixture=f"{m.home} vs {m.away}",
                        market=market,
                        model_p=model_p,
                        implied_p=implied_p,
                        odds=odds,
                        edge_pct=edge,
                        stake_ngn=stake,
                        confidence=_confidence(edge),
                    )
                )
    return signals, last_ensemble


def _stake(settings: BetforgeSettings, p: float, odds: float) -> float:
    if settings.stake_plan == "kelly":
        frac = kelly_fraction(p, odds)
        if frac <= 0:
            return 0.0
        frac = min(frac, settings.hard_max_stake_frac)
        return frac * settings.starting_bankroll_ngn
    frac = min(settings.stake_cap_frac, settings.hard_max_stake_frac)
    return frac * settings.starting_bankroll_ngn


def _has_odds(m: Match) -> bool:
    return all(o != float("inf") and o is not None for o in (m.home_odds, m.draw_odds, m.away_odds))


def _signal_odds(m: Match, market: str) -> float | None:
    from .backtest import _market_odds  # reuse the backtest's stand-in price

    return _market_odds(m, market)
