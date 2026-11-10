"""Minute-7 in-play hypothesis research module (paper/research only).

Hypothesis under test (documented, then tested — not assumed):

    H1: Matches in which at least one goal is scored by minute 7 (<=7') are
        MORE likely to finish Over 1.5 goals than matches without an early
        goal.

Null: the Over-1.5 outcome probability does NOT differ between the early
goal group and the no-early-goal group.

Data: a mock minute-by-minute generator simulates full matches from Poisson
goal rates with realistic goal minutes. The module reports the observed
proportions, a two-proportion z-test p-value, effect size, a 95% confidence
interval and a SUPPORTED / NOT SUPPORTED / INCONCLUSIVE conclusion. The
`simulated: true` flag is always surfaced — this is research-grade mock
evidence, never a claim about real in-play odds.

No real-money bets are placed; any emergent "experimental strategy" is
stake-capped at 0.5% of bankroll and labelled experimental (see README).
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

MIN7 = 7


@dataclass(frozen=True)
class LiveMatch:
    """A simulated live match with per-team goal minutes (1..90)."""

    home: str
    away: str
    home_goals_minutes: tuple[int, ...]
    away_goals_minutes: tuple[int, ...]

    @property
    def early_goal(self) -> bool:
        return any(g <= MIN7 for g in self.home_goals_minutes) or any(g <= MIN7 for g in self.away_goals_minutes)

    @property
    def total_goals(self) -> int:
        return len(self.home_goals_minutes) + len(self.away_goals_minutes)

    @property
    def over15(self) -> bool:
        return self.total_goals >= 2


def gen_goal_minutes(rate: float, *, rng: random.Random,
                     within_90: bool = True) -> tuple[int, ...]:
    """Draw a Poisson number of goals, each at a random minute 1..90."""
    lam = max(rate, 0.0)
    # Poisson draw (stdlib)
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        p *= rng.random()
        if p <= L:
            break
        k += 1
    if k == 0:
        return ()
    mins = sorted((1 + rng.randint(0, 89)) for _ in range(k))
    return tuple(mins)


def simulate_matches(home: str, away: str, n: int, *, lam_home: float = 1.5,
                     lam_away: float = 1.2, seed: int = 7) -> list[LiveMatch]:
    """Generate `n` full simulated live matches with realistic goal minutes."""
    rng = random.Random(seed)
    out: list[LiveMatch] = []
    for _ in range(n):
        h = gen_goal_minutes(lam_home, rng=rng)
        a = gen_goal_minutes(lam_away, rng=rng)
        out.append(LiveMatch(home=home, away=away, home_goals_minutes=h, away_goals_minutes=a))
    return out


def _ztest_two_proportions(p1: float, n1: int, p2: float, n2: int) -> float:
    """Two-proportion pooled z-test -> one-tailed p-value (normal approx)."""
    if n1 == 0 or n2 == 0:
        return 1.0
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se <= 0:
        return 1.0
    z = (p1 - p2) / se
    # stdlib-normal CDF via the math.erf builtin
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return max(0.0, min(1.0, 1.0 - cdf))  # one-tailed


@dataclass(frozen=True)
class ResearchReport:
    sample: int
    early_n: int
    no_early_n: int
    over15_early: float
    over15_no_early: float
    p_value: float
    effect_size: float  # absolute risk difference (early - no_early)
    ci_low: float
    ci_high: float
    conclusion: str
    simulated: bool = True

    def as_dict(self) -> dict:
        return {
            "sample": self.sample,
            "early_goal_n": self.early_n,
            "no_early_goal_n": self.no_early_n,
            "over15_early_pct": round(self.over15_early * 100, 2),
            "over15_no_early_pct": round(self.over15_no_early * 100, 2),
            "p_value": round(self.p_value, 4),
            "effect_size": round(self.effect_size, 4),
            "ci_95": [round(self.ci_low, 4), round(self.ci_high, 4)],
            "conclusion": self.conclusion,
            "simulated": self.simulated,
        }


def run_hypothesis_test(matches: Sequence[LiveMatch], *, alpha: float = 0.05) -> ResearchReport:
    """Run the two-proportion hypothesis test and return a research report."""
    early = [m for m in matches if m.early_goal]
    no_early = [m for m in matches if not m.early_goal]
    n_e, n_n = len(early), len(no_early)
    p_e = sum(1 for m in early if m.over15) / n_e if n_e else 0.0
    p_n = sum(1 for m in no_early if m.over15) / n_n if n_n else 0.0
    p_value = _ztest_two_proportions(p_e, n_e, p_n, n_n)
    effect = p_e - p_n
    se_diff = math.sqrt(max(p_e * (1 - p_e) / max(n_e, 1) + p_n * (1 - p_n) / max(n_n, 1), 0.0))
    ci_low = effect - 1.96 * se_diff
    ci_high = effect + 1.96 * se_diff
    if p_value >= alpha or abs(effect) < 0.02 or (n_e < 30 or n_n < 30):
        conclusion = "INCONCLUSIVE"
    elif p_value < alpha and effect > 0:
        conclusion = "SUPPORTED"
    else:
        conclusion = "NOT SUPPORTED"
    # Override with honesty when simulated markets mean the p-value is mock evidence
    if conclusion == "SUPPORTED":
        conclusion = "SUPPORTED (simulated)"
    return ResearchReport(
        sample=len(matches),
        early_n=n_e,
        no_early_n=n_n,
        over15_early=p_e,
        over15_no_early=p_n,
        p_value=p_value,
        effect_size=effect,
        ci_low=ci_low,
        ci_high=ci_high,
        conclusion=conclusion,
    )


def goal_minute_distribution(matches: Sequence[LiveMatch]) -> dict[str, int]:
    """Bucket all goal minutes into ten 9-minute buckets (research chart input)."""
    buckets = {f"{i*9+1}-{min(90,(i+1)*9)}": 0 for i in range(10)}
    for m in matches:
        for g in list(m.home_goals_minutes) + list(m.away_goals_minutes):
            idx = min(9, (g - 1) // 9)
            bucket = list(buckets)[idx]
            buckets[bucket] += 1
    return buckets
