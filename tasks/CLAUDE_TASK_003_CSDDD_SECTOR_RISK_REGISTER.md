# CLAUDE TASK 003 — CSDDD Sector Risk Register

## Status
COMPLETED — alle 7 Phasen implementiert und getestet (2026-07-02)

## Genehmigt von
Founder (2026-07-01)

## Ziel
AI-gestütztes, sektorspezifisches Risikoregister auf Basis von 2-stelligen NACE-Codes,
CSDDD-geschützten Rechten (Annex I), Wahrscheinlichkeitsskala 1–10 und
Szenario-Simulation. Catena-X-kompatibel. Deterministisch und auditierbar (M43).

---

## Gesamtarchitektur

```
OFFLINE (Kalibrierung)
  ILO/OECD PDFs → pgvector Chunks → Groq → Score-Vorschläge
  → Human Review (Founder) → Matrix eingefroren (DB)

RUNTIME (deterministisch, auditierbar)
  News (GDELT) → Sektor-Aggregation → Pattern Match
  → Szenario-Vorschlag → Human-Confirm
  → Simulation Engine: Base × Faktoren = Szenario-Score
  → Catena-X API Output
```

---

## Architekturregeln (nicht verhandelbar)

- M43: Scoring deterministisch, auditierbar, erklärbar — kein LLM-Scoring
- M44: Keine generativen Forecasts — Simulation auf Basis fixer Faktoren
- LLM (Groq) nur für Kalibrierung offline — nie für Live-Scoring
- Jede Score-Änderung erfordert Founder-Genehmigung
- organization_id Pflicht-Filter auf allen DB-Queries

---

## Phase 1 — Domain Foundation
**Aufwand:** 2 Tage  
**Status:** [x] DONE — 2026-07-01

### Dateien
- `backend/domain/enums.py` — Neue Enums anhängen
- `backend/domain/sector_risk_register.py` — Neue Domain-Entities (neue Datei)

### Aufgaben
- [ ] `CSDDDRight` Enum (21 Rechte aus CSDDD Annex I)
- [ ] `ScenarioType` Enum (6 Typen)
- [ ] `SectorRightScore` Dataclass
- [ ] `ScenarioTemplate` Dataclass
- [ ] `SimulationResult` Dataclass
- [ ] `CalibrationSuggestion` Dataclass (pending / approved)
- [ ] `ScenarioSuggestion` Dataclass (news-triggered, pending / active)

### CSDDDRight Enum (vollständig)
```python
class CSDDDRight(str, Enum):
    CHILD_LABOUR = "child_labour"              # ILO C138, C182
    FORCED_LABOUR = "forced_labour"            # ILO C029, C105
    FREEDOM_OF_ASSOCIATION = "freedom_of_association"  # ILO C087
    COLLECTIVE_BARGAINING = "collective_bargaining"    # ILO C098
    DISCRIMINATION = "discrimination"          # ILO C100, C111
    MINIMUM_WAGE = "minimum_wage"              # ILO C131
    WORKING_HOURS = "working_hours"            # ILO C001
    OCCUPATIONAL_SAFETY = "occupational_safety"        # ILO C155
    LAND_RIGHTS = "land_rights"
    WATER_RIGHTS = "water_rights"
    ENVIRONMENTAL_DESTRUCTION = "environmental_destruction"
    HARMFUL_CHEMICALS = "harmful_chemicals"    # Minamata, Stockholm
    BIODIVERSITY = "biodiversity"              # CBD
    MERCURY = "mercury"
    HAZARDOUS_WASTE = "hazardous_waste"        # Basel Convention
    PRIVACY = "privacy"                        # ICCPR Art. 17
    FREEDOM_OF_EXPRESSION = "freedom_of_expression"
    HUMAN_DIGNITY = "human_dignity"
    MODERN_SLAVERY = "modern_slavery"
    MIGRANT_WORKER_RIGHTS = "migrant_worker_rights"
    COMMUNITY_RIGHTS = "community_rights"
```

### ScenarioType Enum
```python
class ScenarioType(str, Enum):
    GEOPOLITICAL_CONFLICT = "geopolitical_conflict"
    SANCTIONS_ESCALATION = "sanctions_escalation"
    NATURAL_DISASTER = "natural_disaster"
    REGULATORY_CHANGE = "regulatory_change"
    LABOUR_UNREST = "labour_unrest"
    SUPPLY_SHORTAGE = "supply_shortage"
```

---

## Phase 2 — Statische Basis-Matrix
**Aufwand:** 3 Tage  
**Status:** [x] DONE — 2026-07-01  
**Abhängigkeit:** Phase 1 abgeschlossen

### Dateien
- `backend/application/sector_intelligence/nace_taxonomy.py` — neue Datei
- `backend/application/sector_intelligence/base_matrix.py` — neue Datei
- `backend/application/sector_intelligence/profiles.py` — `get_profile()` anpassen für 2-digit

