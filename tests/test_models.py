import math

import pytest

from betforge.normalization import Match, parse_match
from betforge.models import poisson_pmf, joint_goal_matrix, predict, Prediction


def test_parse_valid():
    m = parse_match(["Arsenal", "Chelsea", "2", "1"])
    assert m.home_goals == 2 and m.away_goals == 1
    assert m.total_goals == 3
    assert m.over1_5 is True
    assert m.btts is True


def test_parse_with_date():
    m = parse_match(["Arsenal", "Chelsea", "2", "1", "2026-01-01"])
    assert m.date == "2026-01-01"


@pytest.mark.parametrize(
    "row",
    [
        ["Arsenal"],  # too few columns
        ["", "Chelsea", "2", "1"],  # empty home
        ["A", "B", "x", "1"],  # non-integer
        ["A", "B", "-1", "1"],  # negative
    ],
)
def test_parse_rejects_invalid(row):
    with pytest.raises(ValueError):
        parse_match(row)


def test_over1_5_and_btts_flags():
    assert Match("A", "B", 1, 1).over1_5 is True  # total 2
    assert Match("A", "B", 1, 0).over1_5 is False  # total 1
    assert Match("A", "B", 1, 1).btts is True
    assert Match("A", "B", 3, 0).btts is False
    assert Match("A", "B", 0, 0).btts is False


def test_poisson_pmf_mass():
    # sum of pmf over plausible range ~ 1
    s = sum(poisson_pmf(k, 1.5) for k in range(20))
    assert s == pytest.approx(1.0, abs=1e-9)


def test_joint_matrix_normalized():
    mat = joint_goal_matrix(1.5, 1.3)
    total = sum(sum(r) for r in mat)
    assert total == pytest.approx(1.0, abs=1e-6)
    assert all(v >= 0 for r in mat for v in r)


def test_predict_expresses_markets():
    # Dominant team vs weak team -> home favoured, but Over1.5 likely
    matches = []
    for _ in range(30):
        matches.append(Match("Strong", "Weak", 3, 0))
    p = predict("Strong", "Weak", matches)
    assert isinstance(p, Prediction)
    assert p.p_over1_5 > 0.5  # 3-0 repeatedly => many goals
    assert p.p_home > p.p_away


def test_predict_low_scoring_league():
    # 0-0 and 0-1-heavy league => Over1.5 should be modest
    matches = []
    for _ in range(40):
        matches.append(Match("A", "B", 0, 0))
    p = predict("A", "B", matches)
    assert p.p_over1_5 < 0.6


def test_predict_unknown_teams_reasonable():
    # No history: falls back gracefully, probabilities must be a valid distribution
    matches = [Match("X", "Y", 2, 1) for _ in range(20)]
    p = predict("Nope", "Nobody", matches)
    s = p.p_home + p.p_draw + p.p_away
    assert s == pytest.approx(1.0, abs=1e-6)
    assert 0.0 < p.p_over1_5 < 1.0
