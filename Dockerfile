FROM python:3.11-slim as requirements

RUN apt-get update && \
  apt-get install -y --no-install-recommends build-essential gcc && \
  rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir --upgrade poetry && \
  poetry self add poetry-plugin-export

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN mkdir /src

RUN poetry export -f requirements.txt --without-hashes -o /src/requirements.txt

FROM python:3.11-slim as base

WORKDIR /app

COPY --from=requirements /src/requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY ./src /app/src

CMD ["fastapi", "run", "src/main.py", "--port", "8000"]
