# BetForge service image (paper-trading analytics, SQLite-backed).
# Ships the real O/U closing-line corpus (data/raw_fd) so /health, /api/matches,
# /api/backtest (O2.5), /api/accuracy and /api/research have real data on first
# run. Both tables (matches, matches_ou) live in one SQLite file (betforge.db).
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .[web]

COPY scripts ./scripts
# Real O/U 2.5 closing lines + canonical FT results -> one SQLite file (betforge.db)
COPY data/raw_fd /app/data/raw_fd
RUN python scripts/build_image_seed.py /app/data/raw_fd /app/betforge.db

EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 BETFORGE_DB=/app/betforge.db
CMD ["uvicorn", "betforge.api:app", "--host", "0.0.0.0", "--port", "8000"]
