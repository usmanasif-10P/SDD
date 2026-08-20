# Todo Management App

FastAPI + PostgreSQL service for per-user todo management with JWT auth.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # then edit secrets
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest
```
