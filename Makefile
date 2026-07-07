.PHONY: help up down build logs migrate seed test lint health backup first-deploy ssl-renew restart-backend

COMPOSE_PROD = docker compose -f docker-compose.prod.yml --env-file .env.prod
COMPOSE_DEV  = docker compose -f docker-compose.yml
BACKEND      = cd backend &&
ENV_FILE     = .env.prod

help:
	@echo ""
	@echo "EIOS — Production Operations"
	@echo "─────────────────────────────────────────────"
	@echo "  make first-deploy    First-time production setup"
	@echo "  make up              Start all production services"
	@echo "  make down            Stop all services"
	@echo "  make build           Rebuild images (no cache)"
	@echo "  make logs            Tail all service logs"
	@echo "  make migrate         Run Alembic migrations"
	@echo "  make seed            Seed demo organisation data"
	@echo "  make test            Run backend unit tests"
	@echo "  make lint            Run ruff + mypy"
	@echo "  make health          Check service health endpoints"
	@echo "  make backup          Trigger manual DB backup"
	@echo "  make ssl-renew       Renew Let's Encrypt certificate"
	@echo "  make restart-backend Rolling restart backend + workers"
	@echo ""

first-deploy:
	@test -f $(ENV_FILE) || (echo "ERROR: $(ENV_FILE) not found. Run: cp .env.prod.example .env.prod" && exit 1)
	@test -f nginx/ssl/fullchain.pem || (echo "ERROR: nginx/ssl/fullchain.pem not found. See deployment/DEPLOYMENT.md §1" && exit 1)
	$(COMPOSE_PROD) pull
	$(COMPOSE_PROD) up -d postgres redis redis-blacklist
	@echo "Waiting for PostgreSQL..."
	@for i in $$(seq 1 20); do \
	  $(COMPOSE_PROD) exec postgres pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB && break; \
	  sleep 3; \
	done
	$(COMPOSE_PROD) run --rm backend alembic upgrade head
	$(COMPOSE_PROD) up -d
	@echo ""
	@echo "✅ EIOS is up. Health:"
	@curl -sf http://localhost:8000/health | python3 -m json.tool || echo "FAILED — check: make logs"

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

restart-backend:
	$(COMPOSE_PROD) up -d --no-deps backend celery-worker celery-beat
	@echo "Backend and workers restarted."

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
	$(COMPOSE_PROD) exec postgres-backup pg_backup.sh --s3
	@echo "Backup triggered. Check logs: make logs"

ssl-renew:
	certbot renew --quiet
	cp /etc/letsencrypt/live/$(DOMAIN)/fullchain.pem nginx/ssl/fullchain.pem
	cp /etc/letsencrypt/live/$(DOMAIN)/privkey.pem nginx/ssl/privkey.pem
	$(COMPOSE_PROD) exec nginx nginx -s reload
	@echo "SSL certificate renewed and Nginx reloaded."

# ── Development shortcuts ──────────────────────────────────────────────────────

dev-up:
	$(COMPOSE_DEV) up -d

dev-down:
	$(COMPOSE_DEV) down

dev-logs:
	$(COMPOSE_DEV) logs -f --tail=50

dev-migrate:
	$(BACKEND) source .venv/bin/activate && alembic upgrade head
