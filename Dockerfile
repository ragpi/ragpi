
FROM python:3.11

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry config virtualenvs.create false && \
  poetry install --no-dev

COPY ./src /app/src

CMD ["fastapi", "run", "src/main.py", "--port", "8000"]