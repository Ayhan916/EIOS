# IMPLEMENTATION_PLAN.md — Implementierungsplan
**Status: ACTIVE — Version 1.0 (2026-07-09)**
**Authority: Lead AI Architect**
**Prinzip: Enterprise Quality over Feature Velocity**

---

## Aktueller Stand (IST-Analyse)

### Was funktioniert ✅
- Document Ingestion Pipeline (PDF → Chunks → Embeddings)
- RAG mit pgvector (multilingual-e5-large, 1024d, cosine similarity)
- Copilot Service mit Intent-Detection, Context Assembly, Contradiction Detection
- Metric Extractor (Groq 8B — mit bekannten Limitierungen, ADR-007)
- Assessment, Finding, Risk, Evidence als Domain Entities
- CSDDD Routen (6 Routen, 200 OK)
- Company Metrics + Signals (149 Metriken, 54 Signale aus Prev. Run)
- Compliance Gap Tracking
- Freshness Analysis + Citation Extraction

### Was fehlt / ist fehlerhaft ❌
- Deterministischer Risk Score Calculator (ADR-002)
- CSDDD Obligation Rule Engine (ADR-010)
- Hybrid Search BM25 + pgvector + RRF (ADR-008)
- Parent-Child Chunking für Annual Reports (ADR-009)
- Immutable Audit Log mit Hash-Chain (ADR-006)
- Prompt Versioning (ADR-011)
- Entity Linker (Signal → Supplier-ID Mapping)
- Supply Chain Graph (Tier-2/3 Edges)
- Explainability Layer (Risk Score Breakdown)
- ConfidenceCard Standardisierung (ADR-015)
- Metric Extraction: Groq 8B → Claude Haiku (ADR-007)

### Bekannte Schulden
- `risk.py` Domain Entity: kein composite RiskScore, kein formulaVersion
- `evidence.py` Domain Entity: kein direktes Finding-Linking
- `assessment.py`: Review Lifecycle vorhanden, aber kein Immutability-Gate nach Approval
- Context Budget `_MAX_CHARS = 28_000`: korrekt, aber Retrieval noch reine Vektorsuche
- `run_extract_all.py`: noch Groq 8B, muss auf Haiku migriert werden

---

## Epics und Features

### EPIC 1 — Intelligence Quality (Datenqualität verbessern)
**Priorität: HOCH — alles andere baut darauf auf**
**Abhängigkeiten: keine**

---

#### E1-F1 — Metric Extraction auf Claude Haiku migrieren
**Ref: ADR-007**  
**Aufwand: 0,5 Tage**  
**Status: TODO**

**Hintergrund:**
Groq 8B liefert 0 Metriken für Annual Reports 2022-2025 (250+ Chunks). Root Cause: Modell zu schwach für deutschen Finanztext, Token-Limit (6k), Tabellen-Fragmentierung.

