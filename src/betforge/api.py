"""FastAPI surface that exposes the prediction core over HTTP (/predict).

A lightweight, dependency-optional HTTP layer so BetForge can be served
behind any ASGI host (uvicorn, docker, railway, etc.) without touching the
stdlib model core.

Run:
    uvicorn betforge.api:app --host 0.0.0.0 --port 8000
Example:
    curl 'http://localhost:8000/predict?home=England&away=Brazil'

This serves /predict and a /health endpoint. Provenance of the training
data is returned in every response so prediction origin is traceable.
"""

from __future__ import annotations

from pathlib import Path

from .collection import Source
from .models import predict

# Default provenance: the free/public training set this repo ships with.
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "matches.csv"

_src = Source(name="free-public-international", url=None, license_note="MIT public dataset")


def _load_matches() -> "list":
    p = DATA_DIR
    if _src.matches:
        return _src.matches
    if p.exists():
        _src.ingest_csv(p)
    return _src.matches


def build_app(*, load_on_start: bool = True):
    """Create the FastAPI app. Importable so tests can build it without the ASGI server."""
    from fastapi import FastAPI, Query

    app = FastAPI(title="BetForge", version="0.1.0")

    if load_on_start:
        _load_matches()

    @app.get("/health")
    def health():
        return {"status": "ok", "matches_loaded": len(_src.matches), "source": _src.name}

    @app.get("/predict")
    def do_predict(
        home: str = Query(..., min_length=1),
        away: str = Query(..., min_length=1),
        recent: int | None = Query(default=None, ge=1),
        rho: float = Query(default=0.0),
    ):
        matches = _src.matches
        if not matches:
            from fastapi import HTTPException

            raise HTTPException(503, "no training data loaded; provide data/matches.csv")
        p = predict(home, away, matches, recent=recent, rho=rho)
        out = p.as_dict()
        out["provenance"] = {
            "source": _src.name,
            "license_note": _src.license_note,
            "n_matches": len(matches),
        }
        return out

    return app


app = build_app()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
