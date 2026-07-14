# ADR.md — Architecture Decision Records
**Status: LIVING DOCUMENT**
**Authority: Lead AI Architect**
**Change Control: New entry per decision; existing entries IMMUTABLE after Accepted**

Format: ID · Titel · Status · Kontext · Entscheidung · Konsequenzen · Datum

---

## ADR-001 — LLM ist niemals Source of Truth

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Das System verwendet LLMs (Groq, Claude, etc.) für Extraktion, Analyse und Antwortgenerierung. LLMs können halluzinieren, sind nicht deterministisch bei gleichem Input und produzieren keine zitierbaren Quellen.

**Entscheidung:**
LLMs sind **Synthesizer** — sie formulieren, strukturieren und erklären. Sie sind niemals Quelle für:
- Risk Scores (→ deterministisch, ADR-002)
- CSDDD-Obligation-Mapping (→ Rule Engine, ADR-010)
- Faktische Daten (→ aus Dokumenten extrahiert und gespeichert)
- Compliance-Status (→ aus DB, nicht aus LLM-Inferenz)
- Audit-relevante Entscheidungen (→ menschlich genehmigt, ADR-005)

**Konsequenzen:**
- Copilot antwortet NUR aus strukturiertem Kontext (RetrievalResult)
- Extrahierte Metriken werden in DB gespeichert, nicht on-the-fly generiert
- Jede LLM-Aussage muss durch Evidenz aus dem Retrieval-Context gedeckt sein
- Systemprompt verbietet explizit die Nutzung von Außen-Wissen (`Rules: Answer ONLY from CONTEXT DATA`)

---

## ADR-002 — Risk Score ist deterministisch

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Risk Scores müssen für Wirtschaftsprüfer, Regulatoren und Gerichte nachvollziehbar sein. LLM-generierte Scores sind nicht reproduzierbar, nicht erklärbar und nicht versionierbar.

**Entscheidung:**
Der RiskScore wird als **versionierte, gewichtete Formel** implementiert:

```
composite = Σ (weight_i × factor_i)

Faktoren:
  severity           weight: 0.30
  likelihood         weight: 0.25
  source_reliability weight: 0.15
  evidence_strength  weight: 0.10
  geographic_exposure weight: 0.10
  sector_exposure    weight: 0.05
  temporal_trend     weight: 0.03
  data_completeness  weight: 0.02

Formel-Version: "RiskScore-v1.0" (Änderungen → neue Version → Migration)
```

Jeder Score enthält: `composite`, `factor_breakdown`, `formula_version`, `calculated_at`.

**Konsequenzen:**
- `RiskScoreCalculator` ist ein eigenständiger Service ohne LLM-Abhängigkeit
- Formel-Änderungen werden als neue Version veröffentlicht (nicht stille Überschreibung)
- Historische Scores bleiben mit ihrer Formel-Version gespeichert
- UI zeigt Formel-Breakdown für Explainability
- LLM darf Risk Level **erklären**, aber nicht berechnen

---

## ADR-003 — Evidence First

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Im regulatorischen Umfeld ist jede Behauptung ohne Quellennachweis wertlos. Wirtschaftsprüfer verlangen: "Belegen Sie das."

**Entscheidung:**
Jedes Finding, jeder Risk, jeder ComplianceGap muss mit mindestens einer `EvidenceRef` verknüpft sein.

Invarianten:
- `Finding.supporting_evidence` ist niemals leer (Minimum: 1 EvidenceRef)
- `ComplianceGap` ohne Evidence hat Status `Hypothetical` (nicht `Confirmed`)
- Copilot-Antworten müssen Citations aus dem Retrieval-Context enthalten

**Konsequenzen:**
- Domain-Validation: `Finding` ohne Evidence wirft `DomainInvariantError`
- Evidence-Linking muss vor Finding-Genehmigung abgeschlossen sein
- AuditPackage enthält vollständiges Evidence-Inventar
- "Evidence Strength" ist expliziter Faktor im RiskScore (ADR-002)

---

## ADR-004 — Bounded Context Isolation

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Das System hat 7 Bounded Contexts (Organisation, Lieferkette, Risiko & Intelligence, Regulierung & Compliance, Assessment & Due Diligence, Maßnahmen & Kontrollen, Berichterstattung & Audit). Ohne klare Grenzen entstehen God-Objects und Coupling-Probleme.

