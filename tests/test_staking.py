"""Tests for Quarter-Kelly staking (0.25 Kelly, hard 2% cap, CLV gate)."""

from __future__ import annotations

from betforge import staking as S


def test_kelly_fraction_basic():
    # p=0.6, odds=2.0 -> b=1.0, f=(0.6*1-0.4)/1=0.2
    assert abs(S.kelly_fraction(0.6, 2.0) - 0.2) < 1e-12


def test_kelly_fraction_no_edge():
    # p=0.5 at odds=2.0 is break-even -> 0
    assert S.kelly_fraction(0.5, 2.0) == 0.0
    # p below break-even -> 0 (never negative)
    assert S.kelly_fraction(0.4, 2.0) == 0.0


def test_kelly_fraction_invalid_inputs():
    assert S.kelly_fraction(0.0, 2.0) == 0.0
    assert S.kelly_fraction(1.0, 2.0) == 0.0
    assert S.kelly_fraction(0.6, 1.0) == 0.0
    assert S.kelly_fraction(0.6, 0.5) == 0.0


def test_stake_quarter_kelly():
    # full kelly 0.2 -> quarter 0.05, but 2% cap binds -> 0.02
    st = S.stake(0.6, 2.0, clv_positive=True)
    assert abs(st.full_kelly - 0.2) < 1e-9
    assert abs(st.fraction - 0.02) < 1e-12
    assert st.clamped is True


def test_stake_below_cap():
    # small edge: p=0.55, odds=2.0 -> b=1, f=(0.55-0.45)/1=0.1 -> quarter 0.025 -> cap 0.02
    st = S.stake(0.55, 2.0, clv_positive=True)
    assert st.clamped is True
    assert abs(st.fraction - 0.02) < 1e-12
    # tiny edge: p=0.51 -> f=0.02 -> quarter 0.005 -> below cap
    st2 = S.stake(0.51, 2.0, clv_positive=True)
    assert st2.clamped is False
    assert abs(st2.fraction - 0.005) < 1e-12


def test_stake_clv_gate_closed_by_default():
    """Without positive CLV the stake must be exactly 0 (no bet)."""
    st = S.stake(0.6, 2.0)
    assert st.fraction == 0.0
    assert st.full_kelly == 0.0


def test_stake_clv_gate_explicitly_closed():
    st = S.stake(0.6, 2.0, clv_positive=False)
    assert st.fraction == 0.0


def test_stake_no_edge():
    st = S.stake(0.5, 2.0, clv_positive=True)
    assert st.fraction == 0.0


def test_stake_bankroll_scaling():
    st = S.stake(0.6, 2.0, bankroll=1000.0, clv_positive=True)
    assert abs(st.fraction - 0.02) < 1e-12
    assert abs(st.fraction * 1000.0 - 20.0) < 1e-9


def test_clv_positive_drift():
    # model prob rose on wins, fell on losses -> positive CLV
    open_ = [0.50, 0.50]
    close = [0.60, 0.40]
    outcome = [1, 0]
    v = S.clv(open_, close, outcome)
    assert v > 0


def test_clv_negative_drift():
    open_ = [0.50, 0.50]
    close = [0.40, 0.60]
    outcome = [1, 0]
    v = S.clv(open_, close, outcome)
    assert v < 0


def test_clv_mismatched_lengths():
    import pytest
    with pytest.raises(ValueError):
        S.clv([0.5], [0.6, 0.7], [1])