### Aufgaben
- [ ] `nace_taxonomy.py`: alle 88 NACE-2-digit-Codes → Section-Mapping
- [ ] `base_matrix.py`: 20 Kernsektoren × 21 Rechte = 420 Scores (1–10)
- [ ] `get_profile()` in `profiles.py` für numerische 2-digit-Codes erweitern
- [ ] Alembic-Migration für `sector_right_scores` Tabelle
- [ ] Alembic-Migration für `calibration_suggestions` Tabelle
- [ ] Alembic-Migration für `scenario_suggestions` Tabelle

### Kernsektoren (Priorität Catena-X)
| NACE | Sektor | Priorität |
|------|--------|-----------|
| 29 | Motor vehicles (Automotive) | ★★★ Catena-X Kern |
| 26 | Electronics | ★★★ |
| 13 | Textiles | ★★★ |
| 01 | Agriculture | ★★★ |
| 05 | Mining (coal) | ★★★ |
| 07 | Mining (metal ores) | ★★★ |
| 49 | Land transport / Logistics | ★★ |
| 20 | Chemicals | ★★ |
| 10 | Food manufacturing | ★★ |
| 14 | Clothing / Apparel | ★★ |
| 23 | Non-metallic minerals (cement) | ★★ |
| 24 | Basic metals | ★★ |
| 28 | Machinery | ★★ |
| 62 | IT / Software | ★ |
| 69 | Legal services | ★ |
| 70 | Consulting (M) | ★ |
| 41 | Construction | ★★ |
| 35 | Energy / Electricity | ★★ |
| 46 | Wholesale trade | ★ |
| 86 | Health care | ★ |

### Score-Quellen (für Kalibrierung)
- CSDDD Annex I (primär)
- ILO Sector-specific labour reports
- OECD Due Diligence Guidance for Responsible Supply Chains
- Know The Chain Benchmark Reports (Textiles, Electronics, Food)
- Transparency International CPI (governance proxy)

---

## Phase 3 — RAG Kalibrierungspipeline
**Aufwand:** 3 Tage  
**Status:** [x] DONE — 2026-07-02  
**Abhängigkeit:** Phase 1 + 2 abgeschlossen

### Dateien
- `backend/application/sector_intelligence/rag_calibration.py` — neue Datei
- `backend/interfaces/api/routers/sector_risk_register.py` — Calibrate-Endpoints

### Aufgaben
- [ ] `SectorRiskCalibrationPipeline` Klasse
- [ ] RAG-Query-Logik (EvidenceChunkSearchAdapter, pgvector)
- [ ] Groq-Prompt für Score-Extraktion (CALIBRATION_PROMPT)
- [ ] Parsing: LLM-Response → `CalibrationSuggestion`
- [ ] `POST /api/v1/sector-risk-register/calibrate` Endpoint
- [ ] `POST /api/v1/sector-risk-register/calibrate/{id}/approve` Endpoint
- [ ] `GET /api/v1/sector-risk-register/calibrate/suggestions` Endpoint

### Calibration Prompt Template
```
Du bist ein ESG-Experte. Analysiere den folgenden Text und schätze die
Wahrscheinlichkeit des Risikos "{right}" im Sektor NACE {nace} auf einer Skala
von 1 (sehr unwahrscheinlich) bis 10 (sehr wahrscheinlich).

Kontext aus ILO/OECD-Berichten:
{context}

Antworte ausschließlich in diesem JSON-Format:
{"probability": <1-10>, "confidence": "<Low|Medium|High>", "reasoning": "<max 200 Zeichen>", "sources": ["..."]}
```

---

## Phase 4 — News → Szenario-Trigger
**Aufwand:** 2 Tage  
**Status:** [x] DONE — 2026-07-02  
**Abhängigkeit:** Phase 1 abgeschlossen

### Dateien
- `backend/application/sector_intelligence/news_scenario_detector.py` — neue Datei
- `backend/interfaces/api/routers/sector_risk_register.py` — Scenario-Endpoints

### Aufgaben
- [ ] `_SCENARIO_KEYWORDS` Dict (alle 6 Typen)
- [ ] `_NACE_KEYWORDS` Dict: Sektor-Schlüsselwörter → NACE-Code
- [ ] `NewsScenarioDetector.detect()` — aggregiert Artikel nach NACE + Szenario
- [ ] Schwellenwert-Logik (default: >5 Artikel in 7 Tagen → Vorschlag)
- [ ] `GET /api/v1/scenarios/suggestions` Endpoint
- [ ] `POST /api/v1/scenarios/suggestions/{id}/activate` Endpoint
- [ ] Integration in bestehende News-Pipeline (news_service.py)

