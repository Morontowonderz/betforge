# BetForge Free Football Data Sources — Research Memo

**Date:** 2026-11-06
**Scope:** Genuinely free/public (no-API-key) **club-league** datasets for Over-1.5 / BTTS modelling. All URLs verified reachable (HTTP 200) on 2026-11-06. Licenses quoted verbatim from each source; none invented.

---

## 1. Candidate club-league datasets (no API key required)

### A. xgabora/Club-Football-Match-Data-2000-2025
- **Where:** https://github.com/xgabora/Club-Football-Match-Data-2000-2025
- **License:** MIT (LICENSE file: "MIT License ... Permission is hereby granted, free of charge"). ⚠️ Data itself is *sourced from football-data.co.uk* — see §4 risk flag.
- **Leagues:** 38 league/division codes incl. English Premier League, Bundesliga, La Liga, Serie A, Ligue 1.
- **Freshness:** 238,858 matches, 2000/01 through 3 Sep 2026 (full 2025/26 + opening 2026/27).
- **Depth:** Excellent for training ~26 seasons; **includes pre-match odds** — ideal for calibrating Over-1.5/BTTS probability models.
- **Download (verified):** `curl -L -o Matches.csv "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"` (45.4 MB)

### B. openfootball/football.json (openfootball)
- **Where:** https://github.com/openfootball/football.json
- **License:** CC0 1.0 / public domain ("dedicated to the public domain. Use as you please with no restrictions whatsoever").
- **Leagues:** EPL, Championship, League One/Two, Bundesliga 1–3, La Liga, Segunda, Serie A/B, Ligue 1/2, more.
- **Freshness:** seasons 2010/11 onward (varies by league).
- **Depth:** Good for fixture/result date; **no odds, no per-match stats** (scoreline only) — weaker for BTTS feature engineering.
- **Download (verified):** `curl -L -o en.1.json "https://raw.githubusercontent.com/openfootball/football.json/master/2024-25/en.1.json"`

### C. openfootball/world — Nigeria & Africa (openfootball)
- **Where:** https://github.com/openfootball/world (Africa dir: https://github.com/openfootball/world/tree/master/africa)
- **License:** Public domain (LICENSE.md, same CC0-style dedication as openfootball).
- **Leagues:** Nigerian Premier League (`_ng1`) + Nigerian National League (`_ng2`), plus Egypt, Morocco, Algeria and other African leagues; Football.TXT format.
- **Freshness:** Nigeria 2009-10 → 2025-26 seasons present.
- **Depth:** Results/fixtures only, shallow stats, text format (needs parsing). Direct relevance to a Nigeria-based owner.
- **Download (verified):** `curl -L -o 2024-25_ng1.txt "https://raw.githubusercontent.com/openfootball/world/master/africa/nigeria/2024-25_ng1.txt"`

### D. schochastics/football-data
- **Where:** https://github.com/schochastics/football-data
- **License:** Open Data Commons Attribution License (ODC-BY) — stated in README.
- **Leagues:** 207 top-tier domestic leagues + 20 international tournaments.
- **Freshness:** 1888–2023 (ends 2023 — not current-season).
- **Depth:** 1,237,935 games. Best historical breadth for cross-league normalization.
- **Download (verified):** `curl -L -o games.parquet "https://raw.githubusercontent.com/schochastics/football-data/master/data/results/games.parquet"` (16.4 MB)

### E. Fjelstul English Football Database
- **Where:** https://github.com/Fjelstul/englishfootball
- **License:** CC BY-SA 4.0 (Attribution-ShareAlike) — cite + share-alike.
- **Leagues:** Premier League + EFL, 1888–2024 (208,028 matches, incl. appearances/standings).
- **Depth:** Deep + rich, but on parquet CSV for EFL. ⚠️ Share-alike limits closed monetization.

### F. engsoccerdata (English/Spanish/German data)
- **Where:** https://github.com/jalapic/engsoccerdata
- **License:** **Non-commercial use with citation** — explicitly unsuitable if BetForge is monetized. Listed for completeness only.

### G. European Soccer Database (Hernandez/Nutsu Kaggle)
- **Where:** https://www.kaggle.com/datasets/hugomathien/soccer
- **License:** ODbL. 11 European leagues, 25k+ matches **2008–2016** (stale). Needs a free Kaggle account to fetch. Share-alike caveat.

---

## 2. Verdict on the current source (martj42/international_results)

**Verdict: poor proxy for club-league Over-1.5/BTTS modelling — use only as a supplement, never as the primary training basis.**

- **License is sound:** MIT (per repo LICENSE/README) — permissive for commercial reuse. No issue there.
- **Population mismatch:** Internationals are ~50k matches of national-team games; club-league predictions operate on a different population with higher, more regular scoring and entrenched home advantage. Transfer will be weak.
- **Biases introduced:**
  - **Internationals skew:** friendlies are low-intensity with heavy rotation; tournament knockouts are cagey (fewer goals). Both distort Over-1.5/BTTS rates versus domestic league rhythms.
  - **No domestic rhythm:** no weekend/midweek consistency, no back-to-back scheduling effects, squad cycles differ — features that carry goals-signal in club play are absent or meaningless.
  - **Skill-level chasm:** mismatched internationals (e.g. minnows) produce inflated-goal outliers the model will over-weight.
  - **Team-name matching:** national-team IDs don't align with club names/rosters; can't transfer team identifiers to a club pipeline.
  - **No odds:** lacks betting odds, so you cannot calibrate to implied probabilities the way club data allows.
- **Recommendation:** keep martj42 as a domestic-neutrality/regularization supplement if desired, but add club-league data (A + C) as the core training set.

---

## 3. Top 2 additions: exact verified fetch commands

**#1 — xgabora club matches (Best overall, MIT, includes odds):**
```bash
curl -L -o Matches.csv "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"
```
Verified: HTTP 200, content-length 45,370,018 bytes.

**#2 — openfootball/world Nigeria + Africa (CC0/public domain, local-league relevance):**
```bash
curl -L -o 2024-25_ng1.txt "https://raw.githubusercontent.com/openfootball/world/master/africa/nigeria/2024-25_ng1.txt"
```
Verified: HTTP 200. (Loop over seasons/repos to fetch full history.)

---

## 4. Data-rights risk flags (monetization caveats)

- **xgabora (MIT repo) BUT sourced from football-data.co.uk:** the repo's MIT license covers the *assembly*, not the underlying data. football-data.co.uk has **no formal open-data license** — check its terms page for redistribution/commercial restrictions before any paid product. **Medium-high risk.**
- **openfootball (football.json / world):** CC0/public domain, low risk; compiled from public sources (often Wikipedia) so attribution is polite but not legally required. Committing the openfootball Nigeria files to your repo is fine.
- **schochastics:** ODC-BY — free to use commercially with attribution (Must: credit the source in your credits/about). Low risk.
- **Fjelstul (CC BY-SA) / European Soccer DB (ODbL):** share-alike — any *adapted database* must be released under the same license. Risky for closed monetization; use only for derived predictions, not redistributed DBs.
- **engsoccerdata:** non-commercial — **do not use** if monetizing.
- **martj42:** MIT — safe.

---

## 5. Recommended path forward
1. Adopt **xgabora** as the primary club training set (odds + 26 seasons = best fit for Over-1.5/BTTS probability calibration).
2. Add **openfootball/world** Nigeria/Africa for local-league coverage (target audiences).
3. Use **schochastics** for cross-league historical breadth.
4. Re-verify football-data.co.uk terms before any commercialization; keep martj42 as optional supplement only.
