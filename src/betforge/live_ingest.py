"""Live minute-by-minute ingestion for the Minute-7 research module.

Adapter pattern: when a real live source is configured it is consumed and the
mock generator is bypassed; otherwise research falls back to the (deterministic,
seeded) mock generator so the module always works with no external keys.

Real sources (env-gated, documented, never required):
  * LIVE_MINUTE7_URL   -> a JSON feed, e.g.
        [{"home":"A","away":"B","home_goals_minutes":[3,41],"away_goals_minutes":[9]}]
  * LIVE_MINUTE7_FILE  -> a local JSON file with the same shape (offline real data)

Honesty: a mock is not a live feed. The report carries `simulated: true` when
the mock generator is used and `simulated: false` when a real corpus is loaded.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path

from .minute7 import LiveMatch


def _parse_event(ev: dict) -> LiveMatch | None:
    try:
        home = str(ev["home"])
        away = str(ev["away"])
    except (KeyError, TypeError):
        return None
    def _mins(key: str) -> tuple[int, ...]:
        vals = ev.get(key) or []
        out = []
        for v in vals:
            try:
                m = int(v)
            except (TypeError, ValueError):
                continue
            if 1 <= m <= 90:
                out.append(m)
        return tuple(sorted(out))
    return LiveMatch(home=home, away=away, home_goals_minutes=_mins("home_goals_minutes"), away_goals_minutes=_mins("away_goals_minutes"))


def load_real_live_corpus() -> list[LiveMatch] | None:
    """Load real minute-by-minute data from LIVE_MINUTE7_URL or LIVE_MINUTE7_FILE.

    Returns None when no real source is configured (caller falls back to mock).
    Never raises on transport/parse failure — a broken live feed must not crash
    research; it returns None so the mock fallback (clearly labelled) is used.
    """
    url = os.environ.get("LIVE_MINUTE7_URL")
    if url:
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 - best-effort live feed
            return None
        return _coerce(payload)

    path = os.environ.get("LIVE_MINUTE7_FILE")
    if path:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
        return _coerce(payload)

    return None


def _coerce(payload: object) -> list[LiveMatch]:
    if not isinstance(payload, list):
        return []
    out = []
    for ev in payload:
        if isinstance(ev, dict):
            m = _parse_event(ev)
            if m is not None:
                out.append(m)
    return out


CorpusLoader = Callable[[], list[LiveMatch] | None]

# Injectable loader (tests can override), defaulting to the env-gated real load.
_loader: CorpusLoader = load_real_live_corpus


def set_corpus_loader(loader: CorpusLoader) -> None:
    """Override the corpus loader (used by tests / callers feeding real data)."""
    global _loader
    _loader = loader


def get_minute7_corpus(*, fallback_mock: bool = True) -> tuple[list[LiveMatch], bool]:
    """Return (matches, simulated_flag). Real corpus when configured, else mock.

    `simulated` is True only when the mock generator produced the data.
    """
    real = _loader()
    if real:
        return real, False
    if fallback_mock:
        from .minute7 import simulate_matches

        return simulate_matches("Home", "Away", 200, lam_home=1.4, lam_away=1.2, seed=7), True
    return [], False