**Aufgaben:**
1. `run_extract_all.py`: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-haiku-4-5-20251001`
2. Anthropic API Key in `.env` sicherstellen
3. Rate-Limit-Logik anpassen (Anthropic ≠ Groq Limits)
4. Testlauf mit 3 Annual Reports verifizieren
5. Vollständigen Re-Extraktionslauf ausführen (alle 24 BMW-Dokumente)

**Akzeptanzkriterien (DoD):**
- ✅ BMW Annual Report 2024 (annual_report, 352 Chunks) liefert ≥10 Metriken
- ✅ Kein 413-Fehler für finanzielle Dokumente
- ✅ Gesamtergebnis ≥200 Metriken (vs. aktuell 149)
- ✅ Audit Log Entry für jeden Extraktionslauf

---

#### E1-F2 — Hybrid Search implementieren (BM25 + pgvector + RRF)
**Ref: ADR-008**  
**Aufwand: 2 Tage**  
**Status: TODO**  
**Abhängigkeit: E1-F1 (bessere Daten zum Testen)**

**Hintergrund:**
Reine Vektorsuche versagt bei exakten Firmennamen, Rechtsbegriffen (CSDDD), Abkürzungen (tCO2, LkSG).

**Aufgaben:**
1. Migration: `ALTER TABLE rag_documents ADD COLUMN ts_content tsvector`
2. Migration: `CREATE INDEX idx_rag_ts ON rag_documents USING gin(ts_content)`
3. Migration: `UPDATE rag_documents SET ts_content = to_tsvector('german', content)`
4. `HybridSearchService` implementieren (RRF Fusion SQL-Query als CTE)
5. `document_retriever.py` auf HybridSearch umstellen
6. A/B-Test: Precision@10 vorher vs. nachher mit Testfragen

**SQL-Template (CTE):**
```sql
WITH vector_ranked AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> $query_vec) AS rank
    FROM rag_documents WHERE organization_id = $org_id
),
bm25_ranked AS (
    SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(ts_content, query) DESC) AS rank
    FROM rag_documents, plainto_tsquery('german', $query_text) query
    WHERE ts_content @@ query AND organization_id = $org_id
),
rrf AS (
    SELECT COALESCE(v.id, b.id) AS id,
           COALESCE(1.0/(60+v.rank), 0) + COALESCE(1.0/(60+b.rank), 0) AS score
    FROM vector_ranked v FULL OUTER JOIN bm25_ranked b ON v.id = b.id
)
SELECT r.id, r.score, d.content FROM rrf r JOIN rag_documents d ON d.id = r.id
ORDER BY r.score DESC LIMIT $top_k
```

**Akzeptanzkriterien (DoD):**
- ✅ Suche nach "CSDDD Art. 8" findet regulatorische Chunks (nicht nur semantisch ähnliche)
- ✅ Suche nach "BMW CO2 Scope 1 2023" findet exakten Datenpunkt
- ✅ Keine Regression in bestehenden Copilot-Antworten
- ✅ Performance: <200ms für Top-12 Ergebnisse

---

#### E1-F3 — Parent-Child Chunking für tabellenreiche Dokumente
**Ref: ADR-009**  
**Aufwand: 3 Tage**  
**Status: DEFERRED — Trigger-basiert**  
**Abhängigkeit: E1-F1 Messergebnis**
**Trigger: Haiku-Lauf (E1-F1) liefert < 200 Metriken → sofort einplanen. ≥ 200 Metriken → Phase 2.**

**Hintergrund:**
Finanzielle Tabellen in Annual Reports werden über Chunk-Grenzen aufgeteilt. Wert und Label liegen in verschiedenen Chunks → kein Modell kann sie rekonstruieren.

**Aufgaben:**
1. `rag_documents`: Spalte `parent_chunk_id uuid REFERENCES rag_documents(id)` hinzufügen
2. `ParentChildChunkingStrategy` implementieren:
   - Parent: 1.500–2.000 Token (Sektionsebene)
   - Child: 200–300 Token (Retrieval-Einheit)
3. Ingestion-Pipeline: Strategie nach `doc_type` auswählen
4. `document_retriever.py`: Child-Treffer → Parent-Chunks laden
5. Re-Ingestion der Annual Reports mit neuer Strategie

**Akzeptanzkriterien (DoD):**
- ✅ Extraktion von Annual Report 2024 findet Umsatz + EBITDA + CO2 Scope 1
- ✅ Parent-Child-Relationship korrekt in DB (kein verwaister Child)
- ✅ Retrieval liefert Parent-Kontext bei tabellenreichen Anfragen

---

### EPIC 2 — Deterministic Risk Engine
**Priorität: HOCH — Kernfunktion der Platform**
**Abhängigkeiten: E1-F1 (bessere Extraktionsqualität)**

---

#### E2-F1 — RiskScoreCalculator implementieren
**Ref: ADR-002**  
**Aufwand: 2 Tage**  
**Status: TODO**

**Hintergrund:**
Aktuell werden Risk Scores entweder nicht berechnet oder LLM-delegiert. Beides ist nicht auditierbar.

**Aufgaben:**
1. `domain/value_objects/risk_score.py` erstellen:
   ```python
   @dataclass(frozen=True)
   class RiskScore:
       severity: float          # 0–1
       likelihood: float        # 0–1
       source_reliability: float
       evidence_strength: float
       geographic_exposure: float
       sector_exposure: float
       temporal_trend: float    # -1 bis +1
       data_completeness: float
       composite: float         # berechnet
       formula_version: str     # "RiskScore-v1.0"
       calculated_at: datetime
       factor_breakdown: dict
   ```
2. `application/risk/risk_score_calculator.py` implementieren (reine Funktion, kein LLM)
3. `Risk` Domain Entity um `composite_risk_score: RiskScore` erweitern
4. Trigger: RiskScore neu berechnen wenn Finding hinzugefügt / Signal verändert
5. Unit Tests: 100% Coverage der Formel

**Akzeptanzkriterien (DoD):**
- ✅ Gleiche Inputs → immer gleicher Score (deterministisch)
- ✅ `formula_version` in jedem Score vorhanden
- ✅ `factor_breakdown` in API-Response sichtbar (Explainability)
- ✅ Kein LLM-Aufruf im Scoring-Pfad
- ✅ Unit Tests: alle 8 Faktoren, Edge Cases (0, 1, -1)

---

#### E2-F2 — CSDDD Obligation Rule Engine
**Ref: ADR-010**  
**Aufwand: 3 Tage**  
**Status: TODO**  
**Abhängigkeit: E3-F1 (Findings müssen structurrell korrekt sein)**
**Korrektur (2026-07-09): Ursprüngliche Abhängigkeit E2-F1 war fachlich falsch — Rule Engine berührt keinen RiskScore**

**Hintergrund:**
CSDDD-Artikel müssen deterministisch auf Findings gemappt werden. Aktuell fehlt die `csddd_obligations`-Tabelle.

**Aufgaben:**
1. Migration 106: Tabelle `csddd_obligations` (article_number, obligation_text, trigger_conditions, evidence_requirements)
2. Migration 107: Tabelle `finding_legal_mappings` (finding_id, obligation_id, match_type, confidence, method)
3. Initialdaten: alle 29 CSDDD-Artikel + abgeleitete Obligations einfügen
4. `CsdddRuleEngine` implementieren:
   - Input: Finding-Attribute (category, severity, affectedRights, geographicScope)
   - Matching: strukturierte Regeln (kein LLM)
   - Output: `{obligation_id, match_type, confidence}[]`
5. `FindingService.add_obligation_mappings()` aufrufen nach Finding-Erstellung
6. Integration Tests mit 5 Beispiel-Findings

**Akzeptanzkriterien (DoD):**
- ✅ Finding "Zwangsarbeit in Myanmar" mappt auf CSDDD Art. 8 Abs. 1(a) + Art. 11
- ✅ Finding "Umweltverschmutzung EU-Lieferant" mappt korrekt auf Art. 8 Abs. 1(b)
- ✅ Kein LLM-Aufruf im Mapping-Pfad
- ✅ Alle 29 CSDDD-Artikel sind als Obligations hinterlegt
- ✅ Mapping-Confidence: HIGH/MEDIUM/LOW korrekt differenziert

---

#### E2-F3 — Entity Linker (Signal → Supplier Mapping)
**Aufwand: 2 Tage**  
**Status: TODO**  
**Abhängigkeit: E2-F1**

**Hintergrund:**
News-Signale enthalten Firmennamen in Varianten ("BMW", "Bayerische Motoren Werke AG", "BMW Group"). Diese müssen auf `supplier_id` gemappt werden.

**Aufgaben:**
1. `EntityLinker` Service: Fuzzy-Matching Firmennamen → CompanyProfile
2. Tabelle `entity_aliases` (company_profile_id, alias, confidence)
3. `SignalIngestionService`: nach Klassifikation EntityLinker aufrufen
4. Konfidenz-gestuftes Matching: exact match (1.0), alias match (0.9), fuzzy (0.7)

**Akzeptanzkriterien (DoD):**
- ✅ "BMW Group" → BMW AG Company Profile (confidence 1.0)
- ✅ "Bayerische Motorenwerke" → BMW AG (confidence 0.85)
- ✅ Unbekannte Entitäten → `confidence 0.0`, nicht verknüpft
- ✅ Verknüpfte Signale erscheinen in Supplier Risk Profile

---

### EPIC 3 — Evidence & Audit Trail
**Priorität: MITTEL — für Compliance-Tauglichkeit essenziell**
**Abhängigkeiten: E2-F1 (Risk Score muss auditierbar sein)**

---

#### E3-F1 — Evidence Linking standardisieren
**Ref: ADR-003, ADR-015**  
**Aufwand: 1 Tag**  
**Status: TODO**

**Aufgaben:**
1. Domain-Invariante einbauen: `Finding` ohne `supporting_evidence` → `DomainInvariantError`
2. `FindingService.create()`: Evidence-Ref ist Pflichtparameter
3. API: `POST /findings` gibt 422 ohne `evidence_ids`
4. Migration: bestehende Findings ohne Evidence → Status `Hypothetical` setzen

**Akzeptanzkriterien (DoD):**
- ✅ Kein Finding kann ohne Evidence gespeichert werden (DB + Domain-Ebene)
- ✅ Bestehende Findings ohne Evidence sind als `Hypothetical` markiert
- ✅ API-Fehlermeldung ist verständlich

---

#### E3-F2 — Immutable Audit Log mit Hash-Chain
**Ref: ADR-006**  
**Aufwand: 2 Tage**  
**Status: TODO**

**Aufgaben:**
1. Migration: Spalten `previous_hash varchar(64)`, `entry_hash varchar(64)` zu `audit_events`
2. `AuditEventService.append()`: Hash-Chain-Berechnung (SHA-256)
3. DB-Constraint: kein UPDATE/DELETE auf `audit_events` (Row-Level Security)
4. `AuditEventService.verify_chain()`: Integritätsprüfung
5. Backfill: bestehende Audit Events mit Hashes versehen

**Akzeptanzkriterien (DoD):**
- ✅ Jeder AuditEvent hat `previous_hash` + `entry_hash`
- ✅ `verify_chain()` erkennt manipulierte Einträge
- ✅ `DELETE FROM audit_events` schlägt fehl (DB-Constraint)
- ✅ AuditPackage-Export enthält vollständige Kette

---

#### E3-F3 — Prompt Versioning
**Ref: ADR-011**  
**Aufwand: 1 Tag**  
**Status: TODO**

**Aufgaben:**
1. Migration: Tabelle `prompt_versions` (prompt_name, version, template, variables, active, created_at)
2. Bestehende Prompts migrieren: `_FINANCIAL_SYSTEM`, `_ESG_SYSTEM`, `_STATEMENT_SYSTEM`, `_SIGNAL_SYSTEM`
3. `PromptRegistry.get_active(name)` Service
4. `metric_extractor.py` + `copilot_service.py`: Prompts aus Registry laden

**Akzeptanzkriterien (DoD):**
- ✅ Alle 4 Extraktions-Prompts in DB (nicht im Code)
- ✅ `PromptRegistry.get_active("metric_financial")` liefert aktiven Prompt
- ✅ Jeder LLM-Call loggt `prompt_version` im Audit Trail

---

### EPIC 4 — Domain Model Alignment
**Priorität: MITTEL — technische Schulden in Domain Layer abbauen**
**Abhängigkeiten: E2-F1, E3-F1**

---

#### E4-F1 — ConfidenceCard standardisieren
**Ref: ADR-015**  
**Aufwand: 2 Tage**  
**Status: TODO**

**Aufgaben:**
1. `domain/value_objects/confidence_card.py` (frozen dataclass)
2. `domain/services/confidence_calculator.py` (aus copilot_service.py extrahieren)
3. `Finding.confidence` → `ConfidenceCard` (statt `ConfidenceLevel` enum)
4. `Risk.confidence` → `ConfidenceCard`
5. API: `confidence_card` in Response-Schema

**Akzeptanzkriterien (DoD):**
- ✅ Kein `confidence: float` als alleiniges Feld (immer ConfidenceCard)
- ✅ `missing_information` wird in UI als Warnung angezeigt
- ✅ Rückwärtskompatibilität via `overall_level` Mapping

---

#### E4-F2 — Assessment Immutability Gate
**Ref: ADR-014**  
**Aufwand: 0,5 Tage**  
**Status: TODO**

**Aufgaben:**
1. `AssessmentRepository.update()`: wirft `ImmutableEntityError` wenn `status == Approved`
2. API: `PATCH /assessments/{id}` → 409 wenn Approved
3. Domain Event `AssessmentApproved` triggert Immutability-Flag

**Akzeptanzkriterien (DoD):**
- ✅ Approved Assessment kann nicht geändert werden (API + Domain + DB)
- ✅ Fehlermeldung erklärt warum (neues Assessment erstellen)

---

### EPIC 5 — Explainability & Reporting (Phase 2)
**Priorität: MITTEL — nach Epics 1-4**

#### E5-F1 — Risk Score Explainability
**Aufwand: 1 Tag**

Aufgaben:
1. `ExplainabilityService.explain_risk_score(risk_id)` → Factor Breakdown
2. API: `GET /risks/{id}/explanation`
3. UI: Risk Score mit Faktor-Balken

#### E5-F2 — AuditPackage Generator
**Aufwand: 3 Tage**

Aufgaben:
1. `AuditPackageService.generate(entity_id, period)`
2. Evidence Bundle Assembly (alle EvidenceRefs → Volltexte)
3. Methodik-Dokumentation (Formula Version, Prompt Versions, Model Versions)
4. PDF-Export (optional, Phase 2)

#### E5-F3 — Supply Chain Graph (Tier-2/3)
**Aufwand: 3 Tage**

Aufgaben:
1. Tabelle `supply_chain_edges` (buyer_id, supplier_id, tier, commodity_code, confidence)
2. Graph-Traversal für Tier-2/3-Exposure
3. Risk-Aggregation über Supply Chain Graph

---

## Priorisierter Implementierungsplan — v1.1 (2026-07-09)

> **Änderungsprotokoll v1.0 → v1.1:**
> - E3-F2 (Audit Log) von Woche 3 → Sprint 1 (vor Risk Score, ADR-006)
> - E4-F2 (Assessment Immutability) von Woche 4 → Sprint 1 (Quick Win)
> - E2-F1 (Risk Score) von Woche 1 → Sprint 2 (erst nach Audit Log)
> - E2-F2 (CSDDD Rules): falsche E2-F1-Abhängigkeit entfernt
> - E3-F3 (Prompt Versioning) von Woche 1 → Sprint 3 (nach Haiku-Run)
> - E1-F3 (Parent-Child Chunking): deferred, trigger-basiert nach E1-F1-Messung

```
SPRINT 1 — FOUNDATION (Woche 1)
Ziel: Governance-Infrastruktur vor dem ersten Domain-Feature
Prinzip: Kein Risk Score ohne Audit Trail

  [E4-F2]  Assessment Immutability Gate     0,5T  Keine Deps, Quick Win
  [E3-F1]  Evidence Linking Invariante      1T    Domain-Invariante vor Scoring
  [E3-F2]  Immutable Audit Log (Hash-Chain) 2T    MUSS vor E2-F1 aktiv sein
  [E1-F1]  Haiku Migration + Testlauf       0,5T  Sofortiger ROI, 0 Risiko
                                            ────
                                            4T    (1 Tag Puffer)

