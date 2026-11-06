"""Smoke test for the BetForge prediction entry point.

Constructs a tiny in-memory Match history (no dependence on data/matches.csv)
and asserts that models.predict runs and returns a valid probability
distribution: probabilities in (0, 1) and p_home + p_draw + p_away close to 1.
"""

from betforge.models import predict
from betforge.normalization import Match

# A tiny synthetic international-style history with a couple of team pairs.
HISTORY = [
    Match(home="Alpha", away="Bravo", home_goals=2, away_goals=1, date="2015-06-01"),
    Match(home="Bravo", away="Alpha", home_goals=0, away_goals=0, date="2015-09-01"),
    Match(home="Alpha", away="Gamma", home_goals=3, away_goals=1, date="2016-03-01"),
    Match(home="Gamma", away="Bravo", home_goals=1, away_goals=2, date="2016-07-01"),
    Match(home="Alpha", away="Bravo", home_goals=1, away_goals=1, date="2017-02-01"),
    Match(home="Delta", away="Echo", home_goals=4, away_goals=0, date="2017-05-01"),
    Match(home="Echo", away="Alpha", home_goals=0, away_goals=2, date="2018-01-01"),
]


def test_predict_runs_and_probabilities_valid():
    h, a = "Alpha", "Bravo"
    P = predict(h, a, HISTORY, rho=0.0)

    # Result distribution sums to 1.
    total = P.p_home + P.p_draw + P.p_away
    assert abs(total - 1.0) < 1e-6, f"result probs sum to {total}, want ~1"

    # Market probabilities strictly inside (0, 1).
    for field in ("p_over1_5", "p_btts"):
        val = getattr(P, field)
        assert 0.0 < val < 1.0, f"{field} = {val!r} out of (0, 1)"

    # Expected goals are positive (lambda floored at 0.02 in the model).
    assert P.expected_home > 0.0
    assert P.expected_away > 0.0

    # Sanity on identity fields.
    assert P.home == h and P.away == a


def test_predict_with_cold_team_falls_back():
    """A team with no history should still produce a valid prediction."""
    P = predict("Nobody", "Alpha", HISTORY, rho=0.0)
    assert abs(P.p_home + P.p_draw + P.p_away - 1.0) < 1e-6
    assert 0.0 < P.p_over1_5 < 1.0
    assert 0.0 < P.p_btts < 1.0
