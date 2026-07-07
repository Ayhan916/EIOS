# EIOS — Production Deployment Runbook

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Erstmalige Installation (First Deploy)](#2-erstmalige-installation)
3. [Upgrade (laufendes System)](#3-upgrade)
4. [Rollback](#4-rollback)
5. [Disaster Recovery](#5-disaster-recovery)
6. [Secrets Rotation](#6-secrets-rotation)
7. [Health Checks](#7-health-checks)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Voraussetzungen

**Server:**
- Ubuntu 22.04 LTS / Debian 12
- 4 vCPU, 16 GB RAM (Minimum für Produktiv-Betrieb)
- 100 GB SSD für Postgres-Daten
- Docker 24+ und Docker Compose v2 installiert

**Secrets vorbereiten:**

```bash
# Auf dem Server:
cp .env.prod.example .env.prod
nano .env.prod   # Alle CHANGE_ME-Werte ersetzen

# Starke Passwörter generieren:
openssl rand -base64 32   # für POSTGRES_PASSWORD, REDIS_PASSWORD, etc.
python3 -c "import secrets; print(secrets.token_hex(32))"  # für SECRET_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # für WEBHOOK_SECRET_KEY
```

**SSL-Zertifikate:**
```bash
# Option A: Let's Encrypt (Certbot)
apt install certbot
certbot certonly --standalone -d app.eios.io
cp /etc/letsencrypt/live/app.eios.io/fullchain.pem nginx/ssl/fullchain.pem
cp /etc/letsencrypt/live/app.eios.io/privkey.pem nginx/ssl/privkey.pem
chmod 600 nginx/ssl/privkey.pem

# Option B: Eigenes Zertifikat
mkdir -p nginx/ssl
cp /path/to/cert.pem nginx/ssl/fullchain.pem
cp /path/to/key.pem nginx/ssl/privkey.pem
```

---

## 2. Erstmalige Installation

```bash
# 1. Repository klonen
git clone https://github.com/your-org/eios.git
cd eios

# 2. Umgebungsdatei befüllen
cp .env.prod.example .env.prod
# → .env.prod vollständig ausfüllen (alle CHANGE_ME ersetzen)

# 3. Backupverzeichnis erstellen
mkdir -p /var/backups/eios/postgres

# 4. Alle Services starten (erster Start lädt Images)
docker compose -f docker-compose.prod.yml --env-file .env.prod pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d postgres redis redis-blacklist

# 5. Warten bis PostgreSQL bereit ist
docker compose -f docker-compose.prod.yml --env-file .env.prod exec postgres \
  pg_isready -U $POSTGRES_USER -d $POSTGRES_DB

# 6. Datenbank-Migrationen ausführen
make migrate
# oder:
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec backend alembic upgrade head

# 7. Alle anderen Services starten
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 8. Demo-Daten seeden (optional — für Erstkunden-Demo)
make seed

# 9. Health prüfen
make health
curl -sf https://app.eios.io/health | python3 -m json.tool
```

**Erwartetes Ergebnis nach erfolgreicher Installation:**
```json
{
  "status": "ok",
  "service": "eios-backend",
  "version": "0.23.0",
  "environment": "production"
}
```

---

## 3. Upgrade

Ein Upgrade besteht immer aus: neue Images → Migration → Rolling Restart.

```bash
# 1. Neues Image von GHCR ziehen
docker compose -f docker-compose.prod.yml --env-file .env.prod pull backend frontend

# 2. Datenbank-Migrationen ausführen (BEVOR die neue Version startet)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm backend alembic upgrade head

# 3. Rolling Restart (keine Downtime)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps backend frontend celery-worker celery-beat

# 4. Health prüfen
make health

# 5. Logs auf Fehler prüfen
docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=100 backend
```

**Kubernetes / Helm:**
```bash
# Über GitHub Actions deploy-prod.yml (empfohlen):
# → Workflow manuell triggern mit dem Image-Tag

# Oder manuell:
helm upgrade eios ./helm/eios \
  --namespace eios-prod \
  -f helm/eios/values.prod.yaml \
  --set image.backend.tag=sha-<commit> \
  --set image.frontend.tag=sha-<commit> \
  --wait --atomic
```

---

## 4. Rollback

### Docker Compose Rollback

```bash
# Vorheriges Image-Tag kennen (aus GHCR oder lokalem Cache)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  stop backend frontend

# Vorheriges Image manuell taggen oder ziehen:
docker pull ghcr.io/your-org/eios-backend:sha-<previous-sha>
docker tag ghcr.io/your-org/eios-backend:sha-<previous-sha> \
           ghcr.io/your-org/eios-backend:latest

docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d backend frontend

# Datenbank-Rollback (NUR wenn Migration rückgängig gemacht werden muss)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm backend alembic downgrade -1
```

### Helm Rollback

```bash
# Letzte erfolgreiche Revision anzeigen
helm history eios -n eios-prod

# Auf bestimmte Revision zurück
helm rollback eios <revision> --namespace eios-prod --wait

# Oder automatisch beim letzten Deploy: --atomic ist gesetzt
# → rollback geschieht automatisch bei Fehler
```

---

## 5. Disaster Recovery

### PostgreSQL aus Backup wiederherstellen

```bash
# 1. Laufende Services stoppen (außer Backup-Container)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  stop backend frontend celery-worker celery-beat

# 2. Backup-Liste aus S3 anzeigen
aws s3 ls s3://eios-backups-prod/postgres/ --recursive

# 3. Gewünschtes Backup herunterladen
aws s3 cp s3://eios-backups-prod/postgres/eios_pg_backup_<timestamp>/ \
  /tmp/eios_restore/ --recursive

# 4. Restore-Script ausführen
./backend/scripts/backup/pg_restore.sh \
  /tmp/eios_restore \
  /var/lib/docker/volumes/eios_postgres_data/_data

# 5. Postgres-Container neustarten
docker compose -f docker-compose.prod.yml --env-file .env.prod restart postgres

# 6. Services wieder hochfahren
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d backend frontend celery-worker celery-beat

# 7. Health prüfen
make health
```

### Manuelle Backup-Prüfung

```bash
# Letztes Backup-Timestamp prüfen (im Backend-Container)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec backend curl -sf http://localhost:8000/health/details | python3 -m json.tool | grep backup
```

---

## 6. Secrets Rotation

**Wann rotieren:** mindestens alle 90 Tage, oder sofort bei Verdacht auf Kompromittierung.

### JWT Secret Key (SECRET_KEY)

```bash
# 1. Neuen Key generieren
NEW_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "Neuer KEY: $NEW_KEY"

# 2. In .env.prod ersetzen
sed -i "s/^SECRET_KEY=.*/SECRET_KEY=$NEW_KEY/" .env.prod

# 3. Backend neu starten (alle aktiven Sessions werden invalidiert!)
# ACHTUNG: Alle eingeloggten User müssen sich neu anmelden.
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps backend celery-worker celery-beat

# 4. Alle aktiven Refresh-Tokens aus Redis löschen (sauber)
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB
```

### PostgreSQL Passwort

```bash
# 1. Neues Passwort generieren
NEW_PW=$(openssl rand -base64 32)

# 2. In PostgreSQL setzen
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec postgres psql -U $POSTGRES_USER -c \
  "ALTER USER $POSTGRES_USER PASSWORD '$NEW_PW';"

# 3. .env.prod aktualisieren
sed -i "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$NEW_PW/" .env.prod

# 4. Backend + PgBouncer neu starten
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps pgbouncer backend celery-worker celery-beat
```

### Redis Passwort

```bash
# 1. Neues Passwort generieren
NEW_PW=$(openssl rand -base64 32)

# 2. .env.prod aktualisieren (REDIS_PASSWORD und alle davon abhängigen URLs)
sed -i "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_PW/" .env.prod

# 3. Redis + alle abhängigen Services neu starten
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps redis backend celery-worker celery-beat

# Gleiches Verfahren für REDIS_BLACKLIST_PASSWORD
```

### API Keys (Anthropic, AWS, etc.)

```bash
# 1. Neuen Key beim Provider generieren
# 2. In .env.prod ersetzen
# 3. Backend neu starten — kein Session-Verlust
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps backend
```

### Webhook Secret

```bash
NEW_SECRET=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
sed -i "s/^WEBHOOK_SECRET_KEY=.*/WEBHOOK_SECRET_KEY=$NEW_SECRET/" .env.prod

# HINWEIS: Alle externen Webhook-Sender müssen mit dem neuen Secret aktualisiert werden.
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --no-deps backend
```

---

## 7. Health Checks

```bash
# Liveness (process alive?)
curl -sf https://app.eios.io/health

# Readiness (DB + Redis)
curl -sf https://app.eios.io/health/ready

# Detaillierte Diagnose (Admin-Token erforderlich)
curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" https://app.eios.io/health/details

# Alle Service-States prüfen
docker compose -f docker-compose.prod.yml --env-file .env.prod ps

# Container-Logs live verfolgen
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f --tail=100 backend

# Prometheus Alertmanager — aktive Alerts
curl -sf http://localhost:9093/api/v2/alerts | python3 -m json.tool
```

**Uptime-Monitoring einrichten (Uptime Kuma / BetterUptime):**
```
Endpoint: https://app.eios.io/health
Intervall: 30 Sekunden
Erwarteter Status: 200
Expected Body enthält: "status":"ok"
Alert-Channel: Slack #eios-oncall
```

---

## 8. Troubleshooting

### Backend startet nicht

```bash
# Logs prüfen
docker compose -f docker-compose.prod.yml --env-file .env.prod logs backend --tail=50

# Häufige Ursachen:
# - DATABASE_URL falsch → postgres-replica oder pgbouncer nicht erreichbar
# - SECRET_KEY fehlt oder < 32 Zeichen
# - Alembic-Migration noch nicht durchgeführt

# Manuelle Migration im Container
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  run --rm backend alembic upgrade head
```

### PostgreSQL-Verbindung schlägt fehl

```bash
# PgBouncer Status prüfen
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec pgbouncer psql -h localhost -p 6432 -U pgbouncer pgbouncer -c "SHOW POOLS;"

# Direkt PostgreSQL testen
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1;"
```

### Redis JWT-Blacklist voll (noeviction!)

```bash
# Speichernutzung prüfen
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec redis-blacklist redis-cli -a $REDIS_BLACKLIST_PASSWORD INFO memory

# Abgelaufene Tokens bereinigen (TTL-basiert — laufen automatisch ab)
# Wenn manuell nötig: abgelaufene Keys mit SCAN + TTL < 0 löschen
```

### Nginx SSL-Fehler

```bash
# Zertifikat-Ablauf prüfen
openssl x509 -in nginx/ssl/fullchain.pem -noout -dates

# Let's Encrypt erneuern
certbot renew
cp /etc/letsencrypt/live/app.eios.io/fullchain.pem nginx/ssl/fullchain.pem
cp /etc/letsencrypt/live/app.eios.io/privkey.pem nginx/ssl/privkey.pem
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec nginx nginx -s reload
```

### Automatische SSL-Zertifikat-Erneuerung einrichten

```bash
# Cronjob für certbot (täglich prüfen, < 30 Tage Restlaufzeit → erneuern)
crontab -e
# Folgende Zeile einfügen:
0 3 * * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/app.eios.io/fullchain.pem /path/to/eios/nginx/ssl/ && \
  cp /etc/letsencrypt/live/app.eios.io/privkey.pem /path/to/eios/nginx/ssl/ && \
  docker exec eios-nginx nginx -s reload
```

---

## Kontakt

Bei Produktions-Incidents: Slack `#eios-oncall` oder PagerDuty.
Für Deployments: nur über GitHub Actions (`deploy-prod.yml` mit manueller Bestätigung).
