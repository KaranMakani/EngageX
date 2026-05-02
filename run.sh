#!/bin/bash
# run the full stack locally (API + Discord bot)
cd "$(dirname "$0")"
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
