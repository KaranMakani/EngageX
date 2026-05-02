FROM python:3.12-slim

WORKDIR /app

# install poetry
RUN pip install poetry==2.3.4

# copy dependency files first (better caching)
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# copy the rest of the code
COPY . .

# expose the port
EXPOSE 8000

# start the api (without discord bot for railway - bot runs locally for demo)
ENV API_ONLY=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
