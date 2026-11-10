"""BetForge product API: signals, backtest, paper trading, research, settings.

Mounted onto the existing FastAPI app (`build_app`) so the dashboard has one
backend. Everything here is analysis/paper only — there is no real-bet path.

All endpoints are dependency-light (stdlib) and draw the training matches
from the same SQLite store as /predict.
"""

from __future__ import annotations

from . import storage
from .backtest import O25, Strategy, run_backtest
from .minute7 import goal_minute_distribution, run_hypothesis_test, simulate_matches
from .paper import PaperTrader
from .settings import BetforgeSettings
from .signals import detect_signals


def _sample_matches(db_path, limit: int) -> list:
    """Load up to `limit` matches from SQLite (last N chronologically)."""
    matches = list(storage.iter_matches(db_path))
    matches.sort(key=lambda m: m.date or "")
    return matches[-limit:] if limit > 0 else matches


def build_router(db_path, *, seed: int = 7):
    """Create the product APIRouter bound to a DB path (so tests can inject)."""
    from fastapi import APIRouter, HTTPException

    router = APIRouter(prefix="/api")
    _trader: PaperTrader | None = None

    def get_trader() -> PaperTrader:
        nonlocal _trader
        if _trader is None:
            _trader = PaperTrader(BetforgeSettings.from_env())
        return _trader

    @router.get("/matches")
    def matches():
        """Sample upcoming/settled matches with ensemble probabilities + odds + edge."""
        matches = _sample_matches(db_path, 200)
        if not matches:
            raise HTTPException(503, "no data; run scripts/seed_historical.py")
        rows = []
        for m in matches[-60:]:
            from .imports_api import _row_from_match  # local helper below

            rows.append(_row_from_match(m))
        return {"count": len(rows), "matches": rows, "paper_only": True}

    @router.get("/signals")
    def signals():
        matches = _sample_matches(db_path, 400)
        if not matches:
            raise HTTPException(503, "no data; run scripts/ingest_db.py")
        settings = BetforgeSettings.from_env()
        list_of_signals, _ = detect_signals(matches, rules=settings.alert_rules, settings=settings)
        return {
            "count": len(list_of_signals),
            "signals": [s.as_dict() for s in list_of_signals[:50]],
            "paper_only": True,
        }

    @router.post("/backtest")
    def backtest(body: dict | None = None):
        body = body or {}
        market = body.get("market", O25)
        strategy = Strategy(
            name=body.get("strategy", f"{market}_value"),
            market=market,
            edge_threshold_pct=float(body.get("edge_threshold_pct", 5.0)),
            min_odds=float(body.get("min_odds", 1.4)),
            max_odds=float(body.get("max_odds", 5.0)),
            stake_plan=body.get("stake_plan", "flat"),
        )
        n = int(body.get("sample", 2500))
        if market == O25:
            from . import storage as _st

            # real O/U closing lines -> the honest O2.5 backtest path
            matches = list(_st.iter_matches_ou(db_path))
            matches.sort(key=lambda m: m.date or "")
            matches = matches[-n:]
            if not matches:
                raise HTTPException(503, "no real O/U lines; run scripts/ingest_ou_data.py")
        else:
            matches = _sample_matches(db_path, n)
            if not matches:
                raise HTTPException(503, "no data")
        run = run_backtest(matches, strategy=strategy, start_bankroll=100_000.0)
        curve = run.profit_curve
        step = max(1, len(curve) // 200)
        is_ou = market == "O2.5"
        return {
            "metrics": run.metrics(),
            "profit_curve": [round(v, 2) for v in curve[::step]][:240],
            "bets": [b.__dict__ for b in run.bets[:100]],
            "market_source": (
                "real O/U 2.5 closing line (de-vigged) — a genuine market comparison"
                if is_ou
                else "1x2-proxy (no real O/U closing line in this dataset — ROI is not evidence of real edge)"
            ),
            "paper_only": True,
        }

    @router.get("/paper")
    def paper():
        return get_trader().as_dict()

    @router.post("/paper/place")
    def paper_place(body: dict):
        t = get_trader()
        entry = t.place(str(body.get("key", "demo")), body.get("market", "O1.5"), float(body.get("odds", 2.0)), p=float(body.get("p", 0.6)))
        if entry is None:
            raise HTTPException(400, "blocked by a responsible-use guardrail (cap/daily-loss)")
        return vars(entry)

    @router.post("/paper/settle")
    def paper_settle(body: dict):
        t = get_trader()
        n = t.settle_match(str(body.get("key", "demo")), bool(body.get("won", False)))
        return {"settled": n, "paper": t.as_dict()}

    @router.get("/research/minute7")
    def research():
        matches = simulate_matches("Home", "Away", 200, seed=seed)
        report = run_hypothesis_test(matches, alpha=0.05)
        dist = goal_minute_distribution(matches)
        return {"report": report.as_dict(), "goal_minute_distribution": dist, "paper_only": True}

    @router.get("/accuracy")
    def accuracy():
        """Honest walk-forward-lite calibration: pooled Brier (O1.5) vs base rate."""
        matches = _sample_matches(db_path, 2500)
        if not matches:
            raise HTTPException(503, "no data")
        from .models import precompute_strengths, predict

        strengths, base = precompute_strengths(matches)
        n = 0
        se = 0.0
        se_base = 0.0
        base_rate = sum(1 for m in matches if m.over1_5) / max(1, len(matches))
        for m in matches[-1500:]:
            p = predict(m.home, m.away, matches, strengths=strengths, league_average=base).p_over1_5
            y = 1.0 if m.over1_5 else 0.0
            se += (p - y) ** 2
            se_base += (base_rate - y) ** 2
            n += 1
        return {
            "brier_over15": round(se / n, 4) if n else None,
            "brier_base_rate": round(se_base / n, 4) if n else None,
            "n": n,
            "honest_note": "Calibration tool — the strength-Poisson model does not claim to beat the base rate; edge is not asserted.",
            "paper_only": True,
        }

    @router.get("/settings")
    def settings_get():
        s = BetforgeSettings.from_env()
        return {
            "starting_bankroll_ngn": s.starting_bankroll_ngn,
            "stake_cap_frac": s.stake_cap_frac,
            "hard_max_stake_frac": s.hard_max_stake_frac,
            "daily_loss_cap_ngn": s.daily_loss_cap_ngn,
            "stake_plan": s.stake_plan,
            "edge_threshold_pct": s.edge_threshold_pct,
            "auto_paper_trade": s.auto_paper_trade,
            "responsible_notice": s.responsible_notice,
        }

    return router