SPRINT 2 — CORE INTELLIGENCE (Woche 2)
Ziel: Die zwei sichtbarsten Enterprise-Features
Voraussetzung: Audit Log aktiv (Sprint 1 ✅)

  [E2-F1]  RiskScoreCalculator              2T    Jetzt vollständig auditiert
  [E1-F2]  Hybrid Search (BM25 + RRF)       2T    Unabhängig von E2-F1
                                            ────
                                            4T    (1 Tag Puffer)

SPRINT 3 — COMPLIANCE ENGINE (Woche 3)
Ziel: CSDDD-Kern + Prompt-Audit schließen
Hinweis: E2-F2 benötigt NICHT E2-F1 (korrigiert)

  [E2-F2]  CSDDD Obligation Rule Engine     3T    Dep: E3-F1 (nicht E2-F1!)
  [E3-F3]  Prompt Versioning               1T    Nach Haiku-Run: finale Prompts
                                            ────
                                            4T    (1 Tag Puffer)

SPRINT 4 — QUALITY & CONNECTIVITY (Woche 4)
Ziel: Signal-Linking und Konfidenz-Standardisierung

  [E2-F3]  Entity Linker                    2T
  [E4-F1]  ConfidenceCard Standardisierung  2T
                                            ────
                                            4T    (1 Tag Puffer)

