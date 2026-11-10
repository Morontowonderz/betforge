"""Shared helpers for the product API row serialisation.

Kept separate so product_api stays small and the (stdlib) match->row mapping
is unit-visible. No heavy deps — reuses the strength model + devig.
"""

from __future__ import annotations

from .devig import market_from_1x2
from .models_engine import ensemble
from .normalization import Match


def _row_from_match(m: Match, *, history: list[Match] | None = None) -> dict:
    """One matches/ table row: teams, kickoff, odds, model probs, edge."""
    prior = history or []
    r = ensemble(m.home, m.away, prior)
    mkt = market_from_1x2([m.home_odds, m.draw_odds, m.away_odds])
    edge15 = (r.p_over15 - mkt.p_over15) * 100.0
    edgebtts = (r.p_btts - mkt.p_btts) * 100.0
    return {
        "fixture": f"{m.home} vs {m.away}",
        "date": m.date,
        "home": m.home,
        "away": m.away,
        "odds": {
            "home": round(m.home_odds, 2) if m.home_odds != float("inf") else None,
            "draw": round(m.draw_odds, 2) if m.draw_odds != float("inf") else None,
            "away": round(m.away_odds, 2) if m.away_odds != float("inf") else None,
        },
        "model": {"p_over15": round(r.p_over15, 3), "p_btts": round(r.p_btts, 3)},
        "edge": {"o15_pct": round(edge15, 2), "btts_pct": round(edgebtts, 2)},
    }
