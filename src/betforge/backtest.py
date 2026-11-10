"""Event-driven backtesting engine with STRICT no-lookahead discipline.

For each historical match (chronological order):
   1. Build model features ONLY from matches that finished before kickoff.
   2. Compute the ensemble probabilities.
   3. Compare against the de-vigged market (the match's own pre-match closing
      line) -> edge. If edge >= threshold and odds within bounds -> bet.
   4. Stake (flat % of bankroll, capped) or quarter-Kelly (CLV-gated).
   5. Settle on the actual full-time result; update bankroll.

The engine never reads the target match's result (or any future match) while
computing features or the bet decision — the anti-cheat test randomises the
label order and asserts the edge approximately vanishes (a leakage-free
model cannot profit off random labels).

Responsible-use: default stub uses flat 1% of bankroll, never more than 5%
(hard cap). This is analysis only; no real bet is ever placed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import mean

from .devig import market_from_1x2
from .features import chrono_sort
from .models_engine import EnsembleResult, ensemble
from .normalization import Match
from .staking import kelly_fraction

# market targets BetForge bets on
O15 = "O1.5"
BTTS = "BTTS"


@dataclass(frozen=True)
class Strategy:
    name: str
    market: str  # O1.5 | BTTS
    edge_threshold_pct: float = 5.0
    min_odds: float = 1.4
    max_odds: float = 5.0
    stake_plan: str = "flat"  # flat | kelly
    stake_cap_frac: float = 0.01  # 1% default
    hard_max_frac: float = 0.05  # absolute ceiling


@dataclass(frozen=True)
class Bet:
    index: int
    home: str
    away: str
    date: str | None
    market: str
    model_p: float
    odds: float
    implied_p: float
    edge_pct: float
    stake_ngn: float
    status: str = "PENDING"  # PENDING/WON/LOST/VOID
    profit_ngn: float = 0.0


@dataclass
class BacktestRun:
    strategy: Strategy
    start_bankroll: float
    end_bankroll: float
    bets: list[Bet] = field(default_factory=list)
    profit_curve: list[float] = field(default_factory=list)

    def win_rate(self) -> float:
        s = [b for b in self.bets if b.status in ("WON", "LOST")]
        return (sum(1 for b in s if b.status == "WON") / len(s)) if s else 0.0

    def roi(self) -> float:
        invested = sum(b.stake_ngn for b in self.bets)
        net = self.end_bankroll - self.start_bankroll
        return (net / invested) if invested > 0 else 0.0

    def avg_odds(self) -> float:
        return mean(b.odds for b in self.bets) if self.bets else 0.0

    def max_drawdown(self) -> float:
        peak = self.start_bankroll
        mdd = 0.0
        for v in self.profit_curve:
            peak = max(peak, v)
            if peak > 0:
                mdd = max(mdd, (peak - v) / peak)
        return mdd

    def longest_losing_streak(self) -> int:
        cur = best = 0
        for b in self.bets:
            if b.status == "LOST":
                cur += 1
                best = max(best, cur)
            elif b.status == "WON":
                cur = 0
        return best

    def sharpe(self) -> float:
        rets = [b.profit_ngn for b in self.bets]
        if len(rets) < 2:
            return 0.0
        m = mean(rets)
        sd = (sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5
        return (m / sd) if sd > 0 else 0.0

    def calmar(self) -> float:
        annual = self.end_bankroll - self.start_bankroll
        return (annual / self.max_drawdown()) if self.max_drawdown() > 0 else 0.0

    def metrics(self) -> dict[str, float | int]:
        return {
            "total_bets": len(self.bets),
            "win_rate": round(self.win_rate(), 4),
            "roi": round(self.roi(), 4),
            "net_profit_ngn": round(self.end_bankroll - self.start_bankroll, 2),
            "avg_odds": round(self.avg_odds(), 3),
            "max_drawdown_pct": round(self.max_drawdown(), 4),
            "longest_losing_streak": self.longest_losing_streak(),
            "sharpe": round(self.sharpe(), 4),
            "calmar": round(self.calmar(), 4),
        }


def _market_prob(ensemble_result: EnsembleResult, market: str) -> float:
    return ensemble_result.p_over15 if market == O15 else ensemble_result.p_btts


def _settled(match: Match, market: str) -> str:
    if market == O15:
        return "WON" if match.over1_5 else "LOST"
    return "WON" if match.btts else "LOST"


def run_backtest(
    matches: Sequence[Match],
    *,
    strategy: Strategy,
    start_bankroll: float = 100_000.0,
) -> BacktestRun:
    """Iterate matches chronologically; never look ahead; settle each bet."""
    ordered = chrono_sort(matches)
    run = BacktestRun(strategy=strategy, start_bankroll=start_bankroll, end_bankroll=start_bankroll)
    bankroll = start_bankroll
    curve: list[float] = []
    history: list[Match] = []

    for idx, m in enumerate(ordered):
        # 1) model on the strict past (history grows by exactly this match's FINAL result later)
        result = ensemble(m.home, m.away, history)
        model_p = _market_prob(result, strategy.market)

        # 2) market from the match's OWN pre-match closing line (fair, pre-kickoff)
        has_odds = _has_odds(m)
        if not has_odds:
            history.append(m)
            continue
        odds_value = _market_odds(m, strategy.market)
        if odds_value is None or not (strategy.min_odds <= odds_value <= strategy.max_odds):
            history.append(m)
            continue
        implied = _implied(m, strategy.market)
        edge = (model_p - implied) * 100.0

        # 3) bet decision
        if edge >= strategy.edge_threshold_pct:
            stake = _stake_ngn(strategy, model_p, odds_value, bankroll)
            if stake > 0:
                status = _settled(m, strategy.market)
                raw_profit = (stake * (odds_value - 1.0)) if status == "WON" else -stake
                profit_ngn = round(raw_profit, 2)  # exact accounting amount
                bankroll += profit_ngn
                run.bets.append(
                    Bet(
                        index=idx,
                        home=m.home,
                        away=m.away,
                        date=m.date,
                        market=strategy.market,
                        model_p=model_p,
                        odds=odds_value,
                        implied_p=implied,
                        edge_pct=round(edge, 2),
                        stake_ngn=round(stake, 2),
                        status=status,
                        profit_ngn=profit_ngn,
                    )
                )

        # 4) record the outcome BEFORE the next match (the only allowed advance)
        history.append(m)
        if run.bets:
            curve.append(bankroll)

    run.end_bankroll = bankroll
    run.profit_curve = curve
    return run


def _has_odds(m: Match) -> bool:
    return all(o != float("inf") and o is not None for o in (m.home_odds, m.draw_odds, m.away_odds))


def _market_odds(m: Match, market: str) -> float | None:
    # 1X2-only data: we use the draw-adjusted average of the two relevant
    # outcomes as a stand-in closing price for a two-way market proxy.
    if market == O15:
        inv = [1.0 / m.home_odds, 1.0 / m.draw_odds, 1.0 / m.away_odds]
        return float(1.0 / (sum(inv) / 3))
    btts_inv = 0.5 * (1.0 / m.home_odds + 1.0 / m.away_odds)
    return float(1.0 / btts_inv) if btts_inv > 0 else None


def _implied(m: Match, market: str) -> float:
    mkt = market_from_1x2([m.home_odds, m.draw_odds, m.away_odds])
    return mkt.p_over15 if market == O15 else mkt.p_btts


def _stake_ngn(strategy: Strategy, p: float, odds: float, bankroll: float) -> float:
    if strategy.stake_plan == "kelly":
        frac = kelly_fraction(p, odds)
        if frac <= 0:
            return 0.0
        frac = min(frac, strategy.hard_max_frac)
        return frac * bankroll
    # flat: stake_cap_frac of bankroll, but never more than the hard cap
    frac = min(strategy.stake_cap_frac, strategy.hard_max_frac)
    return frac * bankroll


# ---- anti-cheat helper: randomized-label control (edge must vanish) ----
def edge_on_random_labels(matches: Sequence[Match], strategy: Strategy) -> float:
    """Run a backtest where every outcome (goals) is randomised.

    A leakage-free process has no predictive link to random outcomes, so the
    realised ROI must collapse toward 0. Shuffling order alone would NOT do
    this (true odds stay paired with their own results); randomising the
    labels truly decouples features from outcomes.
    """
    import random

    rng = random.Random(0)
    randomized = [
        Match(
            home=m.home,
            away=m.away,
            home_goals=rng.randint(0, 3),
            away_goals=rng.randint(0, 3),
            date=m.date,
            home_odds=m.home_odds,
            draw_odds=m.draw_odds,
            away_odds=m.away_odds,
        )
        for m in matches
    ]
    run = run_backtest(randomized, strategy=strategy)
    return round(run.roi(), 4)
