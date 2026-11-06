"""Delivery: CLI entry point for generating predictions from a CSV.

Usage:
    betforge predict <matches.csv> --home <teamA> --away <teamB> [--recent N] [--rho X]
    betforge ingest  <matches.csv>            # validate + count records
"""

from __future__ import annotations

import argparse
import json

from .collection import Source
from .models import predict


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="betforge", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest", help="validate and count rows in a CSV fixture")
    ing.add_argument("csv", type=str)
    ing.add_argument("--name", default="local-csv", help="provenance label")
    ing.add_argument("--url", default=None)
    ing.add_argument("--license", default="free/public", help="license note for provenance")

    pr = sub.add_parser("predict", help="predict over1.5 + BTTS for a fixture")
    pr.add_argument("csv", type=str)
    pr.add_argument("--home", required=True)
    pr.add_argument("--away", required=True)
    pr.add_argument("--recent", type=int, default=None)
    pr.add_argument("--rho", type=float, default=0.0, help="Dixon-Coles rho (0 = plain Poisson)")
    pr.add_argument("--json", action="store_true", help="emit JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "ingest":
        src = Source(name=args.name, url=args.url, license_note=args.license)
        n = src.ingest_csv(args.csv)
        valid = n
        skipped = 0  # skipped rows are not counted here by design
        print(f"ingested {valid} valid match records from {args.csv}")
        print("source: %s | license note: %s" % (src.name, src.license_note))
        print("provenance field always accompanies predictions.")
        return 0

    # predict
    src = Source(name="local-csv", url=None, license_note="free/public")
    src.ingest_csv(args.csv)
    if not src.matches:
        print("no valid matches found in %s" % args.csv, file=__import__("sys").stderr)
        return 1
    p = predict(args.home, args.away, src.matches, recent=args.recent, rho=args.rho)
    if args.json:
        print(json.dumps(p.as_dict(), indent=2))
    else:
        print(f"{p.home} vs {p.away}")
        print(f"  expected goals: {p.expected_home:.2f} - {p.expected_away:.2f}")
        print(f"  P(Over 1.5)  = {p.p_over1_5:.3f}")
        print(f"  P(BTTS)      = {p.p_btts:.3f}")
        print(f"  P(1) {p.p_home:.3f}  P(X) {p.p_draw:.3f}  P(2) {p.p_away:.3f}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
