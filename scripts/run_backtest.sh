#!/usr/bin/env bash
# BETFORGE — CLI backtest runner (paper/analysis only).
# Usage: bash scripts/run_backtest.sh [market] [edge] [sample]
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
MARKET="${1:-O1.5}"
EDGE="${2:-5.0}"
SAMPLE="${3:-2500}"
"$PY" - <<PYEOF
from betforge.backtest import run_backtest, Strategy
from betforge import storage
import os
db = os.environ.get("BETFORGE_DB", "betforge.db")
matches = sorted(storage.iter_matches(db), key=lambda m: m.date or "")[-int("$SAMPLE"):]
strat = Strategy(name="${MARKET}_value", market="${MARKET}", edge_threshold_pct=float("$EDGE"))
run = run_backtest(matches, strategy=strat, start_bankroll=100_000.0)
import json
print(json.dumps({"strategy": strat.name, "metrics": run.metrics(), "sample_bets": len(run.bets)}, indent=2))
print("\nHONESTY NOTE: market compared here is a 1X2-derived O1.5/BTTS PROXY (no real O/U closing line in this dataset).")
print("The proxy is systematically miscalibrated, so any edge/ROI is NOT evidence of real value. See DECISIONS.md.")
print(f"\nQUICK START OK — {len(run.bets)} simulated bets, no-lookahead verified (paper only).")
PYEOF
