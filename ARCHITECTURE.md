# ARCHITECTURE.md — Technische Zielarchitektur
**Status: APPROVED — Version 1.0 (2026-07-09)**
**Authority: Lead AI Architect**
**Basis: Clean Architecture + Domain-Driven Design**

---

## Grundprinzip

```
Abhängigkeits-Regel (Dependency Rule):
  Code-Abhängigkeiten zeigen IMMER nach innen.
  Domain kennt niemanden. Application kennt nur Domain.
  Infrastructure kennt Application + Domain.
  API kennt nur Application.
```

```
┌──────────────────────────────────────────────────┐
│              EXTERNAL WORLD                       │
│   Browser | Mobile | API Client | Scheduler       │
└──────────────────────┬───────────────────────────┘
                       │ HTTP / gRPC / Events
┌──────────────────────▼───────────────────────────┐
│  LAYER 1: API / Interface Layer                  │
│  FastAPI Routers, Request/Response DTOs,         │
│  Auth Middleware, Rate Limiting                  │
└──────────────────────┬───────────────────────────┘
                       │ Commands + Queries
┌──────────────────────▼───────────────────────────┐
│  LAYER 2: Application Layer                      │
│  Use Cases, Service Orchestration,               │
│  Event Publishing, Transaction Boundaries        │
└──────────────────────┬───────────────────────────┘
                       │ Domain Objects
┌──────────────────────▼───────────────────────────┐
│  LAYER 3: Domain Layer          [KERN]           │
│  Aggregates, Entities, Value Objects,            │
│  Domain Events, Domain Services,                 │
│  Repository Interfaces, Port Interfaces          │
└──────────────────────────────────────────────────┘
         ↑ (nur nach innen zeigen)
┌─────────────────────────────────────────────────┐
│  LAYER 4: Infrastructure Layer                  │
│  PostgreSQL Repositories, LLM Adapters,         │
│  Embedding Service, Event Bus, External APIs,   │
│  File Storage, Cache                            │
└─────────────────────────────────────────────────┘
```

---

## 8-Layer Technical Architecture

### Layer 1 — Data Ingestion & Enrichment

**Verantwortung:** Rohdaten in strukturierte, indexierbare Form bringen.

```
Komponenten:
  DocumentIngestionService
    ├── PDF/HTML-Parsing (PyMuPDF, Unstructured)
    ├── OCR-Pipeline (für gescannte Dokumente)
    ├── LanguageDetection
    └── ChunkingStrategy (Strategie nach DocType)
        ├── StandardChunking (600 Token, 100 Token Overlap)
        └── ParentChildChunking (für Annual Reports, ADR-009)

  EmbeddingService
    ├── Model: multilingual-e5-large (1024d)
    ├── Batch-Processing (max 512 Dokumente/Batch)
    └── pgvector Storage

  BM25IndexService (ADR-008)
    └── PostgreSQL ts_vector GIN Index

  MetricExtractorService (ADR-007)
    ├── Claude Haiku für Extraktion
    ├── KeywordScoring (_select_chunks)
    ├── QuantitativeFact Extraktion
    └── SignalExtraktion

Output: Dokumente indexiert → Metriken + Signale in DB → Embeddings in pgvector
```

### Layer 2 — Knowledge & Evidence Store

**Verantwortung:** Strukturiertes Wissen speichern und abrufbar machen.

```
Komponenten:
  DocumentRepository (Domain Port)
    └── PostgreSQL Implementation

  KnowledgeFactRepository
    ├── CompanyMetricModel (quantitative Fakten)
    └── CompanySignalModel (qualitative Signale)

  EvidenceRepository
    └── Evidence mit SourceDocument-Link

  HybridSearchService (ADR-008)
    ├── VectorSearch: pgvector cosine similarity
    ├── BM25Search: PostgreSQL ts_rank
    └── RRFusion: 1/(k+rank_bm25) + 1/(k+rank_vector), k=60

  CrossEncoderReranker
    └── Post-retrieval Quality Improvement (Phase 2)
```

### Layer 3 — Intelligence Engine

**Verantwortung:** Aus Wissen Risikointelligenz ableiten. DETERMINISTISCH.