### Keyword-Mapping (Beispiel)
```python
_SCENARIO_KEYWORDS = {
    ScenarioType.GEOPOLITICAL_CONFLICT: {
        "war", "conflict", "invasion", "military", "crisis", "blockade",
        "Krieg", "Konflikt", "Invasion"
    },
    ScenarioType.LABOUR_UNREST: {
        "strike", "walkout", "protest", "union", "workers demand",
        "Streik", "Gewerkschaft", "Protest"
    },
    ScenarioType.REGULATORY_CHANGE: {
        "regulation", "ban", "directive", "CSDDD", "LkSG", "compliance deadline"
    },
    ScenarioType.SANCTIONS_ESCALATION: {
        "sanctions", "embargo", "blacklist", "restriction", "Sanktionen"
    },
    ScenarioType.NATURAL_DISASTER: {
        "flood", "earthquake", "hurricane", "drought", "wildfire"
    },
    ScenarioType.SUPPLY_SHORTAGE: {
        "shortage", "scarcity", "disruption", "bottleneck", "chip shortage"
    },
}
```

---

## Phase 5 — Simulation Engine
**Aufwand:** 2 Tage  
**Status:** [x] DONE — 2026-07-01  
**Abhängigkeit:** Phase 1 + 2 abgeschlossen

### Dateien
- `backend/application/sector_intelligence/simulation_engine.py` — neue Datei

### Aufgaben
- [ ] `_SCENARIO_TEMPLATES` Dict mit allen 6 Templates
- [ ] `ScenarioSimulationEngine.simulate()` — deterministisch
- [ ] Faktor-Anwendung: `min(10, round(base × factor))`
- [ ] Erklärungstext-Generierung pro Right (ohne LLM)
- [ ] `GET /api/v1/sector-risk-register/{nace}/simulate?scenario=X` Endpoint

### Szenario-Templates (vollständig)
```python
_SCENARIO_TEMPLATES = {
    ScenarioType.GEOPOLITICAL_CONFLICT: ScenarioTemplate(
        scenario_type=ScenarioType.GEOPOLITICAL_CONFLICT,
        name="Geopolitischer Konflikt / Kriegsgebiet",
        factors={
            CSDDDRight.FORCED_LABOUR: 1.5,
            CSDDDRight.OCCUPATIONAL_SAFETY: 1.4,
            CSDDDRight.ENVIRONMENTAL_DESTRUCTION: 1.2,
            CSDDDRight.MIGRANT_WORKER_RIGHTS: 1.6,
            CSDDDRight.MODERN_SLAVERY: 1.4,
            CSDDDRight.FREEDOM_OF_EXPRESSION: 1.5,
        },
        affected_nace_sections=["A", "B", "C", "H"],
        sources=["ILO 2024 Conflict Risk Report"],
    ),
    ScenarioType.LABOUR_UNREST: ScenarioTemplate(
        factors={
            CSDDDRight.FREEDOM_OF_ASSOCIATION: 1.6,
            CSDDDRight.COLLECTIVE_BARGAINING: 1.6,
            CSDDDRight.WORKING_HOURS: 1.4,
            CSDDDRight.MINIMUM_WAGE: 1.5,
            CSDDDRight.OCCUPATIONAL_SAFETY: 1.3,
        },
        ...
    ),
    # ... alle 6 Templates
}
```

---

## Phase 6 — API + Catena-X Output
**Aufwand:** 2 Tage  
**Status:** [x] DONE — 2026-07-01 (Kern-Endpoints; Calibrate/Approve Endpoints folgen mit Phase 3)  
**Abhängigkeit:** Phase 1–5 abgeschlossen

### Dateien
- `backend/interfaces/api/routers/sector_risk_register.py` — Haupt-Router (vollständig)
- `backend/app/main.py` — Router registrieren

### Endpoints (vollständig)
```
GET  /api/v1/sector-risk-register/
GET  /api/v1/sector-risk-register/{nace_code}
GET  /api/v1/sector-risk-register/{nace_code}/simulate?scenario=X
POST /api/v1/sector-risk-register/calibrate
POST /api/v1/sector-risk-register/calibrate/{id}/approve
GET  /api/v1/scenarios/suggestions
POST /api/v1/scenarios/suggestions/{id}/activate
```

### Catena-X Output-Schema
```json
{
  "naceCode": "29",
  "sectorName": "Manufacture of motor vehicles",
  "assessmentDate": "2026-07-01",
  "calibrationVersion": "v1.0",
  "csdddRights": [
    {
      "rightId": "forced_labour",
      "rightName": "Forced Labour (ILO C029, C105)",
      "baselineProbability": 4,
      "confidenceLevel": "High",
      "sources": ["ILO 2024 Automotive Sector Report"],
      "scenario": {
        "type": "geopolitical_conflict",
        "adjustedProbability": 6,
        "delta": 2,
        "factor": 1.5,
        "explanation": "Increased by factor 1.5 under geopolitical conflict scenario."
      }
    }
  ]
}
```

