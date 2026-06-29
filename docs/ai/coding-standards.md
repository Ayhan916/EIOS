# Coding Standards — EIOS

> Verbindlich für alle Implementierungen. Claude Code prüft diese Regeln vor jeder Implementierung.

---

## Architektur

### Clean Architecture — Dependency Rule (strikt)

```
Domain Layer          → hängt von NICHTS ab
Application Layer     → hängt nur von Domain ab
Infrastructure Layer  → implementiert Interfaces aus Application
Interface Layer       → hängt von Application ab, nicht von Domain direkt
```

**Verletzungen sind Blocker — kein Merge ohne Fix.**

### Verbotene Imports (werden automatisch geprüft)

```python
# ❌ Domain darf NICHT importieren:
from sqlalchemy import ...
from fastapi import ...
import redis

# ❌ Application darf NICHT importieren:
from sqlalchemy import ...
from fastapi import ...

# ✓ Erlaubt in Domain:
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from uuid import UUID
```

---

## Backend (Python / FastAPI)

### Namenskonventionen

| Element | Konvention | Beispiel |
|---------|-----------|---------|
| Dateien | `snake_case.py` | `supplier_health_service.py` |
| Klassen | `PascalCase` | `SupplierHealthScore` |
| Funktionen | `snake_case` | `calculate_health_score()` |
| Konstanten | `UPPER_SNAKE` | `DEFAULT_SCORE_WEIGHT` |
| Private | `_underscore` | `_normalize_name()` |
| Async | Prefix `async def` | `async def get_supplier()` |

### Service-Layer Regeln

```python
# ✓ Services verwenden session.flush() — NIE session.commit()
async def create_supplier(session: AsyncSession, data: SupplierCreate) -> Supplier:
    supplier = Supplier(**data.model_dump())
    session.add(supplier)
    await session.flush()   # ✓
    return supplier

# ✓ Router besitzen session.commit()
@router.post("/suppliers")
async def create_supplier_endpoint(data: SupplierCreate, session: AsyncSession = Depends(get_session)):
    supplier = await supplier_service.create_supplier(session, data)
    await session.commit()  # ✓ — nur hier
    return SupplierResponse.model_validate(supplier)
```

### Multi-Tenancy — Pflichtfilter

```python
# ✓ JEDE Query muss organization_id filtern
result = await session.execute(
    select(Supplier).where(
        Supplier.organization_id == current_org.id,  # ← PFLICHT
        Supplier.id == supplier_id
    )
)

# ❌ Query ohne organization_id ist ein Sicherheitsfehler
result = await session.execute(select(Supplier).where(Supplier.id == supplier_id))
```

### Sicherheit

```python
# ✓ Secrets ausschließlich als Umgebungsvariablen
import os
SECRET_KEY = os.environ["SECRET_KEY"]   # ✓

# ❌ Nie hardcoden
SECRET_KEY = "mein-geheimes-passwort"   # ❌ — Blocker

# ✓ Passwort-Hash NIEMALS in API-Response
class UserResponse(BaseModel):
    id: UUID
    email: str
    # password_hash: str  ← ❌ VERBOTEN
```

### Scoring Engine — Determinismus

```python
# ✓ Alle M43/M44 Berechnungen deterministisch und auditierbar
# ❌ Kein LLM-basiertes Scoring
# ❌ Keine Black-Box Modelle

def calculate_health_score(signals: list[ScoringSignal]) -> HealthScore:
    """
    Deterministisch. Jede Eingabe erzeugt dieselbe Ausgabe.
    Alle Gewichte sind Konstanten, keine gelernten Parameter.
    """
    ...
```

### Fehlerbehandlung

```python
# ✓ Domänen-Exceptions für erwartete Fehler
class SupplierNotFoundError(DomainError):
    pass

# ✓ HTTP-Exceptions nur im Interface Layer
@router.get("/suppliers/{id}")
async def get_supplier(id: UUID):
    try:
        return await supplier_service.get(id)
    except SupplierNotFoundError:
        raise HTTPException(status_code=404, detail="Supplier not found")
```

---

## Datenbank (PostgreSQL / SQLAlchemy)

### Modell-Konventionen

```python
class Supplier(Base):
    __tablename__ = "suppliers"

    # Pflichtfelder auf JEDEM Modell:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())
```

