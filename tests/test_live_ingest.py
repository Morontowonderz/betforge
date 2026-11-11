"""Live-ingest (Minute-7 corpus) tests: real file corpus + mock fallback + honest flag."""

from __future__ import annotations

import json
from pathlib import Path

from betforge.live_ingest import _coerce, get_minute7_corpus, load_real_live_corpus, set_corpus_loader


def test_mock_fallback_when_no_env():
    set_corpus_loader(load_real_live_corpus)  # no LIVE_* env -> real returns None
    matches, simulated = get_minute7_corpus()
    assert simulated is True  # seeded mock, clearly flagged
    assert len(matches) == 200


def test_real_corpus_sets_simulated_false(tmp_path):
    f = tmp_path / "lives.json"
    f.write_text('[{"home":"A","away":"B","home_goals_minutes":[3],"away_goals_minutes":[9,40]}]', encoding="utf-8")

    def load():
        return _coerce(json.loads(Path(f).read_text(encoding="utf-8")))

    set_corpus_loader(load)
    matches, simulated = get_minute7_corpus()
    assert simulated is False  # real corpus, not the mock generator
    assert len(matches) == 1
    m = matches[0]
    assert m.home == "A" and m.away == "B"
    assert m.home_goals_minutes == (3,)
    assert m.away_goals_minutes == (9, 40)

    # restore default loader for later tests
    set_corpus_loader(load_real_live_corpus)


def test_malformed_event_is_skipped():
    payload = [{"home": "A", "away": "B", "home_goals_minutes": [3], "away_goals_minutes": [9]}, {"nope": True}, "junk"]
    rows = _coerce(payload)
    assert len(rows) == 1
    assert rows[0].early_goal is True  # goal at minute 3 <= 7
