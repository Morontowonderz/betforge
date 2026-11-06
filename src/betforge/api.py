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


def build_app(*, load_on_start: bool = True):
    """Create the FastAPI app. Importable so tests can build it without ASGI."""
    from fastapi import FastAPI, Query

    app = FastAPI(title="BetForge", version="0.1.0")

    if load_on_start:
        load_matches()

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "matches_loaded": len(load_matches()),
            "source": "betforge.db (sqlite)",
            "adb": str(DB_PATH),
        }

    @app.get("/predict")
    def do_predict(
        home: str = Query(..., min_length=1),
        away: str = Query(..., min_length=1),
        recent: int | None = Query(default=None, ge=1),
        rho: float = Query(default=0.0),
    ):
        matches = load_matches()
        if not matches:
            from fastapi import HTTPException

            raise HTTPException(503, "no training data in betforge.db; run scripts/ingest_db.py")
        p = predict(home, away, matches, recent=recent, rho=rho)
        out = p.as_dict()
        out["provenance"] = {
            "source": "betforge.db (sqlite)",
            "n_matches": len(matches),
            "db_rows": count_matches(DB_PATH) if DB_PATH.exists() else 0,
        }
        return out

    return app


app = build_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