**Entscheidung:**
- Kein Context darf direkt auf das Aggregate eines anderen Contexts zugreifen
- Kommunikation zwischen Contexts erfolgt ausschließlich über:
  - Definierte Service-Schnittstellen (Query/Command)
  - Domain Events (asynchron)
  - Published Language (vohldefinierte DTOs, keine Aggregat-Importe)
- Anti-Corruption Layer (ACL) wo nötig

**Konsequenzen:**
- Service-Klassen dürfen keine fremden Domain-Objekte importieren
- Cross-Context-Abfragen gehen über explizite Ports (Interface-Klassen)
- DB-Joins zwischen Context-Tabellen sind in Query-Services gekapselt, nicht in Repositories
- Verletzung dieser Regel gilt als Architektur-Bug (nicht Feature-Request)

---

## ADR-005 — Human-in-the-Loop für kritische Entscheidungen

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
CSDDD und ERM verlangen menschliche Verantwortlichkeit. KI-Systeme dürfen keine finale Entscheidung über Compliance-Status, Risk-Akzeptanz oder Findings-Genehmigung treffen.

**Entscheidung:**
Folgende Aktionen erfordern explizite menschliche Genehmigung (digitale Unterschrift mit UserId + Timestamp):

| Aktion | Gate |
|--------|------|
| Assessment → Approved | Designated Reviewer |
| Risk → Accepted | Compliance Manager |
| ComplianceGap → Closed | Legal/Compliance Sign-off |
| Finding → Confirmed | Assessment Lead |
| Remedy → Implemented | Sustainability Officer |
| AuditPackage → Released | Authorized Signatory |

**Konsequenzen:**
- Workflow-Engine implementiert diese Gates technisch (kein Bypass möglich)
- Audit Log enthält: `actor_id`, `decision`, `rationale`, `timestamp` (unveränderlich)
- Automatische Statusänderungen durch System sind nur für Nicht-Governance-Status möglich
- CLAUDE.md: "KI-Agenten dürfen niemals menschliche Genehmigungsschritte ersetzen"

---

## ADR-006 — Immutable Audit Log mit Hash-Kette

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Für regulatorische Prüfungen muss jede Entscheidung im System lückenlos und manipulationsresistent nachvollzogen werden können. Standard-Timestamps reichen nicht.

**Entscheidung:**
Jeder `AuditEvent` enthält:
- `event_id`, `event_type`, `actor_id`, `entity_ref`, `payload`, `timestamp`
- `previous_hash`: SHA-256 des vorherigen Events (Hash-Kette)
- `entry_hash`: SHA-256(event_id + event_type + actor_id + payload + previous_hash)

Einmal geschrieben: **kein Update, kein Delete**.

**Konsequenzen:**
- `AuditEvent`-Tabelle hat keine UPDATE/DELETE-Berechtigungen auf Row-Level
- Integritätsprüfung kann jederzeit die vollständige Hash-Kette verifizieren
- AuditPackage-Export enthält die vollständige Kette für den betreffenden Zeitraum
- Retention-Policy: 7 Jahre (gesetzliche Mindestanforderung)

---

## ADR-007 — Groq 8B ist kein Produktions-Extraktions-Modell

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Groq llama-3.1-8b-instant wurde für die Metrik-Extraktion eingesetzt. Empirisch bestätigt:
- 0 Metriken aus Annual Reports mit 250+ Chunks (2022-2025)
- Scheitert bei fragmentierten Tabellen über Chunk-Grenzen
- Free Tier: ~6.000 Token/Request — zu wenig für große Dokumente
- 413-Fehler bei Dokumenten mit 164+ Chunks
- Nicht geeignet für deutschen Finanztext

**Entscheidung:**
Produktions-Extraktion verwendet **Claude Haiku** (claude-haiku-4-5-20251001):
- Kein Token-Limit-Problem
- Multilinguale Stärke (DE/EN)
- Tabellenverständnis über Chunk-Grenzen
- Anthropic-API (zuverlässiger als Free-Tier)

Groq bleibt optional für: Low-priority Background Tasks, Cost-sensitive Scenarios mit einfachem Text.

**Konsequenzen:**
- `run_extract_all.py`: `LLM_PROVIDER=anthropic`, `LLM_MODEL=claude-haiku-4-5-20251001`
- Multi-Model-Routing (ADR-012) formalisiert Modell-Auswahl nach Task-Typ
- Groq-spezifischer Code bleibt, aber nicht default für Extraktion

