FROM python:3.11-slim AS requirements

RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential gcc && \
  rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade poetry && \
  poetry self add poetry-plugin-export

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN mkdir /src

RUN poetry export -f requirements.txt --without-hashes -o /src/requirements.txt


FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PORT=8000 

WORKDIR /app

COPY --from=requirements /src/requirements.txt requirements.txt

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY ./src /app/src

CMD ["sh", "-c", "fastapi run src/main.py --host 0.0.0.0 --port ${PORT}"]