---

## Phase 7 — Tests
**Aufwand:** 2 Tage  
**Status:** [x] DONE — 2026-07-02 (157 Tests, alle grün; 2 Bugs gefunden und behoben)  
**Abhängigkeit:** Phase 1–6 abgeschlossen

### Dateien
- `backend/tests/unit/test_simulation_engine.py`
- `backend/tests/unit/test_nace_taxonomy.py`
- `backend/tests/integration/test_rag_calibration.py`
- `backend/tests/api/test_sector_risk_register.py`

### Aufgaben
- [ ] Unit: Simulation deterministisch (gleicher Input → gleicher Output)
- [ ] Unit: Faktor-Grenzwert (Ergebnis immer 1–10)
- [ ] Unit: NACE-Mapping alle 88 Codes vorhanden
- [ ] Unit: CSDDDRight Enum hat exakt 21 Werte
- [ ] Integration: RAG-Pipeline (mock Groq, echter pgvector)
- [ ] API: alle 8 Endpoints mit httpx
- [ ] M43-Compliance-Test: kein LLM-Aufruf im simulate()-Pfad

---

## Abhängigkeitsgraph

```
Phase 1 (Domain)
    ├── Phase 2 (Matrix)
    │       ├── Phase 5 (Simulation Engine)
    │       │       └── Phase 6 (API) ──→ Phase 7 (Tests)
    │       └── Phase 3 (RAG) ──────────→ Phase 6 (API)
    └── Phase 4 (News Trigger) ──────────→ Phase 6 (API)
```

**Phase 1 + 2 zuerst** (kein Risiko, keine externe Abhängigkeit).  
**Phase 3 + 4 + 5 parallel möglich** nach Phase 2.

---

## Zeitplan

| Phase | Inhalt | Aufwand | Status |
|-------|--------|---------|--------|
| 1 | Domain Foundation | 2 Tage | [x] DONE 2026-07-01 |
| 2 | Basis-Matrix (20 × 21) | 3 Tage | [x] DONE 2026-07-01 |
| 3 | RAG Kalibrierung | 3 Tage | [x] DONE 2026-07-02 |
| 4 | News → Szenario-Trigger | 2 Tage | [x] DONE 2026-07-02 |
| 5 | Simulation Engine | 2 Tage | [x] DONE 2026-07-01 |
| 6 | API + Catena-X Output | 2 Tage | [x] DONE 2026-07-01 |
| 7 | Tests | 2 Tage | [x] DONE 2026-07-02 (198 Tests total) |
| **Total** | | **~16 Tage** | **ALLE PHASEN ABGESCHLOSSEN** |

---

## Protokoll

| Datum | Phase | Aktion | Von |
|-------|-------|--------|-----|
| 2026-07-01 | — | Plan erstellt und genehmigt | Founder + Claude |
| 2026-07-01 | 1 | Domain Foundation implementiert: CSDDDRight (21), ScenarioType (6), CalibrationStatus, ScenarioSuggestionStatus Enums + 6 Domain-Dataclasses | Claude |
| 2026-07-01 | 2 | Statische Basis-Matrix: nace_taxonomy.py (88 Codes), base_matrix.py (20 Sektoren × 21 Rechte), profiles.py 2-digit Support, Migration 075 | Claude |
| 2026-07-01 | 5 | Simulation Engine: 6 Szenario-Templates, deterministisch, M43-compliant, Determinismus-Test bestanden | Claude |
| 2026-07-01 | 6 | API Router: 4 Endpoints (/list, /{nace}, /{nace}/simulate, /scenarios/templates), OpenAPI verifiziert | Claude |
| 2026-07-02 | 7 | 157 Tests geschrieben und grün: Enums (16), Taxonomie (14), Matrix (16), Simulation (63), API (48). 2 Bugs entdeckt+behoben: get_scores() Mutation-Bug, normalize_nace() single-digit Bug | Claude |
| 2026-07-02 | 3 | RAG Kalibrierung: SectorRiskCalibrationPipeline, Groq-Prompt, JSON-Parsing (fences/embedded/fallback), CalibrationSuggestionDTO, save/approve/reject/list DB-Helpers, 4 Router-Endpoints. 20 Tests grün. | Claude |
| 2026-07-02 | 4 | News → Szenario-Trigger: NewsScenarioDetector, _SCENARIO_KEYWORDS (6 Typen, EN+DE), _NACE_SECTOR_KEYWORDS (15 Sektoren), 7-Tage-Lookback, Schwellenwert 5 Artikel, save/activate/dismiss/list DB-Helpers, 4 Router-Endpoints. 21 Tests grün. | Claude |