### Migrationen

- Jede Schema-Änderung = neue Alembic-Migration
- Migration-Dateien sind unveränderlich nach Merge
- `alembic upgrade head` wird niemals ohne Review ausgeführt
- Destructive Migrationen (DROP, TRUNCATE) erfordern explizite Genehmigung

### Indizes

```python
# ✓ Composite Index für Multi-Tenancy Queries
__table_args__ = (
    Index("ix_suppliers_org_name", "organization_id", "name"),
)
```

---

## Frontend (React / TypeScript)

### Namenskonventionen

| Element | Konvention | Beispiel |
|---------|-----------|---------|
| Komponenten | `PascalCase.tsx` | `SupplierHealthCard.tsx` |
| Hooks | `camelCase.ts` | `useSupplierHealth.ts` |
| Utility | `camelCase.ts` | `formatHealthScore.ts` |
| Types | `PascalCase` | `SupplierHealthScore` |
| CSS-Klassen | Tailwind (kein Custom CSS ohne Grund) | `bg-red-500` |

### Komponenten-Regeln

```typescript
// ✓ Props immer typisiert
interface SupplierCardProps {
  supplierId: string;
  onSelect?: (id: string) => void;
}

// ✓ Keine direkten API-Calls in Komponenten — nur über Hooks
const { data, isLoading } = useSupplierHealth(supplierId);  // ✓
const data = await fetch('/api/suppliers/' + id);            // ❌

// ✓ Fehler immer behandeln
if (error) return <ErrorBoundary error={error} />;
```

---

## Tests

### Mindestanforderungen

| Art | Minimum | Tool |
|-----|---------|------|
| Unit Tests | Jede Service-Methode | pytest |
| Integration Tests | Jeder API-Endpunkt | pytest + httpx |
| E2E Tests | Jeder kritische Workflow | pytest-asyncio |

### Test-Konventionen

```python
# ✓ Test-Name beschreibt Verhalten, nicht Implementierung
def test_supplier_health_score_drops_on_sanction_match():  # ✓
def test_calculate():                                        # ❌

# ✓ Arrange / Act / Assert
async def test_sanction_match_triggers_alert(session, org):
    # Arrange
    supplier = await create_test_supplier(session, org)

    # Act
    await sanction_service.process_match(session, supplier.id, "EU_LIST")

    # Assert
    events = await intelligence_service.get_events(session, supplier.id)
    assert any(e.event_type == "SANCTION_MATCH" for e in events)
```

### Was NIE gemockt wird

- Datenbankzugriffe in Integrationstests (echte Test-DB)
- Die Scoring-Engine (deterministisch, muss real berechnet werden)
- Auth-Middleware in Security-Tests

---

## KI-Agenten — Einschränkungen (architektonisch durchgesetzt)

```python
# ❌ Agenten dürfen NIEMALS:
agent.approve_assessment()      # ← verboten
agent.close_finding()           # ← verboten
agent.resolve_compliance_gap()  # ← verboten
agent.approve_evidence()        # ← verboten
agent.close_risk()              # ← verboten

# ✓ Agenten dürfen NUR:
agent.create_draft_recommendation()
agent.notify_human()
agent.escalate_to_reviewer()
agent.summarize_findings()
```

---

## Commit-Konventionen

```
feat(supplier): add health score recalculation on sanction match
fix(auth): prevent password_hash from appearing in UserResponse
docs(api): add missing endpoint documentation for /suppliers/{id}
test(scoring): add property-based tests for health score formula
refactor(health): extract dimension calculator into separate service
chore(deps): update fastapi to 0.115.0
```

Format: `type(scope): beschreibung` — immer Englisch, Kleinbuchstaben.

---

## Security Checklist (vor jedem PR)

- [ ] Keine Secrets im Code (ANTHROPIC_API_KEY, SECRET_KEY, DB-Passwörter)
- [ ] `password_hash` erscheint in keiner API-Response
- [ ] Alle Queries filtern nach `organization_id`
- [ ] Keine SQL-Injection möglich (nur ORM / parameterisierte Queries)
- [ ] Eingaben am System-Boundary validiert (Pydantic)
- [ ] Keine `eval()`, `exec()`, `subprocess` mit User-Input
