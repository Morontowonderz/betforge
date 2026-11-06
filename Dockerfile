# BetForge service image.
# Builds a small Python ASGI server exposing /predict from the stdlib model core.
# The training CSV is small (international results window) and shipped in-image;
# a production setup should mount/refresh data separately.
FROM python:3.12-slim

WORKDIR /app

# Install build tooling, then project with web extras (fastapi + uvicorn).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .[web]

# Training data (free/public). Mount over this path to refresh without rebuild.
COPY data/matches.csv /app/data/matches.csv

EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000
CMD ["uvicorn", "betforge.api:app", "--host", "0.0.0.0", "--port", "8000"]
