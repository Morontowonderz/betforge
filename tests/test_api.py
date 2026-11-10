"""Smoke tests for the FastAPI surface + SQLite storage layer.

Use the real loading path: ingest a tiny fixture CSV into a temp betforge.db,
point the module's DB_PATH at it, and exercise /health and /predict. No
reliance on the big data/matches.csv.
"""

import csv

import pytest

fixture_rows = [
    ("Strong", "Weak", 3, 0, "2024-01-01"),
    ("Strong", "Weak", 2, 1, "2024-02-01"),
    ("Weak", "Strong", 1, 2, "2024-03-01"),
    ("Strong", "Weak", 2, 0, "2024-04-01"),
]


@pytest.fixture
def db_path(tmp_path):
    """Build a small SQLite DB from fixture rows; return its path."""
    from betforge.storage import run_ingest

    csv_path = tmp_path / "fixture.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["home", "away", "home_goals", "away_goals", "date"])
        w.writerows(fixture_rows)
    dbp = tmp_path / "fixture.db"
    n = run_ingest(csv_path, dbp)
    assert n == 4
    return dbp


@pytest.fixture
def client(db_path, monkeypatch):
    import betforge.api as api_mod
    from fastapi.testclient import TestClient

    monkeypatch.setattr(api_mod, "DB_PATH", db_path)
    monkeypatch.setattr(api_mod, "_matches", None)
    app = api_mod.build_app(load_on_start=False)
    return TestClient(app)


def test_health(db_path, client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["matches_loaded"] == 4
    assert "betforge.db" in r.json()["source"]


def test_predict_returns_markets_and_provenance(db_path, client):
    r = client.get("/predict", params={"home": "Strong", "away": "Weak"})
    assert r.status_code == 200
    data = r.json()
    assert "p_over1_5" in data and "p_btts" in data
    assert 0.0 < data["p_over1_5"] < 1.0
    assert data["provenance"]["n_matches"] == 4


def test_predict_missing_teams_still_sane(db_path, client):
    r = client.get("/predict", params={"home": "Nope", "away": "AlsoNope"})
    assert r.status_code == 200
    s = r.json()
    assert abs(s["p_home"] + s["p_draw"] + s["p_away"] - 1.0) < 0.01


def test_storage_roundtrip(db_path):
    from betforge.storage import count_matches, iter_matches

    assert count_matches(db_path) == 4
    ms = list(iter_matches(db_path))
    assert len(ms) == 4
    assert ms[0].home_goals >= 0 and ms[0].away_goals >= 0
    # Match objects carry the odds fields (default inf when absent)
    assert ms[0].home_odds == float("inf")


def test_health_reports_db_key(db_path, client):
    """/health must expose the DB path under 'db' (not the old 'adb' typo)."""
    r = client.get("/health")
    assert r.status_code == 200
    assert "db" in r.json()
    assert "adb" not in r.json()


def test_predict_with_odds_uses_dixon_coles(db_path, client):
    """Supplying 1X2 odds must route through the DC baseline."""
    r = client.get("/predict", params={
        "home": "Strong", "away": "Weak",
        "home_odds": 1.65, "draw_odds": 3.3, "away_odds": 4.3,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provenance"]["method"] == "dixon-coles"
    assert 0.0 < data["p_over1_5"] < 1.0
    assert abs(data["p_home"] + data["p_draw"] + data["p_away"] - 1.0) < 0.01
    assert "dc_rho" in data["provenance"]


def test_predict_without_odds_uses_strength_model(db_path, client):
    r = client.get("/predict", params={"home": "Strong", "away": "Weak"})
    assert r.status_code == 200
    assert r.json()["provenance"]["method"] == "strength-poisson"


def test_predict_partial_odds_falls_back_to_strength(db_path, client):
    """Only some odds supplied -> not a full market -> strength model."""
    r = client.get("/predict", params={
        "home": "Strong", "away": "Weak", "home_odds": 1.65,
    })
    assert r.status_code == 200
    assert r.json()["provenance"]["method"] == "strength-poisson"


def test_predict_with_ou_uses_dixon_coles_o25(db_path, client):
    """Real O/U 2.5 pair -> the owner-mandated DC O2.5 path."""
    r = client.get("/predict", params={
        "home": "Strong", "away": "Weak",
        "over25_odds": 1.67, "under25_odds": 2.20,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provenance"]["method"] == "dixon-coles-o25"
    assert "p_over2_5" in data
    assert 0.0 < data["p_over2_5"] < 1.0
    assert "p_over25_market" in data["provenance"]
    # DC baseline should track the de-vigged O2.5 market
    assert abs(data["p_over2_5"] - data["provenance"]["p_over25_market"]) < 5e-3


def test_predict_ou_with_1x2_regulariser(db_path, client):
    r = client.get("/predict", params={
        "home": "Strong", "away": "Weak",
        "home_odds": 1.55, "draw_odds": 3.8, "away_odds": 5.0,
        "over25_odds": 1.67, "under25_odds": 2.20,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["provenance"]["method"] == "dixon-coles-o25"
    assert abs(data["p_home"] + data["p_draw"] + data["p_away"] - 1.0) < 0.01
