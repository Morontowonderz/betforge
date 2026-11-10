"""Tests for the Dixon-Coles baseline (Power-Method de-vig + bivariate Poisson)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from betforge import baseline as B


# --------------------------------------------------------------------------- #
# Power-Method de-vig
# --------------------------------------------------------------------------- #
def test_power_devig_sums_to_one():
    probs, k = B.power_devig([1.65, 3.3, 4.3])
    assert abs(sum(probs) - 1.0) < 1e-9
    assert all(p > 0 for p in probs)
    assert k > 0


def test_power_devig_beats_multiplicative_on_heavy_favourite():
    """A 1.10 / 4.0 / 12.0 market: the power method concentrates mass on the
    favourite and thins the longshot relative to proportional de-vig (the
    standard 'favourite-longshot bias' correction)."""
    odds = [1.10, 4.0, 12.0]
    pw, k = B.power_devig(odds)
    mp = B.multiplicative_devig(odds)
    assert k > 1.0
    assert pw[0] > mp[0]   # favourite gets more mass
    assert pw[2] < mp[2]   # longshot gets less


def test_power_devig_two_way_market():
    probs, k = B.power_devig([1.8, 3.4, 5.0])
    assert abs(sum(probs) - 1.0) < 1e-9


def test_power_devig_degenerate_falls_back():
    probs, k = B.power_devig([1.5, 3.0, float("nan")])
    assert k == 1.0
    assert abs(sum(probs) - 1.0) < 1e-9


def test_power_devig_zero_odds_falls_back():
    probs, k = B.power_devig([1.5, 3.0, 0.0])
    assert k == 1.0


# --------------------------------------------------------------------------- #
# DC matrix
# --------------------------------------------------------------------------- #
def test_dc_matrix_sums_to_one():
    J = B.dc_matrix(1.4, 1.1, -0.1)
    assert abs(J.sum() - 1.0) < 1e-9


def test_dc_matrix_nonnegative():
    J = B.dc_matrix(1.4, 1.1, -0.1)
    assert (J >= 0).all()


def test_dc_matrix_extreme_rho():
    J = B.dc_matrix(1.4, 1.1, 0.3)
    assert abs(J.sum() - 1.0) < 1e-9
    assert (J >= 0).all()


def test_dc_matrix_symmetric_lambdas():
    """Equal lambdas + rho=0 must give a symmetric matrix."""
    J = B.dc_matrix(1.3, 1.3, 0.0)
    assert np.allclose(J, J.T, atol=1e-12)


# --------------------------------------------------------------------------- #
# DC fit
# --------------------------------------------------------------------------- #
def test_fit_dc_recovers_lambdas():
    """Generate probs from a known DC model; fit must recover them.

    NOTE: (lam_h, lam_a, rho) is not uniquely identifiable from 3 market
    probabilities alone, so we assert on the recovered 1X2 probabilities
    (which is what actually matters) and on the lambdas being in range.
    """
    true = B.dc_matrix(1.6, 0.9, -0.15)
    ph, pd_, pa = B._matrix_1x2(true)
    params = B.fit_dc([ph, pd_, pa], starts=6)
    assert params.fit_rmse < 1e-3
    fitted = B.dc_matrix(params.lam_home, params.lam_away, params.rho)
    fh, fd, fa = B._matrix_1x2(fitted)
    assert abs(fh - ph) < 1e-6
    assert abs(fd - pd_) < 1e-6
    assert abs(fa - pa) < 1e-6
    # lambdas should be in a sane range even if not exactly identifiable
    assert 0.5 < params.lam_home < 3.0
    assert 0.3 < params.lam_away < 2.5


def test_fit_dc_rejects_bad_probs():
    params = B.fit_dc([0.0, 0.0, 0.0])
    assert params.method == "fallback"
    assert math.isinf(params.fit_rmse)


# --------------------------------------------------------------------------- #
# Marginalize
# --------------------------------------------------------------------------- #
def test_marginalize_probabilities_valid():
    J = B.dc_matrix(1.4, 1.1, -0.1)
    out = B.marginalize(J)
    for k in ("p_over15", "p_btts", "p_home", "p_draw", "p_away"):
        assert 0.0 < out[k] < 1.0
    assert abs(out["p_home"] + out["p_draw"] + out["p_away"] - 1.0) < 1e-9
    assert out["p_over15"] > out["p_btts"]  # over1.5 is the easier market


def test_marginalize_known_case():
    """1-0-0-1 shape: over15 = 1 - P(0,0) - P(0,1) - P(1,0)."""
    J = B.dc_matrix(1.0, 1.0, 0.0)
    out = B.marginalize(J)
    expected = 1 - J[0, 0] - J[0, 1] - J[1, 0]
    assert abs(out["p_over15"] - expected) < 1e-12


# --------------------------------------------------------------------------- #
# End-to-end
# --------------------------------------------------------------------------- #
def test_predict_from_odds_valid():
    out, params = B.predict_from_odds([1.65, 3.3, 4.3])
    assert 0 < out["p_over15"] < 1
    assert 0 < out["p_btts"] < 1
    assert params.method == "dixon-coles"
    assert params.fit_rmse < 1e-2


def test_predict_from_odds_fallback_on_missing():
    out, params = B.predict_from_odds([1.65, 3.3])
    assert params.method == "fallback"
    assert 0 < out["p_over15"] < 1


def test_predict_from_odds_heavy_favourite():
    """Heavy favourite: fitted p_home must track the de-vigged market prob."""
    odds = [1.10, 4.0, 12.0]
    out, params = B.predict_from_odds(odds)
    dv, _ = B.power_devig(odds)
    assert abs(out["p_home"] - dv[0]) < 1e-3
    assert out["p_home"] > 0.8
    assert params.fit_rmse < 1e-2


def test_predict_from_odds_does_not_raise_on_extreme():
    out, params = B.predict_from_odds([1.01, 50.0, 100.0])
    assert 0 < out["p_over15"] < 1


# --------------------------------------------------------------------------- #
# Over 2.5 (owner mandate: real O/U lines, not the O1.5 proxy)
# --------------------------------------------------------------------------- #
def test_marginalize_over25():
    J = B.dc_matrix(1.5, 1.2, -0.1)
    out = B.marginalize(J)
    assert 0.0 < out["p_over25"] < 1.0
    assert out["p_over25"] < out["p_over15"]  # O2.5 is the harder market
    # direct check: P(total >= 3)
    expected = sum(J[i, j] for i in range(J.shape[0]) for j in range(J.shape[1]) if i + j >= 3)
    assert abs(out["p_over25"] - expected) < 1e-12


def test_predict_from_ou_valid():
    out, params = B.predict_from_ou(1.67, 2.20)
    assert 0 < out["p_over25"] < 1
    assert params.method == "dixon-coles-o25"
    assert params.fit_rmse < 1e-2


def test_predict_from_ou_matches_market():
    """The DC baseline must track the de-vigged O2.5 market probability."""
    over, under = 1.67, 2.20
    out, params = B.predict_from_ou(over, under)
    market_p = (1.0 / over) / (1.0 / over + 1.0 / under)
    assert abs(out["p_over25"] - market_p) < 5e-3
    assert abs(out["p_over25_market"] - market_p) < 1e-9


def test_predict_from_ou_with_1x2_regulariser():
    out, params = B.predict_from_ou(1.67, 2.20, odds_1x2=[1.55, 3.8, 5.0])
    assert 0 < out["p_over25"] < 1
    assert abs(out["p_home"] + out["p_draw"] + out["p_away"] - 1.0) < 1e-9


def test_predict_from_ou_fallback():
    out, params = B.predict_from_ou(1.0, 2.0)
    assert params.method == "fallback"
    assert 0 < out["p_over25"] < 1


def test_fit_dc_to_over25_rejects_bad_target():
    params = B.fit_dc_to_over25(0.0)
    assert params.method == "fallback"
    params = B.fit_dc_to_over25(1.0)
    assert params.method == "fallback"


def test_predict_from_odds_rejects_single_ou_leg():
    import pytest
    with pytest.raises(ValueError):
        B.predict_from_odds([1.65, 3.3, 4.3], over25_odds=1.8)