DEFERRED — Trigger-basierte Entscheidung nach Sprint 1
  [E1-F3]  Parent-Child Chunking            3T
  Gate: Haiku-Lauf (E1-F1) → Ergebnis auswerten
    ≥ 200 Metriken → E1-F3 in Phase 2 (kein unmittelbarer Bedarf)
    < 200 Metriken → E1-F3 in Sprint 3 oder 4 einplanen

PHASE 2 (nach Freigabe)
  [E5-F1]  Risk Score Explainability        1T
  [E5-F2]  AuditPackage Generator           3T
  [E5-F3]  Supply Chain Graph               3T
  [E1-F3]  Parent-Child Chunking            3T    (wenn nicht früher eingeplantt)
```

---

## Definition of Done (projektweite Regel)

Eine Aufgabe ist ABGESCHLOSSEN wenn:

| Kriterium | Prüfung |
|-----------|---------|
| Fachlich korrekt | Passt ins Domänenmodell (DOMAIN_MODEL.md) |
| Architektur-konform | Verletzt keine ADR |
| Kein LLM für deterministische Tasks | ADR-001, ADR-002, ADR-010 |
| Tests vorhanden | Unit Tests für Domain Logic, Integration Tests für Services |
| Keine neuen Tech-Schulden | Keine hardcodierten Strings, keine direkten DB-Zugriffe in Routers |
| Dokumentiert | ARCHITECTURE.md Service-Status aktualisiert |
| Auditierbar | Relevante Aktionen in AuditLog |

---

*Dieser Plan wird nach jeder abgeschlossenen Feature-Lieferung aktualisiert.*