```
Komponenten:
  RiskScoreCalculator (ADR-002)
    ├── Keine LLM-Abhängigkeit
    ├── Versionierte Gewichtungsformel
    └── FactorBreakdown für Explainability

  SignalClassifier
    ├── Rule-based Klassifikation (Tier 1: deterministisch)
    └── ML-Klassifikation (Tier 2: confidence-gestützt)

  EntityLinker
    ├── NER → canonical CompanyProfile
    └── Fuzzy-Matching für Firmennamen-Varianten

  SignalToFindingService
    ├── Verifikation + Entity-Linking
    └── Evidence-Attachment

  FindingToRiskService
    ├── RiskScore-Berechnung
    └── ConfidenceCard-Erstellung

  CsdddRuleEngine (ADR-010)
    ├── Deterministisches Obligation-Matching
    ├── Kein LLM für Rechtsfragen
    └── Finding × Obligation → ComplianceGap
```

### Layer 4 — RAG & Copilot

**Verantwortung:** KI-gestützte Analyse für Compliance-Fragen.

```
Komponenten:
  CopilotService (Orchestrator)
    ├── IntentDetector
    ├── HybridRetriever (Document + Structured)
    ├── ContextAssembler (Budget-aware, 28k chars)
    ├── ContradictionDetector (Pre-LLM)
    ├── FreshnessAnalyzer
    └── ConfidenceCalculator

  RetrievalRouter
    ├── DocumentRetriever (HybridSearch)
    ├── MetricsRetriever (SQL)
    ├── SupplierRetriever
    ├── ComplianceRetriever
    └── DueDiligenceRetriever

  LLMProvider (ADR-012)
    ├── ModelRouter (Task → Model Mapping)
    ├── PromptRegistry (ADR-011)
    └── ResponseParser

  CitationExtractor
    └── Validierung gegen CitationMap
```

### Layer 5 — Assessment & Workflow Engine

**Verantwortung:** Strukturierte Due-Diligence-Prozesse orchestrieren.

```
Komponenten:
  AssessmentService
    ├── Lifecycle Management
    ├── Human Review Gate (ADR-005)
    └── Approval Workflow

  FindingService
    ├── Evidence Linking
    ├── Severity Classification
    └── Obligation Mapping (via CsdddRuleEngine)

  RecommendationService
    └── Finding → Recommendation Generation

  WorkflowEngine
    ├── State Machine für Assessment Lifecycle
    └── Notification Triggers
```

### Layer 6 — Risk Engine & Control Tracking

**Verantwortung:** Risks steuern, Controls verwalten, Mitigationen tracken.

```
Komponenten:
  RiskManagementService
    ├── Risk Lifecycle Management
    ├── Score Recalculation (bei neuen Signals/Findings)
    └── Escalation Rules

  ControlService
    ├── Control Effectiveness Tracking
    └── Test Scheduling

  MitigationService
    ├── Plan Management
    ├── Measure Tracking
    └── Completion Verification

  RemedyService (CSDDD Art. 11)
    ├── Affected Party Management
    └── Stakeholder Engagement Tracking
```

### Layer 7 — Reporting & Audit

**Verantwortung:** Nachvollziehbare Outputs für alle Stakeholder.

```
Komponenten:
  ReportGenerator
    ├── DueDiligenceReport
    ├── ExecutiveSummary
    ├── RegulatoryDisclosure
    └── SupplierCard

  AuditPackageService (ADR-006)
    ├── Evidence Bundle Assembly
    ├── Decision Log Collection
    ├── Methodology Documentation
    └── Hash-Chain Generation (SHA-256)

  ExplainabilityService
    ├── RiskScore Factor Breakdown
    ├── CSDDD Rule Trace
    └── Evidence Chain Visualization
```

### Layer 8 — Observability & Governance

**Verantwortung:** Das System beobachten und kontrollieren.

```
Komponenten:
  AuditEventLog (ADR-006)
    ├── Immutable Event Append
    ├── Hash-Chain Verification
    └── Retention Management (7 Jahre)

  ModelMonitor
    ├── Extraction Quality Metrics
    ├── Retrieval Precision@K
    └── LLM Cost Tracking

  PromptVersionRegistry (ADR-011)
    ├── Active Prompt Management
    └── Version History

  SystemHealthDashboard
    ├── Pipeline Status
    └── Processing Queue
```

---

## Service-Verzeichnis

