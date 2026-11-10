"""Runtime settings for the BetForge product layer (paper trading / signals).

Dependency-light (stdlib + os env). Loads with production-safe defaults and
hard responsible-use caps: stake cap defaults to 1% of bankroll, hard ceiling
5%, and a daily-loss hard stop. No real-money betting path exists anywhere.

Values are read from environment (BETFORGE_*), falling back to the defaults
below, so the deployed API can be tuned without a code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        v = float(raw)
    except ValueError:
        return default
    return v if v >= 0.0 else default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AlertRule:
    """When to fire a value signal + which (mock) channels to notify."""

    market: str  # "O1.5" | "BTTS"
    min_edge_pct: float = 5.0
    min_odds: float = 1.4
    max_odds: float = 5.0
    channels: tuple[str, ...] = ("console", "db")


@dataclass(frozen=True)
class BetforgeSettings:
    """Hard caps + product knobs. Frozen => no accidental mutation of limits."""

    # ---- responsible-use hard caps ----
    starting_bankroll_ngn: int = 100_000          # paper money only
    stake_cap_frac: float = 0.01                  # 1% default max per bet
    hard_max_stake_frac: float = 0.05             # 5% absolute ceiling
    daily_loss_cap_ngn: int = 20_000              # hard daily loss stop
    responsible_notice: str = "Paper Trading Mode — Not Financial Advice."

    # ---- strategy ----
    stake_plan: str = "flat"                      # "flat" | "kelly"
    edge_threshold_pct: float = 5.0               # model - implied >= this
    auto_paper_trade: bool = True                 # signals auto-enter paper bets

    # ---- ensemble weights (normalised at use time) ----
    model_weights: dict[str, float] = field(
        default_factory=lambda: {"poisson": 0.4, "dc": 0.4, "odds": 0.2}
    )

    # ---- alert channels ----
    alert_rules: tuple[AlertRule, ...] = field(
        default_factory=lambda: (
            AlertRule(market="O1.5"),
            AlertRule(market="BTTS", min_edge_pct=6.0),
        )
    )

    @classmethod
    def from_env(cls) -> BetforgeSettings:
        return cls(
            starting_bankroll_ngn=int(_env_float("BETFORGE_BANKROLL_NGN", 100_000.0)),
            stake_cap_frac=_env_float("BETFORGE_STAKE_CAP_FRAC", 0.01),
            hard_max_stake_frac=_env_float("BETFORGE_HARD_MAX_STAKE_FRAC", 0.05),
            daily_loss_cap_ngn=int(_env_float("BETFORGE_DAILY_LOSS_CAP_NGN", 20_000.0)),
            stake_plan=os.environ.get("BETFORGE_STAKE_PLAN", "flat"),
            edge_threshold_pct=_env_float("BETFORGE_EDGE_THRESHOLD_PCT", 5.0),
            auto_paper_trade=_env_bool("BETFORGE_AUTO_PAPER_TRADE", True),
        )
