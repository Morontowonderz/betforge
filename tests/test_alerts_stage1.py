"""Alert adapters (mock fallback) + two-stage λ model tests."""

from __future__ import annotations

from betforge.models_engine import Stage1Lambdas
from betforge.signals import MockAlertBus, Signal


def _sig():
    return Signal(fixture="A vs B", market="O2.5", model_p=0.6, implied_p=0.5, odds=1.9, edge_pct=10.0, stake_ngn=1000.0, confidence="MEDIUM")


def test_alert_bus_mock_when_no_env(monkeypatch):
    bus = MockAlertBus()
    ev = bus.notify("telegram", _sig())  # no TELEGRAM_* env -> mock, no network
    assert ev["delivered"] == "log(mock)"
    assert bus.events and bus.events[0]["channel"] == "telegram"
    # console path records + prints
    ev2 = bus.notify("console", _sig())
    assert ev2["channel"] == "console"


def test_alert_bus_recaps_delivered_flag(monkeypatch):
    bus = MockAlertBus()
    ev = bus.notify("termii", _sig())
    assert ev["delivered"] == "log(mock)"


def _synthetic_rows(n: int):
    import random

    rng = random.Random(1)
    rows = []
    lam_h, lam_a = [], []
    for i in range(n):
        rows.append({"home_played": 5 + (i % 3), "home_gf_avg": 1.2 + (i % 10) * 0.05, "away_played": 4, "away_gf_avg": 1.0, "home_ga_avg": 0.9, "away_ga_avg": 1.1, "home_btts_rate": 0.5, "away_btts_rate": 0.45})
        lam_h.append(1.3 + rng.random() * 0.4)
        lam_a.append(1.0 + rng.random() * 0.4)
    return rows, lam_h, lam_a


def test_stage1_lambdas_fit_and_predict_unit_interval():
    model = Stage1Lambdas(min_samples=40)
    rows, lh, la = _synthetic_rows(200)
    fitted = model.fit(rows, lh, la)
    # Either fitted (sklearn present) or cleanly unavailable; probs must be sane in both cases
    p = model.predict(rows[0])
    assert 0.0 <= p.p_over25 <= 1.0
    # p_over25 <= p_over15 (monotonic total)
    assert p.p_over25 <= p.p_over15 + 1e-9
