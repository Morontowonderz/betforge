"""Model-engine tests: probabilities valid, ensemble blends, ML fallback honest."""

from __future__ import annotations

from betforge.models_engine import MLModel, ensemble

import betforge.normalization as nm


def _two_match_history() -> list[nm.Match]:
    return [
        nm.Match("A", "B", 2, 1, "2024-01-01"),
        nm.Match("A", "C", 1, 3, "2024-01-08"),
    ]


def test_ensemble_probs_in_unit_interval():
    r = ensemble("A", "B", _two_match_history())
    assert 0.0 <= r.p_over15 <= 1.0
    assert 0.0 <= r.p_btts <= 1.0
    assert len(r.components) >= 2


def test_ensemble_components_are_labelled():
    r = ensemble("A", "B", _two_match_history())
    names = {c.name for c in r.components}
    assert {"poisson", "dixon-coles"} <= names  # ML present only if sklearn


def test_ml_fallback_never_raises():
    ml = MLModel()
    model = ml  # train not called -> available False
    assert model.available is False
    r = ensemble("A", "B", _two_match_history(), ml=ml, ml_feature_row={"home_played": 2, "home_gf_avg": 1.5, "home_over15_rate": 0.5})
    assert 0.0 <= r.p_over15 <= 1.0


def test_empty_history_returns_valid_distribution():
    r = ensemble("UnknownHome", "UnknownAway", [])
    assert 0.0 <= r.p_over15 <= 1.0
    assert 0.0 <= r.p_btts <= 1.0
