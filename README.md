# AI Calling SaaS — Project Scaffold

This repository contains a FastAPI backend, Celery worker, Postgres and Redis services.

Quick start (Docker):

```powershell
# from project root
docker-compose up -d
# run migrations inside backend container
docker exec saas_backend alembic upgrade head
```

Local scaffold (creates common folders):

```powershell
python scripts/create_structure.py
```

Files added by the scaffold:
- `.env.example` — example environment variables
- `scripts/create_structure.py` — creates common folders and __init__.py where appropriate

Next steps:
- Edit `.env.example` → `.env` and update values
- Run migrations: `alembic upgrade head`
- Start backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Start worker: `celery -A app.core.celery_app.celery_app worker --loglevel=info -Q campaign_queue`

