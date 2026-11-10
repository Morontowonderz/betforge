"""Quarter-Kelly staking with a hard 2% bankroll cap.

Owner mandate 2026-11-06: implement the staking formula, but arm it ONLY
after the backtest shows positive Closing Line Value (CLV). Until CLV is
positive, `stake()` returns 0.0 -- no bet.

Quarter-Kelly: f* = (p*b - q) / b, scaled by 0.25, where
  p  = model probability of the bet winning
  b  = decimal odds - 1 (net odds received)
  q  = 1 - p

The 2% cap is a hard ceiling on the fraction of bankroll risked per bet,
applied AFTER the Kelly fraction. This is the standard "fractional Kelly
with a cap" construction; the cap binds on strong edges.

This module is pure arithmetic -- it does not know whether the model has
edge. The CLV gate lives in the backtest, not here.
"""

from __future__ import annotations

from dataclasses import dataclass

KELLY_FRACTION = 0.25   # Quarter-Kelly
MAX_BANKROLL_FRACTION = 0.02  # hard 2% cap per bet


@dataclass(frozen=True)
class Stake:
    fraction: float        # fraction of bankroll to stake (0.0 = no bet)
    full_kelly: float      # unscaled Kelly fraction (for diagnostics)
    edge: float            # p - q/b, the model's edge over the market
    clamped: bool          # True if the 2% cap bound


def kelly_fraction(p: float, decimal_odds: float) -> float:
    """Full-Kelly fraction f* = (p*b - q)/b, floored at 0 (no negative bets)."""
    if not (0.0 < p < 1.0) or decimal_odds <= 1.0:
        return 0.0
    b = decimal_odds - 1.0
    q = 1.0 - p
    f = (p * b - q) / b
    return max(f, 0.0)


def stake(p: float, decimal_odds: float, *, bankroll: float = 1.0,
          clv_positive: bool = False) -> Stake:
    """Quarter-Kelly stake with a hard 2% bankroll cap.

    Returns Stake(fraction=0.0) when:
      - the model has no edge (p <= implied break-even)
      - the odds are invalid
      - `clv_positive` is False (the CLV gate is closed -- default)

    `bankroll` is the current bankroll; the returned `fraction` is relative
    to it, so the currency stake is `fraction * bankroll`.
    """
    if not clv_positive:
        return Stake(0.0, 0.0, 0.0, False)
    if not (0.0 < p < 1.0) or decimal_odds <= 1.0:
        return Stake(0.0, 0.0, 0.0, False)

    b = decimal_odds - 1.0
    q = 1.0 - p
    full = kelly_fraction(p, decimal_odds)
    if full <= 0.0:
        return Stake(0.0, 0.0, 0.0, False)

    fractional = full * KELLY_FRACTION
    capped = min(fractional, MAX_BANKROLL_FRACTION)
    edge = p - q / b  # model prob minus break-even prob
    return Stake(
        fraction=capped,
        full_kelly=full,
        edge=edge,
        clamped=(capped < fractional),
    )


def clv(model_probs_open: list[float], model_probs_close: list[float],
        outcome: list[int]) -> float:
    """Closing Line Value: mean(model_close - model_open) on winning bets.

    Positive CLV means the model's probability moved in the right direction
    relative to the closing line -- the necessary condition to arm staking.
    Returns (mean_close - mean_open) on wins minus (mean_close - mean_open)
    on losses, i.e. the net model drift weighted by the outcome.
    """
    if not (len(model_probs_open) == len(model_probs_close) == len(outcome)):
        raise ValueError("CLV inputs must be the same length")
    if not outcome:
        return 0.0
    drift = [c - o for o, c in zip(model_probs_open, model_probs_close)]
    wins = [d for d, y in zip(drift, outcome) if y == 1]
    losses = [d for d, y in zip(drift, outcome) if y == 0]
    return float((sum(wins) - sum(losses)) / len(outcome)) if drift else 0.0