---

## ADR-008 — Hybrid Search: BM25 + pgvector + RRF

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Reine Vektorsuche versagt bei: exakten Begriffen (Artikelnummern, Firmennamen, Rechtsbegriffen), deutschen Komposita, Abkürzungen (CSDDD, LkSG, tCO2). Reine Keyword-Suche versagt bei semantischen Fragen.

**Entscheidung:**
Hybrid Retrieval mit **Reciprocal Rank Fusion (RRF)**:
```
score_rrf(d) = 1/(k + rank_bm25(d)) + 1/(k + rank_vector(d))   [k=60]
```

Implementierung:
- BM25: PostgreSQL `ts_vector`/`ts_rank` (kein externes System)
- Vector: pgvector cosine similarity (multilingual-e5-large, 1024d)
- RRF-Fusion in einer einzigen SQL-Query (CTE)

**Konsequenzen:**
- `RagDocumentModel` erhält Spalte `ts_content tsvector` (GIN-Index)
- Migration erforderlich: `UPDATE rag_documents SET ts_content = to_tsvector('german', content)`
- `document_retriever.py` implementiert Hybrid-Query
- Retrieval-Qualität messbar über Precision@K vor/nach Migration

---

## ADR-009 — Parent-Child Chunking für tabellenreiche Dokumente

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Annual Reports enthalten Finanztabellen, bei denen Metrik-Label (Spaltenüberschrift) und Wert in verschiedenen Chunks liegen. Das 8B-Modell kann diese nicht rekonstruieren. Auch Haiku benötigt Kontext über Chunk-Grenzen.

**Entscheidung:**
Parent-Child Chunking:
- **Parent Chunk**: großer Kontext-Container (1.500–2.000 Tokens) für Tabellen/Abschnitte
- **Child Chunk**: kleiner Retrieval-Chunk (200–300 Tokens) für präzise Ähnlichkeitssuche
- Suche auf Child-Ebene → Antwort auf Parent-Ebene

Implementierung:
- `RagDocumentModel`: neues Feld `parent_chunk_id: uuid | null`
- Retrieval: nach Child-Chunk-Treffern → Parent-Chunks laden und übergeben
- Nur für `doc_type in ('annual_report', 'financial_statement', 'sustainability_report')`

**Konsequenzen:**
- Migration: bestehende Chunks werden reklassifiziert (parent_chunk_id = null = Standalone)
- Neue Ingestion-Pipeline: Chunking-Strategie nach doc_type ausgewählt
- Erhöhter Speicherbedarf (~2× für dokument-schwere Typen) — akzeptabel

---

## ADR-010 — CSDDD Obligation Rule Engine ist deterministisch

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Das Mapping von Findings auf CSDDD-Artikel (Art. 8, 10, 11 etc.) ist eine Rechtsfrage. LLM-Inferenz erzeugt hier unakzeptable Fehlerraten und ist nicht auditierbar.

**Entscheidung:**
CSDDD-Obligations werden als **strukturierte Regelsammlung** implementiert:
- Tabelle `csddd_obligations`: article_number, obligation_text, trigger_conditions[], evidence_requirements[]
- `CsdddRuleEngine`: deterministischer Matcher (Finding-Attribute × Obligation-Bedingungen)
- Mapping-Konfidenz: `HIGH` wenn exakte Rule-Match, `MEDIUM` wenn Partial-Match
- LLM darf Mapping **erklären**, aber nicht **entscheiden**

**Konsequenzen:**
- Neue Tabelle `csddd_obligations` (Migration 099)
- Neue Tabelle `finding_legal_mappings` (obligation_id, finding_id, match_type, confidence)
- `CsdddRuleEngine` ist stateless, testbar, versionierbar
- Obligation-Daten werden von Legal/Compliance gepflegt, nicht von KI generiert
- Fehlerhafte Mappings können gezielt korrigiert werden

---

## ADR-011 — Prompt Versioning

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Prompts sind aktuell als hardcodierte Strings in Produktionscode (z.B. `metric_extractor.py`). Prompt-Änderungen sind nicht nachvollziehbar, nicht versionierbar und nicht A/B-testbar.

**Entscheidung:**
- Tabelle `prompt_versions`: prompt_name, version, template, variables[], created_at, active
- Prompts werden per Name + Version aus DB geladen
- Deployment eines neuen Prompts = neue DB-Zeile (kein Code-Deploy erforderlich)
- Jeder LLM-Call loggt `prompt_version` im Audit Trail