| Service | Context | Layer | LLM? | Status |
|---------|---------|-------|------|--------|
| DocumentIngestionService | Wissen & Evidenz | 1 | Nein | ✅ Vorhanden |
| MetricExtractorService | Wissen & Evidenz | 1 | ✅ Haiku | ⚠️ Groq→Haiku Migration |
| EmbeddingService | Wissen & Evidenz | 1 | Nein (Embedding) | ✅ Vorhanden |
| HybridSearchService | Wissen & Evidenz | 2 | Nein | ❌ Fehlt |
| RiskScoreCalculator | Risiko | 3 | Nein | ❌ Fehlt (deterministisch) |
| CsdddRuleEngine | Regulierung | 3 | Nein | ❌ Fehlt |
| EntityLinker | Risiko | 3 | Optional | ❌ Fehlt |
| CopilotService | RAG | 4 | ✅ Sonnet | ✅ Vorhanden |
| AssessmentService | Assessment | 5 | Nein | ✅ Vorhanden |
| FindingService | Assessment | 5 | Nein | ✅ Vorhanden |
| ControlService | Maßnahmen | 6 | Nein | ✅ Vorhanden |
| MitigationService | Maßnahmen | 6 | Nein | ✅ Vorhanden |
| RemedyService | Maßnahmen | 6 | Nein | ⚠️ Partial |
| AuditPackageService | Berichterstattung | 7 | Nein | ❌ Fehlt |
| ExplainabilityService | Berichterstattung | 7 | Optional | ❌ Fehlt |
| AuditEventLog | Governance | 8 | Nein | ⚠️ Basic (kein Hash-Chain) |
| PromptVersionRegistry | Governance | 8 | Nein | ❌ Fehlt |

---

## Datenbankschema-Strategie

```
Schema-Aufteilung nach Bounded Context:

public.organizations              → Organisation Context
public.suppliers                  → Lieferkette Context
public.supply_chain_edges         → Lieferkette Context [FEHLT]
public.rag_documents              → Wissen & Evidenz
public.document_files             → Wissen & Evidenz
public.company_metrics            → Wissen & Evidenz
public.company_signals            → Wissen & Evidenz
public.assessments                → Assessment Context
public.findings                   → Assessment + Risiko Context
public.risks                      → Risiko Context
public.evidence                   → Wissen & Evidenz
public.controls                   → Maßnahmen Context
public.mitigation_plans           → Maßnahmen Context
public.csddd_obligations          → Regulierung Context [FEHLT]
public.finding_legal_mappings     → Regulierung Context [FEHLT]
public.compliance_gaps            → Regulierung Context
public.audit_events               → Governance (immutable)
public.prompt_versions            → Governance [FEHLT]
```

---

## LLM-Interaktions-Prinzipien

```
1. LLM ist Synthesizer, nicht Entscheider (ADR-001)
   Input: strukturierter Kontext aus DB/Retrieval
   Output: natürlichsprachliche Antwort

2. Kein Cascade-Chaining
   Eine User-Anfrage = ein LLM-Call (außer explizit orchestriert)

3. Prompt Versioning (ADR-011)
   Kein hardcodierter Prompt in Production

4. Model Routing (ADR-012)
   Haiku → Extraktion/Klassifikation
   Sonnet → Copilot/Analyse
   Opus  → Komplexe Analyse (explizit angefordert)
   kein LLM → Risk Score, CSDDD Rules, Compliance Status

5. Token Budget
   Copilot: max 28k chars Kontext, 1024 max_tokens Output
   Extraktion: max 11k chars Kontext, 2000 max_tokens Output
```

---

## Technologie-Stack

| Bereich | Technologie | Begründung |
|---------|------------|-----------|
| Backend | FastAPI / Python | Vorhanden, async-first |
| ORM | SQLAlchemy async | Vorhanden |
| DB | PostgreSQL + pgvector | Vorhanden |
| Embeddings | multilingual-e5-large (1024d) | Vorhanden, multilingual |
| LLM (Prod) | Anthropic Claude (Haiku/Sonnet/Opus) | ADR-007, ADR-012 |
| LLM (Dev) | Groq (8B) | Nur für schnelle Entwicklungsiterationen |
| Search | pgvector + PostgreSQL FTS | ADR-008 (Hybrid) |
| Observability | structlog | Vorhanden |
| Task Queue | Geplant: Celery/ARQ | Nach Phase 2 |
| Caching | Geplant: Redis | Nach Phase 2 |

---

*Dieses Dokument beschreibt die Zielarchitektur. Ist-Zustand in IMPLEMENTATION_PLAN.md.*
