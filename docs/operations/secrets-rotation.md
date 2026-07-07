# EIOS — Secrets Rotation Guide

> Alle Secrets sind ausschliesslich als Umgebungsvariablen zu übergeben.  
> Niemals `.env` committen. Niemals Klartext-Secrets in Logs, Responses oder Code.

---

## Übersicht der rotierbaren Secrets

| Variable | Wo genutzt | Rotationsintervall |
|---------|-----------|-------------------|
| `SECRET_KEY` | JWT-Signierung, Board-Portal-Token | 90 Tage oder bei Verdacht |
| `POSTGRES_PASSWORD` | DB-Verbindung (alle Services) | 180 Tage |
| `REDIS_PASSWORD` | Rate-Limiter, Celery-Broker | 180 Tage |
| `REDIS_BLACKLIST_PASSWORD` | Token-Blacklist | 180 Tage |
| `ANTHROPIC_API_KEY` | AI Copilot, LLM | Bei Compromise sofort |
| `OPENAI_API_KEY` | Fallback-LLM | Bei Compromise sofort |
| `GROQ_API_KEY` | Sector Intelligence | Bei Compromise sofort |
| `AWS_SECRET_ACCESS_KEY` | S3 / Evidence-Upload | 90 Tage |

---

## 1. SECRET_KEY rotieren

Der `SECRET_KEY` signiert alle JWTs (Access + Refresh Tokens) und Board-Portal-Share-Links.

**Auswirkung:** Alle aktiven Sessions werden beim nächsten Request ungültig.  
Alle Nutzer müssen sich neu anmelden. Board-Portal-Links werden ungültig.

```bash
# 1. Neuen Key generieren (mind. 32 Zeichen)
python3 -c "import secrets; print(secrets.token_hex(32))"

# 2. In .env (Prod) ersetzen
SECRET_KEY=<neuer-key>

# 3. Backend neu starten
make down && make up

# 4. Verifizieren: alle Sessions laufen ab, Login funktioniert
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@eios.io","password":"..."}'
```

---

## 2. PostgreSQL-Passwort rotieren

**Auswirkung:** Kurze Downtime (~30s) während alle Verbindungen neu aufgebaut werden.

```bash
# 1. Neues Passwort generieren
NEW_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

# 2. In der laufenden DB ändern (zero-downtime: erst DB, dann Env)
docker compose -f docker-compose.prod.yml exec postgres \
  psql -U "$POSTGRES_USER" -c "ALTER USER $POSTGRES_USER PASSWORD '$NEW_PW';"

# 3. .env aktualisieren
POSTGRES_PASSWORD=<neues-passwort>

# 4. Backend + PgBouncer neu starten (DB selbst läuft weiter)
docker compose -f docker-compose.prod.yml restart backend pgbouncer celery-worker

# 5. Health-Check
make health
```

---

## 3. Redis-Passwort rotieren

**Auswirkung:** Alle Redis-Verbindungen brechen kurz ab. Rate-Limit-Counter werden zurückgesetzt.

```bash
# 1. Neues Passwort generieren
NEW_REDIS_PW=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

# 2. Redis-Config live aktualisieren
docker compose -f docker-compose.prod.yml exec redis \
  redis-cli CONFIG SET requirepass "$NEW_REDIS_PW"

# 3. .env aktualisieren (REDIS_PASSWORD + CELERY_BROKER_URL)
REDIS_PASSWORD=<neues-passwort>
CELERY_BROKER_URL=redis://:$NEW_REDIS_PW@redis:6379/2

# 4. Backend + Celery neu starten
docker compose -f docker-compose.prod.yml restart backend celery-worker
```

---

## 4. API-Keys (Anthropic / OpenAI / Groq) rotieren

Bei Kompromittierung: sofort rotieren, kein geplanter Zeitplan abwarten.

```bash
# 1. Neuen Key in der Provider-Konsole erstellen
#    Anthropic: console.anthropic.com → API Keys
#    OpenAI:    platform.openai.com → API Keys
#    Groq:      console.groq.com → API Keys

# 2. Alten Key in der Konsole deaktivieren (NACH dem neuen)

# 3. .env aktualisieren
ANTHROPIC_API_KEY=sk-ant-<neuer-key>

# 4. Backend neu starten (kein Downtime nötig — live reload)
docker compose -f docker-compose.prod.yml restart backend
```

---

## 5. AWS / S3-Credentials rotieren

```bash
# 1. Neuen Access Key in AWS IAM erstellen
# 2. Alten Key deaktivieren (erst nach Test des neuen)

# 3. .env aktualisieren
AWS_ACCESS_KEY_ID=<neue-key-id>
AWS_SECRET_ACCESS_KEY=<neuer-secret>

# 4. Backend neu starten
docker compose -f docker-compose.prod.yml restart backend celery-worker

# 5. Upload-Test
curl -X POST http://localhost:8000/api/v1/evidence/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"
```

---

## Notfallprozedur bei Leak

Falls ein Secret in git oder Logs erscheint:

1. **Sofort** den Key in der Provider-Konsole deaktivieren
2. Neuen Key generieren und deployen (Schritte 1–4 oben)
3. git-History bereinigen: `git filter-repo --path .env --invert-paths`
4. Alle aktiven Sessions invalidieren (SECRET_KEY rotieren)
5. Incident im Audit-Log dokumentieren
6. Bei POSTGRES_PASSWORD oder SECRET_KEY: alle User benachrichtigen

---

## Secrets-Prüfung vor jedem Deploy

```bash
# Sicherstellen dass kein Secret in git gelangt ist
git diff --staged | grep -E "(sk-ant|sk-|AKIA|password|secret)" && echo "WARNING: Possible secret in diff"

# .env niemals im Index
git status | grep ".env" && echo "WARNING: .env tracked"
```
