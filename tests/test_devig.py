"""De-vig / market derivation tests."""

from __future__ import annotations

from betforge.devig import market_from_1x2, market_from_ou, multiplicative_devig


def test_multiplicative_devig_sums_to_one():
    probs = multiplicative_devig([2.4, 3.4, 3.1])
    assert abs(sum(probs) - 1.0) < 1e-9
    assert all(p > 0 for p in probs)


def test_market_from_1x2_finite_and_coherent():
    mk = market_from_1x2([2.4, 3.4, 3.1])
    assert 0.0 <= mk.p_over15 <= 1.0
    assert 0.0 <= mk.p_btts <= 1.0
    assert 0.0 <= mk.p_home <= 1.0
    assert abs(mk.p_home + mk.p_draw + mk.p_away - 1.0) < 1e-6
    assert mk.proxy is True  # honestly labelled 1X2 proxy


def test_market_from_ou_is_not_proxy():
    mk = market_from_ou(1.6, 2.2)
    assert mk.proxy is False
    assert 0.0 <= mk.p_over15 <= 1.0
