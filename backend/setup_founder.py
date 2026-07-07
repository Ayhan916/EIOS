"""
One-time script: create the Founder admin account in EIOS.

Run from the backend/ directory:
    source .venv/bin/activate
    python setup_founder.py

Safe to re-run — skips creation if the e-mail already exists.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

import asyncpg
import bcrypt

# ── Config ────────────────────────────────────────────────────────────────────

EMAIL = "ayhan.yaman1@icloud.com"
PASSWORD = "Founder2026!"
ROLE = "admin"
ORG_NAME = "EIOS"

_RAW_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://eios:eios_dev@localhost:5432/eios_db",
)
# asyncpg uses plain postgresql:// scheme
DSN = _RAW_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
    "postgresql+psycopg2://", "postgresql://"
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    try:
        conn = await asyncpg.connect(DSN)
    except Exception as e:
        print(f"\n[ERROR] Cannot connect to database: {e}")
        print(f"        DSN used: {DSN}")
        print("        Make sure PostgreSQL is running and migrations have been applied.")
        sys.exit(1)

    async with conn.transaction():
        # Check if user already exists
        existing = await conn.fetchrow("SELECT id, role FROM users WHERE email = $1", EMAIL)
        if existing:
            print(f"\n[OK] User already exists (id={existing['id']}, role={existing['role']})")
            print(f"     E-Mail : {EMAIL}")
            await conn.close()
            return

        now = _now()
        user_id = str(uuid.uuid4())

        # Reuse or create organisation
        org_row = await conn.fetchrow(
            "SELECT id FROM organizations WHERE name = $1 LIMIT 1", ORG_NAME
        )
        if org_row:
            org_id = org_row["id"]
            print(f"[INFO] Reusing existing organization (id={org_id})")
        else:
            org_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO organizations
                    (id, name, created_at, updated_at, created_by, updated_by, version)
                VALUES ($1, $2, $3, $4, $5, $6, 1)
                """,
                org_id,
                ORG_NAME,
                now,
                now,
                user_id,
                user_id,
            )
            print(f"[INFO] Created organization '{ORG_NAME}' (id={org_id})")

        pw_hash = _hash(PASSWORD)
        await conn.execute(
            """
            INSERT INTO users
                (id, email, display_name, password_hash, role, organization_id,
                 is_active, version, created_at, updated_at, created_by, updated_by)
            VALUES
                ($1, $2, $3, $4, $5, $6,
                 TRUE, 1, $7, $8, $9, $10)
            """,
            user_id,
            EMAIL,
            "Ayhan Yaman",
            pw_hash,
            ROLE,
            org_id,
            now,
            now,
            user_id,
            user_id,
        )

    await conn.close()

    print()
    print("=" * 52)
    print("  EIOS Founder Account erstellt")
    print("=" * 52)
    print(f"  E-Mail     : {EMAIL}")
    print(f"  Passwort   : {PASSWORD}")
    print(f"  Rolle      : {ROLE}")
    print(f"  Org-ID     : {org_id}")
    print(f"  User-ID    : {user_id}")
    print("=" * 52)
    print("  Bitte Passwort nach dem ersten Login aendern.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
