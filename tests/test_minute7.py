"""Minute-7 research module tests: statistical test + report validity."""

from __future__ import annotations

from betforge.minute7 import (
    goal_minute_distribution,
    simulate_matches,
    run_hypothesis_test,
)


def test_report_shape_and_mock_presence():
    matches = simulate_matches("Alpha", "Beta", 120, lam_home=1.4, lam_away=1.2, seed=7)
    report = run_hypothesis_test(matches, alpha=0.05)
    d = report.as_dict()
    assert d["simulated"] is True
    assert 0.0 <= d["p_value"] <= 1.0
    assert d["conclusion"] in ("SUPPORTED (simulated)", "NOT SUPPORTED", "INCONCLUSIVE")
    assert d["sample"] == 120
    assert abs(d["effect_size"]) <= 1.0


def test_goal_distribution_buckets_sum():
    matches = simulate_matches("A", "B", 50, seed=1)
    dist = goal_minute_distribution(matches)
    total_bucketed = sum(dist.values())
    total_goals = sum(len(m.home_goals_minutes) + len(m.away_goals_minutes) for m in matches)
    assert total_bucketed == total_goals
    assert len(dist) == 10
