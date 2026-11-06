# BetForge service image.
# Builds a small Python ASGI server exposing /predict from the SQLite-backed,
# stdlib model core. Training data is ingested into betforge.db at build time
# from the shipped canonical CSV (the .db itself is a gitignored build artifact).
FROM python:3.12-slim

WORKDIR /app

# Install build tooling, then project with web extra (fastapi + uvicorn).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .[web]

# Training data + ingest script -> build the SQLite DB inside the image.
COPY scripts ./scripts
COPY data/matches.csv /app/data/matches.csv
RUN python scripts/ingest_db.py --csv /app/data/matches.csv --db /app/betforge.db

EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 BETFORGE_DB=/app/betforge.db
CMD ["uvicorn", "betforge.api:app", "--host", "0.0.0.0", "--port", "8000"]
