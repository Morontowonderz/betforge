"""Paper-trading simulator tests: ledger math + hard caps + daily loss stop."""

from __future__ import annotations

from betforge.paper import PaperTrader
from betforge.settings import BetforgeSettings


def _trader(settings: BetforgeSettings | None = None) -> PaperTrader:
    return PaperTrader(settings or BetforgeSettings.from_env())


def test_place_and_settle_win_updates_balance():
    t = _trader()
    e = t.place("A-vs-B", "O1.5", 2.0, p=0.7)
    assert e is not None
    before = t.balance
    t.settle(e, True)
    assert t.balance >= before  # won adds stake*(odds-1)
    assert e.status == "WON"


def test_ledger_math_closed_under_settlement():
    t = _trader()
    total_staked = 0.0
    for i in range(50):
        e = t.place(f"m{i}", "O1.5", 2.0 + (i % 5) * 0.1, p=0.6)
        if e is None:
            continue
        t.settle(e, i % 2 == 0)  # deterministic, but the invariant must hold
        total_staked += e.stake_ngn
    start = float(t.settings.starting_bankroll_ngn)
    sum_pnl = sum(e.profit_ngn for e in t.ledger)
    assert abs(t.balance - (start + sum_pnl)) < 1e-6  # sum(P&L) = balance change


def test_stake_cap_enforced():
    t = _trader()
    e = t.place("x", "O1.5", 3.0, p=0.99)
    assert e is not None
    cap = t.settings.hard_max_stake_frac * t.settings.starting_bankroll_ngn
    assert e.stake_ngn <= cap


def test_daily_loss_cap_halts_bets():
    settings = BetforgeSettings(starting_bankroll_ngn=100_000, daily_loss_cap_ngn=5_000, stake_cap_frac=0.04)
    t = _trader(settings)
    # hammer losing bets until the daily loss cap binds
    stopped = False
    for i in range(50):
        e = t.place(f"l{i}", "O1.5", 2.0, p=0.5)
        if e is None:
            stopped = True
            break
        t.settle(e, False)
    assert stopped  # at some point the daily-loss guardrail blocks further bets


def test_auto_paper_trade_flag_surfaces():
    s = BetforgeSettings(auto_paper_trade=False)
    t = PaperTrader(s)
    assert t.as_dict()["auto_paper_trade"] is False
