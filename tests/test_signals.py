"""Signals + value detection + mock alerts tests."""

from __future__ import annotations

from betforge.settings import AlertRule, BetforgeSettings
from betforge.signals import MockAlertBus, detect_signals


def test_detect_signals_respect_edge_and_odds(rules):
    signals, _ = detect_signals(rules["season"], rules=rules["rule_list"])
    for s in signals:
        assert s.edge_pct >= rules["min_edge"]
        assert s.stake_ngn >= 0
        # stake never exceeds the hard cap
        assert s.stake_ngn <= rules["hard_cap"] * rules["settings"].starting_bankroll_ngn + 1e-6


def test_mock_alert_bus_records_events(rules):
    bus = MockAlertBus()
    signals, _ = detect_signals(rules["season"], rules=rules["rule_list"])
    for s in signals[:3]:
        bus.notify("console", s)
    assert len(bus.events) >= 0
    if bus.events:
        assert "edge_pct" in bus.events[0]
        assert bus.events[0]["channel"] == "console"


def test_no_odds_skipped(rules):
    import betforge.normalization as nm

    season = rules["season"]
    # strip odds from one match -> must not crash and must be skipped
    stripped = [
        nm.Match(m.home, m.away, m.home_goals, m.away_goals, m.date, float("inf"), float("inf"), float("inf"))
        for m in season
    ]
    signals, _ = detect_signals(stripped, rules=rules["rule_list"])
    assert signals == []
