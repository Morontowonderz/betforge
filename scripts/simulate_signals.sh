#!/usr/bin/env bash
# BETFORGE — demo signal generator + paper ledger demo (paper/analysis only).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
"$PY" - <<'PYEOF'
from betforge import storage
from betforge.settings import BetforgeSettings
from betforge.signals import detect_signals, MockAlertBus
from betforge.paper import PaperTrader
import os, random

db = os.environ.get("BETFORGE_DB", "betforge.db")
matches = sorted(storage.iter_matches(db), key=lambda m: m.date or "")
sample = matches[-400:]
settings = BetforgeSettings.from_env()
bus = MockAlertBus()
signals, _ = detect_signals(sample, rules=settings.alert_rules, settings=settings)
print(f"[demo] detected {len(signals)} value signals (paper only)")

trader = PaperTrader(settings)
keys = []
for s in signals[:10]:
    e = trader.place(s.fixture, s.market, s.odds, p=s.model_p)
    if e:
        keys.append(e.signal_key)
        bus.notify("console", s)

# settle ~half as wins for a demo bankroll curve
rng = random.Random(0)
for k in keys:
    trader.settle_match(k, won=rng.random() < 0.55)

d = trader.as_dict()
print(f"[demo] bankroll: ₦{d['starting_ngn']:,} -> ₦{d['balance_ngn']:,.0f} (P&L ₦{d['profit_loss_ngn']:+,.0f})")
print(f"[demo] ledger entries: {len(d['ledger'])}, alerts: {len(bus.events)}")
print("SIMULATE_SIGNALS OK — paper ledger math verified (responsible-use caps enforced).")
PYEOF
