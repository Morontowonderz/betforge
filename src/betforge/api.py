"""FastAPI surface that exposes the prediction core over HTTP (/predict).

A lightweight, dependency-optional HTTP layer so BetForge can be served
behind any ASGI host (uvicorn, docker, railway, etc.) without touching the
stdlib model core. Training matches are loaded from the local SQLite database
(`betforge.db`), not from the CSV on every startup.

Run:
    uvicorn betforge.api:app --host 0.0.0.0 --port 8000
Example:
    curl 'http://localhost:8000/predict?home=England&away=Brazil'
"""

from __future__ import annotations

import os
from pathlib import Path

from .models import predict
from .storage import count_matches, iter_matches

# The SQLite database holds the free/public training set. Priority:
#   1. BETFORGE_DB env var (set it in Docker, systemd, etc.)
#   2. ./betforge.db relative to the working directory (the Docker WORKDIR /app)
# A module-relative path is deliberately NOT used: inside a container the package
# is installed into site-packages, so __file__ would point far from the data.
DB_PATH = Path(os.environ.get("BETFORGE_DB", "betforge.db"))

_matches: list | None = None


def load_matches():
    """Load matches from SQLite once and cache for the app lifetime."""
    global _matches
    if _matches is not None:
        return _matches
    if not DB_PATH.exists():
        _matches = []  # /health will report 0; /predict will 503
        return _matches
    _matches = list(iter_matches(DB_PATH))
    return _matches


def _dc_response(home: str, away: str, market: dict, params, matches) -> dict:
    """Build the /predict response for a Dixon-Coles baseline result."""
    return {
        "home": home,
        "away": away,
        "expected_home": round(params.lam_home, 3),
        "expected_away": round(params.lam_away, 3),
        "p_over1_5": round(market["p_over15"], 4),
        "p_over2_5": round(market["p_over25"], 4),
        "p_btts": round(market["p_btts"], 4),
        "p_home": round(market["p_home"], 4),
        "p_draw": round(market["p_draw"], 4),
        "p_away": round(market["p_away"], 4),
        "provenance": {
            "source": "betforge.db (sqlite)",
            "method": params.method,
            "n_matches": len(matches),
            "db_rows": count_matches(DB_PATH) if DB_PATH.exists() else 0,
            "devig_k": round(market.get("devig_k", 1.0), 4),
            "dc_rho": round(params.rho, 4),
            "dc_fit_rmse": round(params.fit_rmse, 6),
            "p_over25_market": round(market.get("p_over25_market", 0.0), 4),
        },
    }


def build_app(*, load_on_start: bool = True):
    """Create the FastAPI app. Importable so tests can build it without ASGI."""
    from fastapi import FastAPI, Query

    app = FastAPI(title="BetForge", version="0.1.0")

    from .product_api import build_router

    app.include_router(build_router(DB_PATH))

    if load_on_start:
        load_matches()

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "matches_loaded": len(load_matches()),
            "source": "betforge.db (sqlite)",
            "db": str(DB_PATH),
        }

    @app.get("/predict")
    def do_predict(
        home: str = Query(..., min_length=1),
        away: str = Query(..., min_length=1),
        recent: int | None = Query(default=None, ge=1),
        rho: float = Query(default=0.0),
        home_odds: float | None = Query(default=None, gt=1.0),
        draw_odds: float | None = Query(default=None, gt=1.0),
        away_odds: float | None = Query(default=None, gt=1.0),
        over25_odds: float | None = Query(default=None, gt=1.0),
        under25_odds: float | None = Query(default=None, gt=1.0),
    ):
        matches = load_matches()
        if not matches:
            from fastapi import HTTPException

            raise HTTPException(503, "no training data in betforge.db; run scripts/ingest_db.py")

        ou_supplied = over25_odds is not None and under25_odds is not None
        odds_supplied = all(o is not None for o in (home_odds, draw_odds, away_odds))

        # Owner mandate 2026-11-06: real O/U 2.5 closing lines are the primary
        # path. Fit the DC baseline to the O2.5 pair (1X2 as regulariser).
        if ou_supplied:
            from .baseline import predict_from_ou

            assert over25_odds is not None and under25_odds is not None
            market, params = predict_from_ou(
                over25_odds, under25_odds,
                odds_1x2=[home_odds, draw_odds, away_odds] if odds_supplied else None,
            )
            return _dc_response(home, away, market, params, matches)

        if odds_supplied:
            from .baseline import predict_from_odds

            assert home_odds is not None and draw_odds is not None and away_odds is not None
            market, params = predict_from_odds([home_odds, draw_odds, away_odds])
            return _dc_response(home, away, market, params, matches)

        p = predict(home, away, matches, recent=recent, rho=rho)
        out = p.as_dict()
        out["provenance"] = {
            "source": "betforge.db (sqlite)",
            "method": "strength-poisson",
            "n_matches": len(matches),
            "db_rows": count_matches(DB_PATH) if DB_PATH.exists() else 0,
        }
        return out

    return app


app = build_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
