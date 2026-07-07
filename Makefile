.PHONY: help up down build logs migrate seed test lint health backup

COMPOSE_PROD = docker compose -f docker-compose.prod.yml
COMPOSE_DEV  = docker compose -f docker-compose.yml
BACKEND      = cd backend &&

help:
	@echo ""
	@echo "EIOS — Production Operations"
	@echo "─────────────────────────────────────────────"
	@echo "  make up          Start all production services"
	@echo "  make down        Stop all services"
	@echo "  make build       Rebuild images (no cache)"
	@echo "  make logs        Tail all service logs"
	@echo "  make migrate     Run Alembic migrations"
	@echo "  make seed        Seed demo organisation data"
	@echo "  make test        Run backend unit tests"
	@echo "  make lint        Run ruff + mypy"
	@echo "  make health      Check service health endpoints"
	@echo "  make backup      Trigger manual DB backup"
	@echo ""

up:
	$(COMPOSE_PROD) up -d
	@echo "Services started. Health: http://localhost/health"

down:
	$(COMPOSE_PROD) down

build:
	$(COMPOSE_PROD) build --no-cache

logs:
	$(COMPOSE_PROD) logs -f --tail=100

migrate:
	$(COMPOSE_PROD) exec backend alembic upgrade head

seed:
	$(COMPOSE_PROD) exec backend python -c \
	  "import asyncio; from infrastructure.demo.seed import ensure_demo_data; \
	   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession; \
	   from app.config import settings; \
	   engine = create_async_engine(settings.database_url); \
	   async def run(): \
	     async with AsyncSession(engine) as s, s.begin(): await ensure_demo_data(s); \
	   asyncio.run(run())"
	@echo "Demo data seeded: demo@eios.internal / DemoEIOS2024!"

test:
	$(BACKEND) source .venv/bin/activate && pytest tests/unit/ -q --tb=short

lint:
	$(BACKEND) source .venv/bin/activate && ruff check . && ruff format --check . && mypy domain/

health:
	@echo "── Backend ──────────────────────────────────"
	@curl -sf http://localhost:8000/health | python3 -m json.tool || echo "FAILED"
	@echo "── Ready ────────────────────────────────────"
	@curl -sf http://localhost:8000/health/ready | python3 -m json.tool || echo "FAILED"

backup:
	$(COMPOSE_PROD) exec postgres-backup pg_backup.sh
	@echo "Backup triggered. Check logs: make logs"

# ── Development shortcuts ──────────────────────────────────────────────────────

dev-up:
	$(COMPOSE_DEV) up -d

dev-down:
	$(COMPOSE_DEV) down

dev-logs:
	$(COMPOSE_DEV) logs -f --tail=50

dev-migrate:
	$(BACKEND) source .venv/bin/activate && alembic upgrade head
