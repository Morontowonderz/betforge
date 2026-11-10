"""Shared synthetic dataset for BetForge product tests.

Guarantees:
  * chronologically ordered matches with valid 1X2 closing odds and dates,
  * enough per-team history for the strength model to have signal,
  * deterministic (fixed seed).
"""

from __future__ import annotations

import random

import pytest

from betforge.normalization import Match


def make_odds(rng: random.Random) -> tuple[float, float, float]:
    """Realistic 1X2 decimal odds centred ~ home favourite, valid (>1.0)."""
    ph = 0.40 + rng.random() * 0.15          # 0.40..0.55
    pd = 0.24 + rng.random() * 0.05          # 0.24..0.29
    pa = max(0.22, 1.0 - ph - pd)
    probs = [ph, pd, pa]
    total = sum(probs)
    devig = [p / total for p in probs]       # margin-free, sums to 1
    margin = 1.05
    odds = [1.0 / (d * margin) for d in devig]
    # every leg must be a valid decimal odd > 1.01
    safe = tuple(o if o > 1.01 else 1.3 for o in odds)
    return safe  # type: ignore[return-value]


def build_season(matches_per_pair: int = 3, seed: int = 1) -> list[Match]:
    """Build a small round-robin league + matches with dates/odds."""
    rng = random.Random(seed)
    teams = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta"]
    out: list[Match] = []
    day = 1
    for _round in range(matches_per_pair):
        for i, home in enumerate(teams):
            for j, away in enumerate(teams):
                if i >= j:
                    continue
                ho = rng.randint(0, 3)
                ao = rng.randint(0, 3)
                odds = make_odds(rng)
                out.append(
                    Match(
                        home=home,
                        away=away,
                        home_goals=ho,
                        away_goals=ao,
                        date=f"2024-{(day % 12) + 1:02d}-{((day * 13) % 28) + 1:02d}",
                        home_odds=odds[0],
                        draw_odds=odds[1],
                        away_odds=odds[2],
                    )
                )
                day += 1
    out.sort(key=lambda m: m.date or "")
    return out


@pytest.fixture
def season():
    return build_season()


@pytest.fixture
def rules():
    from betforge.settings import AlertRule, BetforgeSettings

    settings = BetforgeSettings.from_env()
    return {
        "season": build_season(),
        "rule_list": (AlertRule(market="O1.5", min_edge_pct=1.0), AlertRule(market="BTTS", min_edge_pct=1.0)),
        "settings": settings,
        "min_edge": 1.0,
        "hard_cap": settings.hard_max_stake_frac,
    }
