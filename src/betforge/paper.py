"""Paper-trading simulator: bankroll, ledger, settlement, hard caps.

Every signal (when AUTO_PAPER_TRADE) places a paper bet: stake deducted on
entry, settled against the real match result. Balance, bankroll curve and
P&L are tracked in-memory (a DB-backed persistence layer is a production
swap; mock persists to a caller-provided sink for the dashboard).

Responsible-use hard stops implemented HERE:
  * stake cap defaults to 1% of bankroll, absolute ceiling 5%;
  * a daily-loss cap halts further paper bets for the day once breached;
  * there is NO real-money API anywhere in this product.

All amounts are Nigerian Naira (₦); paper money only.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from .settings import BetforgeSettings


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PaperLedgerEntry:
    signal_key: str
    market: str
    odds: float
    stake_ngn: float
    status: str = "PENDING"  # PENDING/WON/LOST/VOID
    profit_ngn: float = 0.0
    placed_at: str = field(default_factory=_utcnow)
    settled_at: str | None = None


@dataclass
class PaperBankroll:
    balance: float
    starting: float
    peak: float
    daily_loss_today: float
    today: str
    curve: list[dict] = field(default_factory=list)


class PaperTrader:
    """In-memory paper trader with settlement + guardrails."""

    def __init__(self, settings: BetforgeSettings | None = None, *, sink: Callable[[dict], None] | None = None) -> None:
        self.settings = settings or BetforgeSettings.from_env()
        self.ledger: list[PaperLedgerEntry] = []
        self.peak = float(self.settings.starting_bankroll_ngn)
        self.balance = float(self.settings.starting_bankroll_ngn)
        self.curve = []
        self._day = date.today().isoformat()
        self._daily_loss = 0.0
        self._daily_stopped = False  # hard daily-loss stop
        self.sink = sink

    def _refresh_day(self) -> None:
        now = date.today().isoformat()
        if now != self._day:
            self._day = now
            self._daily_loss = 0.0
            self._daily_stopped = False

    def available_capital(self) -> float:
        self._refresh_day()
        if self._daily_stopped:
            return 0.0
        remaining = self.settings.daily_loss_cap_ngn - self._daily_loss
        return max(0.0, min(self.balance, remaining))

    def place(self, key: str, market: str, odds: float, *, p: float) -> PaperLedgerEntry | None:
        """Place a paper bet. Returns None when any hard guardrail blocks it.

        Hard daily-loss stop: once realised losses today reach the cap, no
        further bets until the next day (the cap is a real stop, not a throttle).
        """
        self._refresh_day()
        if self._daily_stopped or self._daily_loss >= self.settings.daily_loss_cap_ngn:
            return None
        if odds < 1.01:
            return None
        frac = min(self.settings.stake_cap_frac, self.settings.hard_max_stake_frac)
        stake = round(frac * self.balance, 2)
        if stake <= 0 or stake > self.balance:
            return None
        self.balance = round(self.balance - stake, 2)
        entry = PaperLedgerEntry(signal_key=key, market=market, odds=odds, stake_ngn=stake)
        self.ledger.append(entry)
        self._snapshot()
        return entry

    def settle(self, entry: PaperLedgerEntry, won: bool) -> None:
        """Settle a pending entry from the real match result (exact ₦ accounting).

        Invariant: balance_final - balance_start == sum(entry.profit_ngn).
        The stake is already deducted at entry; a WIN returns stake + profit
        (stake * odds), a LOSS leaves the deducted stake as the loss and counts
        against the daily-loss hard stop.
        """
        if entry.status != "PENDING":
            return
        stake = entry.stake_ngn
        self._refresh_day()
        if won:
            payout = round(stake * entry.odds, 2)
            self.balance = round(self.balance + payout, 2)
            entry.profit_ngn = round(payout - stake, 2)
            entry.status = "WON"
        else:
            entry.profit_ngn = round(-stake, 2)
            entry.status = "LOST"
            self._daily_loss = round(self._daily_loss + stake, 2)
            if self._daily_loss >= self.settings.daily_loss_cap_ngn:
                self._daily_stopped = True
        entry.settled_at = _utcnow()
        self.peak = max(self.peak, self.balance)
        self._snapshot()
        if self.sink:
            self.sink(self.as_dict())

    def settle_match(self, key: str, won: bool) -> int:
        """Settle all pending entries for a fixture key at once. Returns count."""
        n = 0
        for e in self.ledger:
            if e.signal_key == key and e.status == "PENDING":
                self.settle(e, won)
                n += 1
        return n

    def _snapshot(self) -> None:
        self.curve.append({"ds": _utcnow(), "balance": round(self.balance, 2), "peak": round(self.peak, 2)})

    def profit_loss(self) -> float:
        return self.balance - float(self.settings.starting_bankroll_ngn)

    def max_drawdown_pct(self) -> float:
        mdd = 0.0
        for pt in self.curve:
            if pt["peak"] > 0:
                mdd = max(mdd, (pt["peak"] - pt["balance"]) / pt["peak"])
        return round(mdd, 4)

    def as_dict(self) -> dict:
        return {
            "balance_ngn": round(self.balance, 2),
            "starting_ngn": self.settings.starting_bankroll_ngn,
            "profit_loss_ngn": round(self.profit_loss(), 2),
            "peak_ngn": round(self.peak, 2),
            "max_drawdown_pct": self.max_drawdown_pct(),
            "daily_loss_today": round(self._daily_loss, 2),
            "auto_paper_trade": self.settings.auto_paper_trade,
            "ledger": [vars(e) for e in self.ledger],
            "curve": self.curve,
        }


def run_settlement_check(trader: PaperTrader, keys: Sequence[str], won: bool) -> int:
    """Settle a batch of fixture keys (used by the simulate_signals script)."""
    total = 0
    for k in keys:
        total += trader.settle_match(k, won)
    return total
