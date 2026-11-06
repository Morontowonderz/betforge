"""Smoke tests for the FastAPI surface, independent of data/matches.csv.

Uses build_app(load_on_start=False) and injects small in-memory history so
these tests pass anywhere (CI, clean checkout) without the data file.
"""

import pytest

fixture_matches = [
    ("Strong", "Weak", 3, 0, "2024-01-01"),
    ("Strong", "Weak", 2, 1, "2024-02-01"),
    ("Weak", "Strong", 1, 2, "2024-03-01"),
    ("Strong", "Weak", 2, 0, "2024-04-01"),
]


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from betforge.api import build_app
    from betforge.collection import Source

    app = build_app(load_on_start=False)
    src = Source(name="test", url=None, license_note="test")
    from betforge.normalization import Match

    src.ingest_records([Match(h, a, hg, ag, d) for h, a, hg, ag, d in fixture_matches])
    app.state.src = src
    # point the module-level source the app reads at our fixture
    import betforge.api as api_mod

    api_mod._src.matches = src.matches
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["matches_loaded"] == 4


def test_predict_returns_markets_and_provenance(client):
    r = client.get("/predict", params={"home": "Strong", "away": "Weak"})
    assert r.status_code == 200
    data = r.json()
    assert "p_over1_5" in data and "p_btts" in data
    assert 0.0 < data["p_over1_5"] < 1.0
    assert data["provenance"]["n_matches"] == 4


def test_predict_missing_teams_still_sane(client):
    r = client.get("/predict", params={"home": "Nope", "away": "AlsoNope"})
    assert r.status_code == 200
    s = r.json()
    # API returns 4-decimal-rounded probabilities, so allow rounding slack.
    assert abs(s["p_home"] + s["p_draw"] + s["p_away"] - 1.0) < 0.01