**Konsequenzen:**
- `_FINANCIAL_SYSTEM`, `_ESG_SYSTEM` etc. werden in DB migriert
- `PromptRegistry` Service liefert aktive Prompt-Version
- A/B-Testing möglich über Feature-Flag auf Prompt-Ebene
- AuditPackage enthält verwendete Prompt-Versionen

---

## ADR-012 — Multi-Model Routing nach Task-Typ

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Verschiedene Tasks haben verschiedene Anforderungen an Modell-Fähigkeit und Kosten:
- Einfache Klassifikation: günstiges Modell ausreichend
- Komplexe Analyse: leistungsfähiges Modell erforderlich
- Batch-Extraktion: Kosten-Optimierung wichtig

**Entscheidung:**
```
Task-Typ                  → Modell
──────────────────────────────────────────────────────────
Metrik-Extraktion (Batch) → claude-haiku-4-5-20251001
Signal-Klassifikation     → claude-haiku-4-5-20251001
Copilot-Antwort           → claude-sonnet-4-6 (default)
Komplexe Analyse          → claude-opus-4-8 (explizit angefordert)
CSDDD Rule Engine         → kein LLM (deterministisch)
Risk Score Calculator     → kein LLM (deterministisch)
```

**Konsequenzen:**
- `ModelRouter` Service: `route(task_type) → ModelConfig`
- Konfiguration über Env-Variable oder DB-Config
- `LLMProvider`-Interface abstrahiert Modell-Wahl
- Kosten-Monitoring per Task-Typ möglich

---

## ADR-013 — Signal → Finding → Risk Pipeline (keine Abkürzungen)

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Direkte Signal-zu-Risk-Mappings verletzen das Evidence-First-Prinzip (ADR-003). Ein Signal ist unverifiziert. Ein Risk ist verifiziert und gesteuert.

**Entscheidung:**
Die Pipeline ist strikt dreistufig:
```
Signal (unverifiziert)
  → Klassifikation + Entity-Linking
  → Finding (verifiziert, mit Evidence)
    → Risk Score Berechnung
    → Risk (gesteuert, mit Lifecycle)
```

Abkürzungen sind verboten:
- Kein `Signal → Risk` (umgeht Verifikation)
- Kein `Finding` ohne mindestens eine `EvidenceRef` (ADR-003)
- Kein `Risk` ohne mindestens ein `Finding`

**Konsequenzen:**
- Domain-Services validieren diese Invarianten
- `SignalToFindingService`: expliziter Schritt mit Entity-Linking
- `FindingToRiskService`: RiskScore-Berechnung mit ConfidenceCard
- UI zeigt Pipeline-Status (Signal → Finding → Risk)

---

## ADR-014 — Assessment ist unveränderlich nach Genehmigung

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Ein genehmigtes Assessment ist ein rechtlicher Akt. Nachträgliche Änderungen würden die Integrität des Audit Trails untergraben.

**Entscheidung:**
Ein Assessment mit `status = Approved` ist **immutable**:
- Keine Änderung an Findings, Risks, Evidence-Refs
- Keine Severity-Änderungen
- Keine nachträgliche Löschung

Wenn neue Erkenntnisse vorliegen: neues Assessment erstellen (Verweis auf Vorgänger).

**Konsequenzen:**
- API-Endpunkte für Approved Assessments liefern 409 bei Mutation-Versuchen
- `AssessmentRepository.update()` prüft Status vor jedem Write
- UI: Approved Assessment ist read-only (kein Edit-Button)
- Audit Log: `AssessmentApproved`-Event ist Marker für Immutability

---

## ADR-015 — ConfidenceCard als Standard-Konfidenz-Objekt

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Aktuell gibt es inkonsistente Konfidenz-Darstellungen: `confidence: float`, `confidence_level: str`, `quality_score: float` — alle bedeuten etwas anderes und sind nicht vergleichbar.

**Entscheidung:**
`ConfidenceCard` ist das einzige Konfidenz-Objekt im System (Value Object):

```python
@dataclass(frozen=True)
class ConfidenceCard:
    overall_level: ConfidenceLevel        # HIGH | MEDIUM | LOW
    source_count: int                     # Anzahl unabhängiger Quellen
    source_independence: float            # 0–1
    source_recency_days: int              # Durchschnittliches Alter
    data_completeness: float              # 0–1
    cross_validation_score: float         # 0–1
    contradiction_penalty: float          # Abzug bei Widersprüchen
    missing_information: list[str]        # explizite Lücken
    calculated_at: datetime
```

