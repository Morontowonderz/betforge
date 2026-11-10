"""Real O/U line ingestion + honest O2.5 backtest tests."""

from __future__ import annotations

from betforge.backtest import O25, Strategy, run_backtest
from betforge.ingestion import parse_football_data_file
from betforge.devig import ou_implied_p25
from betforge.normalization import Match

FD_CSV = """Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,AvgC>2.5,AvgC<2.5,B365>2.5,B365<2.5,Avg>2.5,Avg<2.5
2024-01-06,Liverpool,Newcastle,4,2,H,1.40,2.90,1.35,3.20,1.38,3.05
2024-01-13,Wolves,Man United,1,0,H,2.10,1.70,2.00,1.80,2.05,1.78
2024-01-20,Arsenal,Chelsea,2,2,D,,,,,1.60,2.30
"""


def test_parse_football_data_uses_closing_line(tmp_path):
    p = tmp_path / "E0_2324.csv"
    p.write_text(FD_CSV, encoding="utf-8")
    matches, stats = parse_football_data_file(p)
    assert stats["with_ou"] == 3
    # row 1 uses the CLOSING line (AvgC>2.5=1.40), row 3 falls back to opening (Avg>2.5=1.60)
    liv = next(m for m in matches if m.home == "Liverpool")
    assert liv.over_odds == 1.40 and liv.under_odds == 2.90
    assert liv.has_ou_line
    ars = next(m for m in matches if m.home == "Arsenal")
    assert ars.over_odds == 1.60  # opening fallback
    # team alias normalised
    assert any(m.home == "Wolverhampton Wanderers" for m in matches)


def test_parse_drops_rows_missing_ou_line(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(FD_CSV, encoding="utf-8")
    # force an extra row with no O/U columns present? FD_CSV has columns; craft a row with empty OU
    with p.open("a", encoding="utf-8") as fh:
        fh.write("2024-02-01,TeamA,TeamB,1,1,D,,,,,\n")
    matches, stats = parse_football_data_file(p)
    assert stats["dropped_ou"] == 1
    assert len(matches) == 3


def test_ou_implied_p25_is_devigged():
    # P(over) = (1/1.40) / (1/1.40 + 1/2.90)
    expected = (1 / 1.40) / (1 / 1.40 + 1 / 2.90)
    assert abs(ou_implied_p25(1.40, 2.90) - expected) < 1e-6


def _ou_season() -> list[Match]:
    # real-line synthetic season: +3/0/0 style goals, varied lines
    return [
        Match("A", "B", 3, 1, "2024-01-01", over_odds=1.6, under_odds=2.3),
        Match("C", "D", 1, 1, "2024-01-03", over_odds=2.5, under_odds=1.5),
        Match("E", "F", 2, 0, "2024-01-05", over_odds=1.9, under_odds=1.9),
        Match("A", "C", 2, 2, "2024-01-08", over_odds=1.5, under_odds=2.6),
        Match("B", "D", 0, 0, "2024-01-10", over_odds=2.6, under_odds=1.5),
        Match("C", "E", 3, 3, "2024-01-12", over_odds=1.55, under_odds=2.4),
        Match("A", "D", 1, 2, "2024-01-15", over_odds=1.7, under_odds=2.1),
        Match("B", "E", 4, 0, "2024-01-18", over_odds=1.5, under_odds=2.6),
        Match("D", "F", 0, 1, "2024-01-20", over_odds=2.4, under_odds=1.55),
        Match("A", "E", 2, 1, "2024-01-22", over_odds=1.6, under_odds=2.3),
    ]


def test_o25_backtest_uses_real_line_and_settles():
    strategy = Strategy(name="O2.5_value", market=O25, edge_threshold_pct=-999.0, min_odds=1.01)
    run = run_backtest(_ou_season(), strategy=strategy, start_bankroll=100_000.0)
    assert run.bets  # forced to bet every OU fixture
    for b in run.bets:
        m = next(x for x in _ou_season() if x.home == b.home and x.away == b.away)
        assert b.odds == m.over_odds  # the REAL closing over-line price, no proxy
        assert b.status == ("WON" if m.over2_5 else "LOST")
        # ledger math still holds
    assert abs(sum(b.profit_ngn for b in run.bets) - (run.end_bankroll - run.start_bankroll)) < 1e-6
    # honest market: implied is the de-vigged O2.5 line, not a 1X2 proxy
    first = run.bets[0]
    m = next(x for x in _ou_season() if x.home == first.home and x.away == first.away)
    assert abs(first.implied_p - ou_implied_p25(m.over_odds, m.under_odds)) < 1e-9