**Konsequenzen:**
- `Finding`, `Risk`, `Assessment` ersetzen bisherige Konfidenz-Felder durch `ConfidenceCard`
- `ConfidenceCalculator` Service standardisiert die Berechnung
- Migration: bestehende `confidence`-Felder in `ConfidenceCard`-kompatible Felder umwandeln

---

## ADR-016 — Architecture Compliance Check (ACC) als Pflichtschritt

**Status:** Accepted  
**Datum:** 2026-07-09

**Kontext:**
Ohne formalen Prüfschritt entstehen stille Architekturabweichungen. Jede Implementierung, die "nur kurz etwas löst", riskiert über Zeit kumulative Architekturverletzungen.

**Entscheidung:**
Vor jeder Implementierung — ohne Ausnahme — wird ein Architecture Compliance Check (ACC) durchgeführt und explizit dokumentiert.

### Architecture Compliance Check Template

```
## Architecture Compliance Check — [Feature-Name]
**Datum:** YYYY-MM-DD | **Feature-Ref:** [Epic-ID]

### 1. Bounded Contexts
| Context | Betroffen | Art der Beteiligung |
|---------|-----------|---------------------|
| Organisation | Ja/Nein | Owner / Consumer / Event-Subscriber |
| Lieferkette | ... | ... |
| Risiko & Intelligence | ... | ... |
| Regulierung & Compliance | ... | ... |
| Assessment | ... | ... |
| Maßnahmen & Kontrollen | ... | ... |
| Berichterstattung & Audit | ... | ... |

### 2. ADR-Compliance
| ADR | Relevant | Status | Begründung |
|-----|----------|--------|-----------|
| ADR-001 (LLM ≠ SoT) | Ja/Nein | ✅ Compliant / ❌ Violation | [Kurz] |
| ADR-002 (RiskScore deterministisch) | ... | ... | ... |
| ADR-003 (Evidence First) | ... | ... | ... |
| ADR-004 (Context Isolation) | ... | ... | ... |
| ADR-005 (Human-in-the-Loop) | ... | ... | ... |
| ADR-013 (Signal→Finding→Risk) | ... | ... | ... |
| ADR-014 (Assessment Immutability) | ... | ... | ... |

### 3. Architektur-Verletzungen
[ ] Keine festgestellt
[ ] Verletzung: [Beschreibung] → STOP, ADR-XXX erforderlich

### 4. Technische Schulden
[ ] Keine eingeführt
[ ] Schuld eingeführt: [Beschreibung + Tilgungsplan]

### 5. Domain Model Impact
[ ] Keine Änderung erforderlich
[ ] Neues Aggregate: [Name + Begründung]
[ ] Neue Domain Events: [Event + Trigger]
[ ] Neue Value Objects: [Name + Felder]

### 6. Entscheidung
[ ] ✅ PROCEED — alle Checks bestanden
[ ] ⛔ STOP — [Verletzung] → ADR-[XXX] wird erstellt
```

**Konsequenzen:**
- Kein Code wird geschrieben bevor ACC abgeschlossen ist
- ACC-Ergebnis wird im Code-Review sichtbar (in PR-Beschreibung oder Commit-Message)
- Bei ⛔ STOP: Implementierung pausiert, ADR-Vorschlag erstellt, Freigabe abgewartet
- Schnelle Tasks (≤30 Min, rein technisch, kein Domänen-Impact) benötigen vereinfachten ACC (nur ADR-Tabelle)

---

## Offene Entscheidungen (noch kein ADR)

| Thema | Status | Nächster Schritt |
|-------|--------|-----------------|
| GraphDB für Supply Chain (Tier-2/3) | Under Discussion | Evaluate nach Phase 2 |
| Event Sourcing für Risk Lifecycle | Under Discussion | Evaluate nach Phase 1 |
| Multi-Tenant Architektur | Under Discussion | Requirement klären |
| Real-time Monitoring (WebSocket) | Under Discussion | Nach Phase 2 |

---

*Einmal als "Accepted" markierte ADRs dürfen nicht geändert werden. Neue Entscheidung → neue ADR (mit Verweis auf superseded ADR).*
