# Feature Knowledge Graph — EIOS

> Jedes Feature ist vollständig zu allen Artefakten verknüpft.
> Stand: 2026-06-29 · Automatisch aus Codebase-Analyse generiert.

---

## Vorlage

```yaml
feature:
  name: "[Feature-Name]"
  status: "active | deprecated | in-development | planned"
  horizon: "H1 | H2 | H3 | H4 | H5 | TECH"
  last_updated: "YYYY-MM-DD"

backend:
  services:
    - file: "backend/application/[domain]/[name]_service.py"
      class: "[ClassName]"
      methods: []
  api_endpoints:
    - method: "GET"
      path: "/api/v1/[resource]"
      auth: "Bearer JWT"
      roles: []
  models:
    - table: "[table_name]"
      file: "backend/infrastructure/persistence/models/[name].py"
  migrations:
    - file: "backend/alembic/versions/[NNN]_[description].py"

frontend:
  pages:
    - file: "frontend/src/app/(app)/[route]/page.tsx"
      route: "/[route]"
  api_client: "frontend/src/lib/api/[name].ts"

tests:
  unit: []
  integration: []

documentation:
  confluence:
    page_id: "TBD"
    status: "draft | current | outdated"

jira:
  epic: "KAN-[N]"
  stories: []

permissions:
  roles: []
  special_restrictions: []

external_dependencies: []
```

---

## Ausgefüllte Features

---

### 01 · Supplier Management

```yaml
feature:
  name: "Supplier Management"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/scoring/supplier_scorer.py"
      class: "SupplierScorer"
      methods:
        - "score_supplier(supplier_id)"
        - "recalculate_all()"
    - file: "backend/application/external_intelligence/enrichment_service.py"
      class: "EnrichmentService"
      methods:
        - "enrich_supplier(supplier_id)"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/suppliers"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "SupplierCreate"
      schema_out: "SupplierResponse"
    - method: "GET"
      path: "/api/v1/suppliers"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
      schema_out: "Page[SupplierResponse]"
    - method: "GET"
      path: "/api/v1/suppliers/{supplier_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
      schema_out: "SupplierResponse"
    - method: "PATCH"
      path: "/api/v1/suppliers/{supplier_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "SupplierUpdate"
      schema_out: "SupplierResponse"
    - method: "DELETE"
      path: "/api/v1/suppliers/{supplier_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/suppliers/{supplier_id}/assessments"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
    - method: "GET"
      path: "/api/v1/suppliers/{supplier_id}/risk-profile"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
      schema_out: "SupplierRiskProfile"
  models:
    - table: "suppliers"
      file: "backend/infrastructure/persistence/models/supplier.py"
      key_fields: ["id", "organization_id", "name", "country", "industry", "created_at"]
    - table: "supplier_scores"
      file: "backend/infrastructure/persistence/models/supplier_score.py"
      key_fields: ["id", "supplier_id", "overall_score", "dimension_scores", "scored_at"]
  migrations:
    - file: "backend/alembic/versions/018_add_supplier_management.py"
      description: "Suppliers Tabelle + Basisfelder"
    - file: "backend/alembic/versions/019_supplier_name_uniqueness.py"
      description: "Unique-Constraint auf (organization_id, name)"
    - file: "backend/alembic/versions/020_add_supplier_scores.py"
      description: "Supplier-Score-Tabelle für 8-dimensionalen Health Score"

frontend:
  pages:
    - file: "frontend/src/app/(app)/suppliers/page.tsx"
      route: "/suppliers"
    - file: "frontend/src/app/(app)/suppliers/[id]/page.tsx"
      route: "/suppliers/:id"
  api_client: "frontend/src/lib/api/suppliers.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_suppliers.py"
      endpoints_tested: ["POST /suppliers", "GET /suppliers", "PATCH /suppliers/{id}", "DELETE /suppliers/{id}"]
    - file: "backend/tests/integration/api/test_supplier_hardening.py"
      endpoints_tested: ["Multi-Tenancy Isolation", "RBAC Guards"]

documentation:
  confluence:
    page_id: "2588673"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2588673"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-2"
      title: "Lieferantenerfassung & Stammdaten"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create", "read", "update", "delete"]
    - name: "compliance_manager"
      can: ["create", "read", "update"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Jede Query MUSS WHERE organization_id = current_org.id enthalten"
    - "Supplier darf nicht gelöscht werden wenn offene Findings existieren"

configuration:
  env_vars:
    - name: "SUPPLIER_MATCHER_THRESHOLD"
      required: false
      default: "0.45"
      description: "Jaccard-Schwellenwert für Duplikaterkennung"
    - name: "SUPPLIER_COUNTRY_BOOST"
      required: false
      default: "0.10"
      description: "Score-Boost bei Länder-Übereinstimmung"
```

---

### 02 · Supplier Digital Twin & Health Engine

```yaml
feature:
  name: "Supplier Digital Twin & Health Engine"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/scoring/supplier_scorer.py"
      class: "SupplierScorer"
      methods:
        - "calculate_overall_score(signals)"
        - "calculate_dimension(dimension, signals)"
        - "map_delta(severity, signal_type)"
    - file: "backend/application/external_intelligence/health_service.py"
      class: "HealthService"
      methods:
        - "get_health_summary(supplier_id)"
        - "get_dimension_breakdown(supplier_id)"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/supplier-twin/{supplier_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
      schema_out: "SupplierTwinResponse"
    - method: "GET"
      path: "/api/v1/supplier-twin/{supplier_id}/scores"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
    - method: "POST"
      path: "/api/v1/supplier-twin/{supplier_id}/recalculate"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "POST"
      path: "/api/v1/supplier-twin/{supplier_id}/snapshot"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/supplier-twin/{supplier_id}/timeline"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
  models:
    - table: "supplier_digital_twin"
      file: "backend/infrastructure/persistence/models/supplier_digital_twin.py"
      key_fields: ["id", "supplier_id", "overall_score", "compliance_score", "esg_score",
                   "financial_score", "human_rights_score", "geopolitical_score",
                   "cyber_score", "environmental_score", "operational_score", "calculated_at"]
    - table: "supplier_scores"
      file: "backend/infrastructure/persistence/models/supplier_score.py"
  migrations:
    - file: "backend/alembic/versions/064_supplier_digital_twin.py"
      description: "supplier_digital_twin Tabelle mit allen 8 Dimensionen"

frontend:
  pages:
    - file: "frontend/src/app/(app)/suppliers/[id]/page.tsx"
      route: "/suppliers/:id (Health Score Card integriert)"
  api_client: "frontend/src/lib/api/supplier-twin.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_health_api.py"
      endpoints_tested: ["GET /supplier-twin/{id}", "POST /supplier-twin/{id}/recalculate"]

documentation:
  confluence:
    page_id: "2621441"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2621441"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-3"
      title: "8-dimensionaler Health Score"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["read", "trigger_recalculate", "create_snapshot"]
    - name: "compliance_manager"
      can: ["read", "trigger_recalculate"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Scoring ist deterministisch — kein LLM-basiertes Scoring (VERBOTEN)"
    - "Gewichte: compliance×0.20 + esg×0.15 + financial×0.15 + human_rights×0.15 + geopolitical×0.10 + cyber×0.10 + environmental×0.10 + operational×0.05"
    - "Alle Berechnungen müssen auditierbar und erklärbar sein"
```

---

### 03 · External Intelligence & Sanctions Screening

```yaml
feature:
  name: "External Intelligence & Sanctions Screening"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/external_intelligence/signal_service.py"
      class: "SignalService"
      methods:
        - "ingest_signal(supplier_id, source, signal_data)"
        - "process_sanctions_match(supplier_id, list_name, score)"
        - "get_signals(supplier_id)"
    - file: "backend/application/external_intelligence/country_risk_service.py"
      class: "CountryRiskService"
      methods:
        - "get_risk(country_code)"
        - "refresh_world_bank_data()"
    - file: "backend/application/external_intelligence/dataset_service.py"
      class: "DatasetService"
      methods:
        - "download_eu_sanctions_list()"
        - "download_ofac_list()"
        - "download_un_list()"
    - file: "backend/application/external_intelligence/benchmark_engine.py"
      class: "BenchmarkEngine"
    - file: "backend/application/external_intelligence/scheduler.py"
      class: "IntelligenceScheduler"
      methods:
        - "schedule_refresh()"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/external-intelligence/suppliers/{id}/signals"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/external-intelligence/suppliers/{id}/sanctions"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/external-intelligence/suppliers/{id}/country-risk"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
    - method: "GET"
      path: "/api/v1/external-intelligence/suppliers/{id}/news"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "POST"
      path: "/api/v1/external-intelligence/refresh"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/external-intelligence/screen/{supplier_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
  models:
    - table: "external_intelligence"
      file: "backend/infrastructure/persistence/models/external_intelligence.py"
      key_fields: ["id", "supplier_id", "source", "event_type", "severity", "raw_data", "ingested_at"]
  migrations:
    - file: "backend/alembic/versions/025_add_regulatory_intelligence.py"
      description: "External Intelligence Events + Sanktions-Matching"
    - file: "backend/alembic/versions/033_m34_external_intelligence.py"
      description: "M34 Intelligence-Engine Erweiterung"
    - file: "backend/alembic/versions/034_m34_1_connectors.py"
      description: "Connector-Framework für externe Datenquellen"
    - file: "backend/alembic/versions/035_m34_2_hardening.py"
      description: "Rate-Limiting, Fehlerbehandlung, GDELT-Integration"

frontend:
  pages:
    - file: "frontend/src/app/(app)/suppliers/[id]/page.tsx"
      route: "/suppliers/:id (Intelligence Panel)"
  api_client: "frontend/src/lib/api/suppliers.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_supplier_intelligence.py"
      endpoints_tested: ["GET /external-intelligence/suppliers/{id}/signals",
                         "POST /external-intelligence/screen/{id}"]

documentation:
  confluence:
    page_id: "2654209"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2654209"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-5"
      title: "Sanctions Screening Engine"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["read", "trigger_refresh", "trigger_screen"]
    - name: "compliance_manager"
      can: ["read", "trigger_screen"]
    - name: "viewer"
      can: ["read_country_risk"]
  special_restrictions:
    - "Agenten dürfen Sanktionstreffer NICHT eigenständig schließen — nur empfehlen"
    - "GDELT: asyncio.Semaphore(1) + 1.5s sleep, graceful 429 handling"

external_dependencies:
  - name: "EU Financial Sanctions List"
    type: "API"
    url: "https://webgate.ec.europa.eu/fsd/fsf"
    fallback: "Letzter bekannter Stand; Alert an Ops-Team"
  - name: "OFAC SDN List"
    type: "API"
    url: "https://www.treasury.gov/ofac/downloads/sdn.xml"
    fallback: "Letzter bekannter Stand; Alert an Ops-Team"
  - name: "UN Consolidated List"
    type: "API"
    url: "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
    fallback: "Letzter bekannter Stand; Alert an Ops-Team"
  - name: "World Bank WGI"
    type: "API"
    url: "https://api.worldbank.org/v2/country"
    fallback: "Gecachte Länderrisiko-Tabelle; risk = 100 - GOV_WGI_CC.SC"
  - name: "GDELT News"
    type: "API"
    url: "https://api.gdeltproject.org/api/v2/doc/doc"
    fallback: "Leer-Ergebnis mit Warning-Log"
```

---

### 04 · Assessments & Findings

```yaml
feature:
  name: "Assessments & Findings"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/due_diligence/"
      class: "AssessmentService"
      methods:
        - "create_assessment(supplier_id, type, data)"
        - "approve_assessment(assessment_id, user_id)"
        - "get_assessment(assessment_id)"
        - "list_assessments(supplier_id)"
        - "create_finding(assessment_id, data)"
        - "close_finding(finding_id, resolution)"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/assessments"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "AssessmentCreate"
      schema_out: "AssessmentResponse"
    - method: "GET"
      path: "/api/v1/assessments"
      auth: "Bearer JWT"
      schema_out: "Page[AssessmentResponse]"
    - method: "GET"
      path: "/api/v1/assessments/{assessment_id}"
      auth: "Bearer JWT"
      schema_out: "AssessmentResponse"
    - method: "GET"
      path: "/api/v1/assessments/{assessment_id}/findings"
      auth: "Bearer JWT"
      schema_out: "list[FindingResponse]"
    - method: "GET"
      path: "/api/v1/assessments/{assessment_id}/risks"
      auth: "Bearer JWT"
      schema_out: "list[RiskResponse]"
    - method: "PATCH"
      path: "/api/v1/assessments/{assessment_id}/approve"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "PATCH"
      path: "/api/v1/assessments/{assessment_id}/status"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/assessments/{assessment_id}/trace"
      auth: "Bearer JWT"
      schema_out: "AssessmentTraceResponse"
    - method: "GET"
      path: "/api/v1/assessments/{assessment_id}/remediation"
      auth: "Bearer JWT"
      schema_out: "RemediationPlanResponse"
    - method: "GET"
      path: "/api/v1/assessments/{assessment_id}/brief"
      auth: "Bearer JWT"
      schema_out: "DecisionBriefResponse"
    - method: "POST"
      path: "/api/v1/findings"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/findings"
      auth: "Bearer JWT"
    - method: "PATCH"
      path: "/api/v1/findings/{finding_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "DELETE"
      path: "/api/v1/findings/{finding_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "assessments"
      file: "backend/infrastructure/persistence/models/assessment.py"
      key_fields: ["id", "organization_id", "supplier_id", "type", "status", "created_by", "approved_by"]
    - table: "findings"
      file: "backend/infrastructure/persistence/models/finding.py"
      key_fields: ["id", "assessment_id", "severity", "category", "description", "status"]
    - table: "finding_evidence_links"
      file: "backend/infrastructure/persistence/models/finding_evidence_link.py"
  migrations:
    - file: "backend/alembic/versions/007_extend_assessment_quality.py"
      description: "Assessment-Qualitäts-Felder"
    - file: "backend/alembic/versions/029_m32_1_due_diligence.py"
      description: "Due-Diligence Assessment-Framework M32.1"

frontend:
  pages:
    - file: "frontend/src/app/(app)/assessments/page.tsx"
      route: "/assessments"
  api_client: "frontend/src/lib/api/assessments.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_assessments_api.py"
      endpoints_tested: ["POST /assessments", "GET /assessments/{id}/findings",
                         "PATCH /assessments/{id}/approve"]
  unit:
    - file: "backend/tests/unit/application/test_m31_gap_engine.py"
    - file: "backend/tests/unit/application/test_m31_mapping_engine.py"

documentation:
  confluence:
    page_id: "2686977"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2686977"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-6"
      title: "Assessment-Lifecycle Management"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create", "read", "approve", "close", "delete"]
    - name: "compliance_manager"
      can: ["create", "read", "approve"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Agenten dürfen Assessments NICHT genehmigen — nur Empfehlungen erstellen"
    - "Agenten dürfen Findings NICHT schließen — nur eskalieren und notifizieren"
```

---

### 05 · Risk Management

```yaml
feature:
  name: "Risk Management"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/surveillance/risk_drift_engine.py"
      class: "RiskDriftEngine"
    - file: "backend/application/surveillance/emerging_risk_engine.py"
      class: "EmergingRiskEngine"
    - file: "backend/application/surveillance/early_warning_engine.py"
      class: "EarlyWarningEngine"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/risks"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "RiskCreate"
      schema_out: "RiskResponse"
    - method: "GET"
      path: "/api/v1/risks"
      auth: "Bearer JWT"
      schema_out: "list[RiskResponse]"
    - method: "GET"
      path: "/api/v1/risks/{risk_id}"
      auth: "Bearer JWT"
      schema_out: "RiskResponse"
    - method: "PATCH"
      path: "/api/v1/risks/{risk_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/risks/{risk_id}/mitigations"
      auth: "Bearer JWT"
    - method: "DELETE"
      path: "/api/v1/risks/{risk_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "risks"
      file: "backend/infrastructure/persistence/models/risk.py"
      key_fields: ["id", "organization_id", "supplier_id", "category", "severity",
                   "likelihood", "impact", "status", "owner_id"]
    - table: "surveillance"
      file: "backend/infrastructure/persistence/models/surveillance.py"
  migrations:
    - file: "backend/alembic/versions/057_m46_3_scheduling_alerts.py"
      description: "Risk-Alert-Scheduling und automatische Eskalation"

frontend:
  pages:
    - file: "frontend/src/app/(app)/risks/page.tsx"
      route: "/risks"
  api_client: "frontend/src/lib/api/risks.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_risks_api.py"
      endpoints_tested: ["POST /risks", "GET /risks", "PATCH /risks/{id}"]

documentation:
  confluence:
    page_id: "2719745"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2719745"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-7"
      title: "Risk Register & Mitigations"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create", "read", "update", "close", "delete"]
    - name: "compliance_manager"
      can: ["create", "read", "update"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Agenten dürfen Risiken NICHT schließen — nur eskalieren"
    - "Strategische Risiken: Human-Approval durchgesetzt auf Service-Layer"
```

---

### 06 · Evidence Management

```yaml
feature:
  name: "Evidence Management"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/ingestion/pipeline.py"
      class: "IngestionPipeline"
      methods:
        - "ingest_document(file, metadata)"
        - "extract_content(file)"
        - "chunk_and_embed(content)"
    - file: "backend/application/ingestion/parsers.py"
      class: "DocumentParsers"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/evidence"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "EvidenceCreate (multipart)"
      schema_out: "EvidenceResponse"
    - method: "GET"
      path: "/api/v1/evidence"
      auth: "Bearer JWT"
      schema_out: "Page[EvidenceResponse]"
    - method: "POST"
      path: "/api/v1/evidence/{evidence_id}/approve"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/evidence/{evidence_id}"
      auth: "Bearer JWT"
      schema_out: "EvidenceResponse"
    - method: "GET"
      path: "/api/v1/evidence/{evidence_id}/versions"
      auth: "Bearer JWT"
      schema_out: "list[dict]"
    - method: "DELETE"
      path: "/api/v1/evidence/{evidence_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "evidence"
      file: "backend/infrastructure/persistence/models/evidence.py"
      key_fields: ["id", "organization_id", "supplier_id", "file_key", "file_type",
                   "status", "approved_by", "approved_at"]
    - table: "evidence_chunks"
      file: "backend/infrastructure/persistence/models/evidence_chunk.py"
      key_fields: ["id", "evidence_id", "embedding", "content", "chunk_index"]
    - table: "evidence_versions"
      file: "backend/infrastructure/persistence/models/evidence_version.py"
  migrations:
    - file: "backend/alembic/versions/003_add_pgvector.py"
      description: "pgvector Extension + embedding Spalte"
    - file: "backend/alembic/versions/011_add_document_ingestion.py"
      description: "Evidence + Chunks Tabellen"
    - file: "backend/alembic/versions/016_add_evidence_intelligence.py"
      description: "Evidence-Intelligence Verknüpfung"

frontend:
  pages:
    - file: "frontend/src/app/(app)/evidence/page.tsx"
      route: "/evidence"
  api_client: "frontend/src/lib/api/evidence.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_evidence_intelligence.py"
      endpoints_tested: ["POST /evidence", "GET /evidence", "POST /evidence/{id}/approve"]
  unit:
    - file: "backend/tests/unit/application/test_ingestion_pipeline.py"
    - file: "backend/tests/unit/application/test_ingestion_parsers.py"
    - file: "backend/tests/unit/application/test_extraction.py"

documentation:
  confluence:
    page_id: "2457602"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2457602"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-8"
      title: "Evidence Upload & Versionierung"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["upload", "read", "approve", "delete"]
    - name: "compliance_manager"
      can: ["upload", "read", "approve"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Agenten dürfen Evidence NICHT genehmigen — nur Analyse-Empfehlungen erstellen"

configuration:
  env_vars:
    - name: "S3_BUCKET_NAME"
      required: true
      description: "S3-Bucket für Evidence-Dateien"
    - name: "EMBEDDING_MODEL"
      required: false
      default: "BAAI/bge-small-en-v1.5"
      description: "HuggingFace-Modell für pgvector Embeddings (384 Dims)"

external_dependencies:
  - name: "pgvector (PostgreSQL Extension)"
    type: "Database"
    description: "IVFFlat Index, cosine similarity, 384 Dimensionen"
    fallback: "Volltext-Suche als Fallback"
  - name: "AWS S3"
    type: "Storage"
    description: "Primärspeicher für Evidence-Dateien"
    fallback: "Lokales Dateisystem (nur Dev)"
```

---

### 07 · Compliance Lifecycle

```yaml
feature:
  name: "Compliance Lifecycle"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/compliance/gap_engine.py"
      class: "GapEngine"
      methods:
        - "identify_gaps(org_id, framework)"
        - "calculate_gap_severity(gap)"
    - file: "backend/application/compliance/mapping_engine.py"
      class: "MappingEngine"
      methods:
        - "map_controls_to_framework(controls, framework)"
        - "get_coverage_report(org_id, framework)"
    - file: "backend/application/compliance/frameworks.py"
      class: "FrameworkService"
    - file: "backend/application/compliance/org_status.py"
      class: "OrgComplianceStatus"
    - file: "backend/application/compliance/scoring.py"
      class: "ComplianceScoring"
    - file: "backend/application/compliance/coverage.py"
      class: "CoverageCalculator"
    - file: "backend/application/compliance/verdict.py"
      class: "ComplianceVerdict"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/compliance/gaps"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/compliance/gaps/{gap_id}"
      auth: "Bearer JWT"
    - method: "PATCH"
      path: "/api/v1/compliance/gaps/{gap_id}"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/compliance/center"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/compliance/frameworks"
      auth: "Bearer JWT"
  models:
    - table: "framework_mappings"
      file: "backend/infrastructure/persistence/models/framework_mapping.py"
      key_fields: ["id", "organization_id", "framework", "control_id", "status"]
    - table: "regulatory"
      file: "backend/infrastructure/persistence/models/regulatory.py"
    - table: "regulatory_calendar"
      file: "backend/infrastructure/persistence/models/regulatory_calendar.py"
  migrations:
    - file: "backend/alembic/versions/026_m31_1_hardening.py"
      description: "Compliance-Reporting Hardening M31.1"
    - file: "backend/alembic/versions/027_compliance_reports.py"
      description: "Compliance-Berichte Tabellen"
    - file: "backend/alembic/versions/060_m47_1_framework_mapping.py"
      description: "Framework-Mapping Engine (LkSG/CSDDD/CSRD/SFDR)"
    - file: "backend/alembic/versions/059_m47_regulatory_calendar.py"
      description: "Regulatorischer Kalender"

frontend:
  pages:
    - file: "frontend/src/app/(app)/compliance/page.tsx"
      route: "/compliance"
    - file: "frontend/src/app/(app)/compliance/gaps/page.tsx"
      route: "/compliance/gaps"
    - file: "frontend/src/app/(app)/compliance/center/page.tsx"
      route: "/compliance/center"
  api_client: "frontend/src/lib/api/compliance.ts"

tests:
  unit:
    - file: "backend/tests/unit/application/test_compliance.py"
    - file: "backend/tests/unit/application/test_compliance_reasoning.py"
    - file: "backend/tests/unit/application/test_m31_gap_engine.py"
    - file: "backend/tests/unit/application/test_m31_mapping_engine.py"
    - file: "backend/tests/unit/application/test_m31_org_status.py"
    - file: "backend/tests/unit/application/test_m31_1_reports.py"
    - file: "backend/tests/unit/application/test_m31_1_ownership.py"
    - file: "backend/tests/unit/application/test_m31_1_versioning.py"
    - file: "backend/tests/unit/application/test_m32_1_csddd_engine.py"

documentation:
  confluence:
    page_id: "2457619"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2457619"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-2"
  stories:
    - key: "KAN-15"
      title: "LkSG Compliance Mapping"
      status: "To Do"
    - key: "KAN-16"
      title: "CSDDD Framework Coverage"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["read", "update_gap_status", "assign_owner"]
    - name: "compliance_manager"
      can: ["read", "update_gap_status"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Agenten dürfen Compliance-Gaps NICHT schließen — nur eskalieren"
    - "Regulatorischer Kalender: LkSG, CSDDD, CSRD, SFDR Fristen"
```

---

### 08 · AI Copilot / RAG

```yaml
feature:
  name: "AI Copilot / RAG"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/copilot/copilot_service.py"
      class: "CopilotService"
      methods:
        - "ask(question, conversation_id, org_id)"
        - "get_conversations(org_id)"
        - "create_conversation(org_id)"
        - "get_messages(conversation_id)"
    - file: "backend/application/copilot/context_assembler.py"
      class: "ContextAssembler"
    - file: "backend/application/copilot/intent_detector.py"
      class: "IntentDetector"
    - file: "backend/application/copilot/citation_extractor.py"
      class: "CitationExtractor"
    - file: "backend/application/copilot/citation_integrity.py"
      class: "CitationIntegrityChecker"
    - file: "backend/application/copilot/confidence_calculator.py"
      class: "ConfidenceCalculator"
    - file: "backend/application/copilot/audit_package_service.py"
      class: "AuditPackageService"
    - file: "backend/application/copilot/executive_brief_engine.py"
      class: "ExecutiveBriefEngine"
    - file: "backend/application/copilot/action_advisor_engine.py"
      class: "ActionAdvisorEngine"
    - file: "backend/application/copilot/suggested_questions.py"
      class: "SuggestedQuestionsEngine"
    - file: "backend/application/copilot/analytics_service.py"
      class: "CopilotAnalyticsService"
    - file: "backend/application/copilot/reproducibility_verifier.py"
      class: "ReproducibilityVerifier"
    - file: "backend/application/copilot/contradiction_detector.py"
      class: "ContradictionDetector"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/copilot/ask"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager", "viewer"]
      schema_in: "CopilotQuestionRequest"
      schema_out: "CopilotAnswerResponse"
    - method: "GET"
      path: "/api/v1/copilot/conversations"
      auth: "Bearer JWT"
      schema_out: "list[CopilotConversationSummary]"
    - method: "POST"
      path: "/api/v1/copilot/conversations"
      auth: "Bearer JWT"
      schema_out: "CopilotConversationSummary"
    - method: "GET"
      path: "/api/v1/copilot/conversations/{id}/messages"
      auth: "Bearer JWT"
      schema_out: "list[CopilotMessageResponse]"
    - method: "GET"
      path: "/api/v1/copilot/suggested-questions"
      auth: "Bearer JWT"
      schema_out: "SuggestedQuestionsResponse"
    - method: "GET"
      path: "/api/v1/copilot/executive-brief"
      auth: "Bearer JWT"
      roles: ["admin", "executive"]
      schema_out: "ExecutiveBriefResponse"
    - method: "GET"
      path: "/api/v1/copilot/action-advisor"
      auth: "Bearer JWT"
      schema_out: "ActionAdvisorResponse"
    - method: "GET"
      path: "/api/v1/copilot/audit/{message_id}"
      auth: "Bearer JWT"
      schema_out: "AuditPackageResponse"
    - method: "GET"
      path: "/api/v1/copilot/audit/{message_id}/verify"
      auth: "Bearer JWT"
      schema_out: "VerificationResultResponse"
  models:
    - table: "copilot_conversations"
      file: "backend/infrastructure/persistence/models/copilot.py"
    - table: "copilot_messages"
      file: "backend/infrastructure/persistence/models/copilot.py"
    - table: "copilot_audit"
      file: "backend/infrastructure/persistence/models/copilot_audit.py"
    - table: "evidence_chunks"
      file: "backend/infrastructure/persistence/models/evidence_chunk.py"
      key_fields: ["embedding (384 dims, pgvector)"]
  migrations:
    - file: "backend/alembic/versions/030_m33_copilot.py"
      description: "Copilot-Basis-Tabellen"
    - file: "backend/alembic/versions/032_m33_2_copilot_enterprise.py"
      description: "Enterprise-Copilot: Audit-Trail, Reproducibility"

frontend:
  api_client: "frontend/src/lib/api/suppliers.ts"

tests:
  unit:
    - file: "backend/tests/integration/api/test_knowledge_api.py"

documentation:
  confluence:
    page_id: "2752513"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2752513"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-3"
  stories:
    - key: "KAN-30"
      title: "AI Copilot RAG Pipeline"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["ask", "read_audit", "verify_answer"]
    - name: "compliance_manager"
      can: ["ask", "read_audit"]
    - name: "viewer"
      can: ["ask"]
  special_restrictions:
    - "Copilot-Antworten enthalten IMMER Quellenangaben (Citations)"
    - "Alle Antworten sind auditierbar via /audit/{message_id}"
    - "Copilot darf KEINE Genehmigungen erteilen oder Daten verändern"

configuration:
  env_vars:
    - name: "ANTHROPIC_API_KEY"
      required: true
      description: "Claude API Key — NIEMALS hardcoden"
    - name: "OPENAI_API_KEY"
      required: false
      description: "Optional für GPT-Fallback"
    - name: "EMBEDDING_MODEL"
      required: false
      default: "BAAI/bge-small-en-v1.5"
      description: "384-dimensionales Embedding-Modell für pgvector"

external_dependencies:
  - name: "Anthropic Claude API"
    type: "API"
    description: "LLM für natürlichsprachige Antworten"
    fallback: "Structured-only Antwort ohne LLM"
  - name: "pgvector"
    type: "Database"
    description: "Vektorähnlichkeitssuche für RAG-Retrieval"
    fallback: "Volltext-Suche (PostgreSQL tsvector)"
```

---

### 09 · Regulatory Reporting (LkSG / CSRD / SFDR / GRI / TCFD)

```yaml
feature:
  name: "Regulatory Reporting"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/reporting/service.py"
      class: "ReportingService"
      methods:
        - "generate_lkseg_report(org_id, year)"
        - "generate_csrd_report(org_id, period)"
        - "generate_sfdr_pai(org_id, period)"
        - "generate_gri_report(org_id, period)"
        - "generate_tcfd_report(org_id, period)"
    - file: "backend/application/reporting/xbrl_exporter.py"
      class: "XBRLExporter"
      methods:
        - "export_ixbrl(report_data)"
        - "validate_taxonomy(report)"
    - file: "backend/application/reporting/sfdr_pai.py"
      class: "SFDRPAIExporter"
    - file: "backend/application/reporting/gri_exporter.py"
      class: "GRIExporter"
    - file: "backend/application/reporting/tcfd_exporter.py"
      class: "TCFDExporter"
    - file: "backend/application/reporting/audit_exporter.py"
      class: "AuditExporter"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/reports"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "ReportCreate"
      schema_out: "ReportResponse"
    - method: "GET"
      path: "/api/v1/reports"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/reports/{report_id}"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/reports/{report_id}/download"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/regulatory-reporting/lkseg"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "POST"
      path: "/api/v1/regulatory-reporting/lkseg/generate"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/regulatory-reporting/csrd"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/regulatory-reporting/sfdr"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/regulatory-reporting/gri"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/regulatory-reporting/tcfd"
      auth: "Bearer JWT"
    - method: "DELETE"
      path: "/api/v1/regulatory-reporting/{report_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "reports"
      file: "backend/infrastructure/persistence/models/report.py"
      key_fields: ["id", "organization_id", "type", "period", "status", "file_key", "is_immutable"]
    - table: "board_reports"
      file: "backend/infrastructure/persistence/models/board_report.py"
  migrations:
    - file: "backend/alembic/versions/013_add_reports.py"
      description: "Basisberichte"
    - file: "backend/alembic/versions/021_add_board_reports.py"
      description: "Board Reports mit Immutability"
    - file: "backend/alembic/versions/024_board_report_immutability.py"
      description: "Immutability-Constraint für veröffentlichte Berichte"
    - file: "backend/alembic/versions/028_m32_disclosure.py"
      description: "CSRD Disclosure-Framework"

frontend:
  pages:
    - file: "frontend/src/app/(app)/reports/page.tsx"
      route: "/reports"
  api_client: "frontend/src/lib/api/reports.ts"

tests:
  unit:
    - file: "backend/tests/unit/application/test_m31_1_reports.py"
    - file: "backend/tests/unit/application/test_m31_1_versioning.py"

documentation:
  confluence:
    page_id: "2785281"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2785281"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-2"
  stories:
    - key: "KAN-17"
      title: "LkSG Jahresbericht Generator"
      status: "To Do"
    - key: "KAN-18"
      title: "CSRD iXBRL Export"
      status: "To Do"
    - key: "KAN-19"
      title: "SFDR PAI Report"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create", "read", "download", "delete"]
    - name: "compliance_manager"
      can: ["create", "read", "download"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Veröffentlichte Berichte sind immutable — kein Überschreiben nach Freigabe"
    - "Board Reports: separates Zugriffsmodell via board_access_token"
```

---

### 10 · Auth, Organizations & MFA

```yaml
feature:
  name: "Auth & Organizations (inkl. MFA)"
  status: "active"
  horizon: "TECH"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/security/"
      class: "AuthService"
      methods:
        - "register(email, password, org_id)"
        - "login(email, password)"
        - "refresh_token(token)"
        - "logout(token)"
        - "get_current_user(token)"
    - file: "backend/application/mfa/"
      class: "MFAService"
      methods:
        - "setup_totp(user_id)"
        - "verify_totp(user_id, code)"
        - "disable_mfa(user_id)"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/auth/register"
      auth: "None (Public)"
      schema_in: "UserCreate"
      schema_out: "TokenResponse"
    - method: "POST"
      path: "/api/v1/auth/login"
      auth: "None (Public)"
      schema_out: "LoginResponse"
    - method: "POST"
      path: "/api/v1/auth/refresh"
      auth: "Refresh Token"
      schema_out: "RefreshResponse"
    - method: "POST"
      path: "/api/v1/auth/logout"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/auth/me"
      auth: "Bearer JWT"
      schema_out: "UserResponse"
    - method: "PATCH"
      path: "/api/v1/auth/me"
      auth: "Bearer JWT"
      schema_out: "UserResponse"
    - method: "POST"
      path: "/api/v1/auth/external-access/revoke"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/organizations"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/organizations"
      auth: "Bearer JWT"
      roles: ["superadmin"]
    - method: "GET"
      path: "/api/v1/users"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "users"
      file: "backend/infrastructure/persistence/models/user.py"
      key_fields: ["id", "organization_id", "email", "role", "is_active"]
    - table: "organizations"
      file: "backend/infrastructure/persistence/models/organization.py"
      key_fields: ["id", "name", "plan", "created_at"]
    - table: "api_keys"
      file: "backend/infrastructure/persistence/models/api_key.py"
    - table: "mfa"
      file: "backend/infrastructure/persistence/models/mfa.py"
    - table: "service_accounts"
      file: "backend/infrastructure/persistence/models/service_account.py"
    - table: "custom_roles"
      file: "backend/infrastructure/persistence/models/custom_role.py"
  migrations:
    - file: "backend/alembic/versions/001_initial_schema.py"
      description: "Basisschema: Users, Organizations"
    - file: "backend/alembic/versions/002_add_user_password_hash.py"
      description: "password_hash Spalte (NIEMALS in API-Response)"
    - file: "backend/alembic/versions/010_add_organization_rbac.py"
      description: "RBAC: Rollen, Berechtigungen"
    - file: "backend/alembic/versions/042_m40_1_identity_hardening.py"
      description: "Identity Hardening: Service Accounts, API Keys"
    - file: "backend/alembic/versions/052_m45_mfa_rls_phase1.py"
      description: "MFA (TOTP) + Row Level Security Phase 1"
    - file: "backend/alembic/versions/054_m45_1_1_rls_phase2.py"
      description: "RLS Phase 2 — vollständige Isolierung"

frontend:
  pages:
    - file: "frontend/src/app/(auth)/"
      route: "/login, /register"
  api_client: "frontend/src/lib/api/auth.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_auth_api.py"
      endpoints_tested: ["POST /auth/register", "POST /auth/login", "GET /auth/me"]
    - file: "backend/tests/integration/api/test_users_api.py"

documentation:
  confluence:
    page_id: "2818049"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2818049"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-4"
  stories:
    - key: "KAN-40"
      title: "MFA / TOTP"
      status: "To Do"
    - key: "KAN-41"
      title: "SSO SAML/OIDC"
      status: "To Do"

permissions:
  roles:
    - name: "superadmin"
      can: ["manage_organizations"]
    - name: "admin"
      can: ["manage_users", "manage_api_keys", "manage_roles"]
    - name: "compliance_manager"
      can: ["read_users"]
    - name: "viewer"
      can: ["read_own_profile"]
  special_restrictions:
    - "password_hash darf NIEMALS in UserResponse erscheinen (Sicherheitsblocker)"
    - "SupplierUser.password_hash darf NIEMALS in SupplierUser API Response erscheinen"
    - "SECRET_KEY, JWT-Schlüssel ausschließlich als Umgebungsvariablen"
```

---

### 11 · AI Agents & Governance

```yaml
feature:
  name: "AI Agents & AI Governance"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/agents/base.py"
      class: "BaseAgent"
    - file: "backend/application/agents/esg_assessment.py"
      class: "ESGAssessmentAgent"
    - file: "backend/application/agents/risk_assessment.py"
      class: "RiskAssessmentAgent"
    - file: "backend/application/agents/recommendation.py"
      class: "RecommendationAgent"
    - file: "backend/application/agents/research.py"
      class: "ResearchAgent"
    - file: "backend/application/agents/reporting.py"
      class: "ReportingAgent"
    - file: "backend/application/agents/governance.py"
      class: "GovernanceAgent"
    - file: "backend/application/agents/retrieval.py"
      class: "RetrievalAgent"
    - file: "backend/application/agents/registry.py"
      class: "AgentRegistry"
    - file: "backend/application/agent_monitoring/agent_monitoring.py"
      class: "AgentMonitoringService"
    - file: "backend/application/ai_governance/"
      class: "AIGovernanceService"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/agents/run"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
      schema_in: "AgentRunRequest"
      schema_out: "AgentRunResponse"
    - method: "GET"
      path: "/api/v1/agents/runs"
      auth: "Bearer JWT"
      schema_out: "list[AgentRunResponse]"
    - method: "GET"
      path: "/api/v1/agents/runs/{run_id}"
      auth: "Bearer JWT"
      schema_out: "AgentRunResponse"
  models:
    - table: "agent_runs"
      file: "backend/infrastructure/persistence/models/agent_run.py"
      key_fields: ["id", "organization_id", "agent_type", "status", "input", "output", "created_at"]
    - table: "agent_monitoring"
      file: "backend/infrastructure/persistence/models/agent_monitoring.py"
    - table: "ai_governance"
      file: "backend/infrastructure/persistence/models/ai_governance.py"
    - table: "recommendations"
      file: "backend/infrastructure/persistence/models/recommendation.py"
  migrations:
    - file: "backend/alembic/versions/004_add_agent_runs.py"
      description: "Agent-Runs Tabelle"
    - file: "backend/alembic/versions/038_m36_monitoring_agents.py"
      description: "Agent-Monitoring Dashboard"
    - file: "backend/alembic/versions/044_m41_ai_governance.py"
      description: "AI Governance Framework"
    - file: "backend/alembic/versions/045_m41_1_hardening.py"
      description: "AI Governance Hardening"

frontend:
  pages:
    - file: "frontend/src/app/(app)/ai-governance/page.tsx"
      route: "/ai-governance"
  api_client: "frontend/src/lib/api/ai-governance.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_agents_api.py"
    - file: "backend/tests/integration/api/test_governance_api.py"
    - file: "backend/tests/integration/api/test_governance_hardening.py"
  unit:
    - file: "backend/tests/unit/application/test_agents.py"
    - file: "backend/tests/unit/application/test_governance_hardening.py"

documentation:
  confluence:
    page_id: "2850817"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2850817"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-3"
  stories:
    - key: "KAN-35"
      title: "AI Governance Dashboard"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["run_agent", "read_runs", "read_governance"]
    - name: "compliance_manager"
      can: ["run_agent", "read_runs"]
    - name: "viewer"
      can: ["read_runs"]
  special_restrictions:
    - "Agenten dürfen NIEMALS genehmigen: approve_assessment(), close_finding(), resolve_compliance_gap(), approve_evidence(), close_risk()"
    - "Agenten dürfen NUR: create_draft_recommendation(), notify_human(), escalate_to_reviewer(), summarize_findings()"
    - "Human-Approval ist auf Service-Layer architektonisch durchgesetzt"
```

---

### 12 · Dashboard & Executive Intelligence

```yaml
feature:
  name: "Dashboard & Executive Intelligence"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/executive/"
      class: "ExecutiveService"
      methods:
        - "get_executive_dashboard(org_id)"
        - "get_kpi_trends(org_id)"
        - "get_risk_register(org_id)"
        - "get_heatmaps(org_id)"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/dashboard"
      auth: "Bearer JWT"
      schema_out: "DashboardResponse"
    - method: "GET"
      path: "/api/v1/executive/dashboard"
      auth: "Bearer JWT"
      roles: ["admin", "executive"]
      schema_out: "ExecutiveDashboard"
    - method: "GET"
      path: "/api/v1/executive/kpi-trends"
      auth: "Bearer JWT"
      schema_out: "KPITrendResponse"
    - method: "GET"
      path: "/api/v1/executive/risk-register"
      auth: "Bearer JWT"
      schema_out: "list[RiskRegisterEntry]"
    - method: "GET"
      path: "/api/v1/executive/heatmaps"
      auth: "Bearer JWT"
      schema_out: "ExecutiveHeatmapResponse"
    - method: "GET"
      path: "/api/v1/executive/action-effectiveness"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/executive/governance-metrics"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/executive/command-center"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/executive/findings/export"
      auth: "Bearer JWT"
      description: "CSV-Export aller Findings"
    - method: "GET"
      path: "/api/v1/executive/risks/export"
      auth: "Bearer JWT"
      description: "CSV-Export aller Risks"

frontend:
  pages:
    - file: "frontend/src/app/(app)/dashboard/page.tsx"
      route: "/dashboard"
    - file: "frontend/src/app/(app)/executive/page.tsx"
      route: "/executive"
  api_client: "frontend/src/lib/api/executive.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_executive.py"

documentation:
  confluence:
    page_id: "2850834"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2850834"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-9"
      title: "Executive Dashboard"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["read", "export"]
    - name: "executive"
      can: ["read", "export"]
    - name: "compliance_manager"
      can: ["read"]
    - name: "viewer"
      can: ["read_basic"]
```

---

### 13 · Workflows & Automation

```yaml
feature:
  name: "Workflows & Automation"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/workflows/engine.py"
      class: "WorkflowEngine"
      methods:
        - "run(workflow_type, context)"
        - "get_step_output(run_id, step_index)"
    - file: "backend/application/workflows/executor.py"
      class: "WorkflowExecutor"
    - file: "backend/application/workflows/registry.py"
      class: "WorkflowRegistry"
    - file: "backend/application/workflows/definitions.py"
      class: "WorkflowDefinitions"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/workflows/types"
      auth: "Bearer JWT"
      schema_out: "list[WorkflowTypeInfo]"
    - method: "POST"
      path: "/api/v1/workflows/trigger"
      auth: "Bearer JWT"
      roles: ["admin", "compliance_manager"]
    - method: "GET"
      path: "/api/v1/workflows/jobs"
      auth: "Bearer JWT"
      schema_out: "Page[WorkflowJobResponse]"
    - method: "GET"
      path: "/api/v1/workflows/jobs/{job_id}"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/workflows/runs"
      auth: "Bearer JWT"
      schema_out: "Page[WorkflowRunResponse]"
    - method: "GET"
      path: "/api/v1/workflows/runs/{run_id}"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/workflows/runs/{run_id}/steps/{step_index}/output"
      auth: "Bearer JWT"
  models:
    - table: "workflow_runs"
      file: "backend/infrastructure/persistence/models/workflow_run.py"
      key_fields: ["id", "organization_id", "type", "status", "started_at", "completed_at"]
    - table: "workflow_jobs"
      file: "backend/infrastructure/persistence/models/workflow_job.py"
      key_fields: ["id", "run_id", "step_index", "status", "output"]
  migrations:
    - file: "backend/alembic/versions/005_add_workflow_runs.py"
      description: "Workflow-Runs Tabelle"
    - file: "backend/alembic/versions/006_add_audit_events_and_extend_workflow.py"
      description: "Audit-Events + Workflow-Erweiterung"
    - file: "backend/alembic/versions/009_add_workflow_jobs.py"
      description: "Workflow-Jobs (Step-Level Tracking)"
    - file: "backend/alembic/versions/055_m45_2_s3_celery.py"
      description: "Celery Task Queue für asynchrone Workflows"

frontend:
  api_client: "frontend/src/lib/api/workflows.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_workflows_api.py"

documentation:
  confluence:
    page_id: "2883585"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2883585"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-3"
  stories:
    - key: "KAN-33"
      title: "Workflow-Automatisierung Engine"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["trigger", "read", "cancel"]
    - name: "compliance_manager"
      can: ["trigger", "read"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "Agenten dürfen Workflow-Schritte NICHT genehmigen — nur Human-Approval"

external_dependencies:
  - name: "Celery + Redis"
    type: "Queue"
    description: "Asynchrone Workflow-Ausführung"
    fallback: "Synchrone Ausführung (nur für kleine Workflows)"
```

---

### 14 · Notifications

```yaml
feature:
  name: "Notifications"
  status: "active"
  horizon: "H1"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/notifications/slack_adapter.py"
      class: "SlackAdapter"
      methods:
        - "send_alert(channel, message, severity)"
    - file: "backend/application/notifications/teams_adapter.py"
      class: "TeamsAdapter"
      methods:
        - "send_card(webhook_url, card_data)"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/notifications"
      auth: "Bearer JWT"
      schema_out: "NotificationListResponse"
    - method: "PATCH"
      path: "/api/v1/notifications/{notification_id}/read"
      auth: "Bearer JWT"
      schema_out: "NotificationResponse"
    - method: "PATCH"
      path: "/api/v1/notifications/read-all"
      auth: "Bearer JWT"
  models:
    - table: "notifications"
      file: "backend/infrastructure/persistence/models/notification.py"
      key_fields: ["id", "organization_id", "user_id", "type", "is_read", "payload", "created_at"]
  migrations:
    - file: "backend/alembic/versions/015_add_notifications.py"
      description: "Notifications Tabelle"

frontend:
  pages:
    - file: "frontend/src/app/(app)/notifications/page.tsx"
      route: "/notifications"
  api_client: "frontend/src/lib/api/notifications.ts"

tests:
  integration:
    - file: "backend/tests/integration/api/test_notifications_api.py"

documentation:
  confluence:
    page_id: "2654226"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2654226"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-1"
  stories:
    - key: "KAN-12"
      title: "Notification Center"
      status: "To Do"

external_dependencies:
  - name: "Slack Webhook"
    type: "API"
    description: "Push-Notifications für kritische Events"
    fallback: "Nur In-App-Notification"
  - name: "Microsoft Teams Webhook"
    type: "API"
    description: "Teams-Cards für Enterprise-Kunden"
    fallback: "Nur In-App-Notification"
```

---

### 15 · Supplier Portal (Tier-2 Self-Assessment)

```yaml
feature:
  name: "Supplier Portal"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/supplier_portal/supplier_auth_service.py"
      class: "SupplierAuthService"
      methods:
        - "activate(token, password)"
        - "login(email, password)"
        - "reset_password(email)"
    - file: "backend/application/supplier_portal/questionnaire_service.py"
      class: "QuestionnaireService"
    - file: "backend/application/supplier_portal/evidence_service.py"
      class: "SupplierEvidenceService"
    - file: "backend/application/supplier_portal/dashboard_service.py"
      class: "SupplierDashboardService"
    - file: "backend/application/supplier_portal/remediation_service.py"
      class: "SupplierRemediationService"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/supplier-portal/auth/activate"
      auth: "Activation Token"
    - method: "POST"
      path: "/api/v1/supplier-portal/auth/login"
      auth: "None (Public)"
    - method: "GET"
      path: "/api/v1/supplier-portal/dashboard"
      auth: "SupplierJWT"
      schema_out: "DashboardResponse"
    - method: "GET"
      path: "/api/v1/supplier-portal/evidence/requests"
      auth: "SupplierJWT"
      schema_out: "list[EvidenceRequestResponse]"
    - method: "POST"
      path: "/api/v1/supplier-portal/evidence/upload"
      auth: "SupplierJWT"
    - method: "GET"
      path: "/api/v1/supplier-portal/questionnaires"
      auth: "SupplierJWT"
    - method: "POST"
      path: "/api/v1/supplier-portal/questionnaires/{id}/answers"
      auth: "SupplierJWT"
    - method: "GET"
      path: "/api/v1/supplier-portal/remediation"
      auth: "SupplierJWT"
  models:
    - table: "supplier_portal"
      file: "backend/infrastructure/persistence/models/supplier_portal.py"
      key_fields: ["id", "supplier_id", "user_type", "email", "is_active"]
  migrations:
    - file: "backend/alembic/versions/036_m35_supplier_portal.py"
      description: "Supplier-Portal Tabellen"
    - file: "backend/alembic/versions/037_m35_1_hardening.py"
      description: "Supplier-Portal Hardening: Rate-Limiting, Aktivierung"

frontend:
  api_client: "frontend/src/lib/api/suppliers.ts"

documentation:
  confluence:
    page_id: "2916353"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2916353"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-2"
  stories:
    - key: "KAN-20"
      title: "Supplier Self-Service Portal"
      status: "To Do"

permissions:
  roles:
    - name: "supplier_user"
      can: ["read_own_dashboard", "upload_evidence", "answer_questionnaires"]
  special_restrictions:
    - "Supplier-Nutzer können KEINE Daten anderer Organisationen sehen"
    - "SupplierUser.password_hash darf NIEMALS in API-Response erscheinen"
```

---

### 16 · Financial ESG & GHG Accounting

```yaml
feature:
  name: "Financial ESG & GHG Accounting"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/financial_esg/kpi_service.py"
      class: "FinancialKPIService"
    - file: "backend/application/financial_esg/carbon_cost_service.py"
      class: "CarbonCostService"
    - file: "backend/application/financial_esg/taxonomy_service.py"
      class: "TaxonomyAssessmentService"
    - file: "backend/application/financial_esg/value_service.py"
      class: "ValueCreationService"
    - file: "backend/application/financial_esg/finance_service.py"
      class: "FinanceInstrumentService"
    - file: "backend/application/financial_esg/readiness_service.py"
      class: "FinancingReadinessService"
    - file: "backend/application/ghg/ghg_engine.py"
      class: "GHGEngine"
      methods:
        - "calculate_scope1(inventory)"
        - "calculate_scope2(inventory)"
        - "calculate_scope3(inventory)"
  api_endpoints:
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/kpis"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/financial-esg/{org_id}/kpis"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/carbon-cost"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/risk"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/taxonomy"
      auth: "Bearer JWT"
    - method: "PATCH"
      path: "/api/v1/financial-esg/{org_id}/taxonomy/{assessment_id}/status"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/transition-plans"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/value-creation"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/financial-esg/{org_id}/finance"
      auth: "Bearer JWT"
  models:
    - table: "financial_esg"
      file: "backend/infrastructure/persistence/models/financial_esg.py"
    - table: "ghg"
      file: "backend/infrastructure/persistence/models/ghg.py"
      key_fields: ["id", "organization_id", "scope", "category", "tonnes_co2e", "period"]
  migrations:
    - file: "backend/alembic/versions/047_m43_financial_esg.py"
      description: "Financial ESG Tabellen"
    - file: "backend/alembic/versions/046_m42_sustainability.py"
      description: "Sustainability + GHG Accounting"
    - file: "backend/alembic/versions/051_fix_carbon_inventory_columns.py"
      description: "Bugfix: Carbon Inventory Spalten"

frontend:
  pages:
    - file: "frontend/src/app/(app)/financial-esg/page.tsx"
      route: "/financial-esg"
    - file: "frontend/src/app/(app)/sustainability/page.tsx"
      route: "/sustainability"
  api_client: "frontend/src/lib/api/financial-esg.ts"

tests:
  unit:
    - file: "backend/tests/unit/application/test_kpi_calculator.py"
    - file: "backend/tests/unit/application/test_esg_categorizer.py"

documentation:
  confluence:
    page_id: "2949121"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2949121"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-5"
  stories:
    - key: "KAN-60"
      title: "GHG Scope 1/2/3 Engine"
      status: "To Do"
    - key: "KAN-61"
      title: "EU Taxonomie Assessment"
      status: "To Do"
    - key: "KAN-62"
      title: "Carbon Cost Modellierung"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create", "read", "update"]
    - name: "compliance_manager"
      can: ["read", "create_draft"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "GHG-Berechnungen: deterministisch und auditierbar — kein LLM-basiertes Scoring"
```

---

### 17 · Strategy & M44 Scenario Forecasting

```yaml
feature:
  name: "Strategy & M44 Scenario Forecasting"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/strategy/digital_twin_service.py"
      class: "DigitalTwinService"
    - file: "backend/application/strategy/scenario_service.py"
      class: "ScenarioService"
    - file: "backend/application/strategy/forecast_service.py"
      class: "ForecastService"
    - file: "backend/application/strategy/stress_test_service.py"
      class: "StressTestService"
    - file: "backend/application/strategy/planning_service.py"
      class: "StrategicPlanningService"
    - file: "backend/application/strategy/board_simulation_service.py"
      class: "BoardSimulationService"
    - file: "backend/application/strategy/comparison_service.py"
      class: "ScenarioComparisonService"
    - file: "backend/application/strategy/pathway_service.py"
      class: "PathwayService"
    - file: "backend/application/strategy/template_service.py"
      class: "TemplateService"
    - file: "backend/application/strategy/methodology_service.py"
      class: "MethodologyService"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/strategy/{org_id}/digital-twin"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/digital-twin"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/strategy/{org_id}/plans"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/plans"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/strategy/{org_id}/scenarios"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/scenarios"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/scenarios/{scenario_id}/execute"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/strategy/{org_id}/stress-tests/climate"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/stress-tests/climate"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/stress-tests/supplier-shock"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/strategy/{org_id}/stress-tests/financial"
      auth: "Bearer JWT"
  models:
    - table: "strategy"
      file: "backend/infrastructure/persistence/models/strategy.py"
      key_fields: ["id", "organization_id", "type", "status", "payload", "created_at"]
  migrations:
    - file: "backend/alembic/versions/048_m44_strategy.py"
      description: "Strategy-Tabellen: Digital Twin, Pläne, Szenarien"
    - file: "backend/alembic/versions/049_m44_1_strategy_completion.py"
      description: "Stress-Tests, Board-Simulation, Vergleiche"

frontend:
  pages:
    - file: "frontend/src/app/(app)/strategy/page.tsx"
      route: "/strategy"
    - file: "frontend/src/app/(app)/strategy/digital-twin/page.tsx"
      route: "/strategy/digital-twin"
    - file: "frontend/src/app/(app)/strategy/scenarios/page.tsx"
      route: "/strategy/scenarios"
    - file: "frontend/src/app/(app)/strategy/stress-tests/page.tsx"
      route: "/strategy/stress-tests"
    - file: "frontend/src/app/(app)/strategy/board-simulation/page.tsx"
      route: "/strategy/board-simulation"
    - file: "frontend/src/app/(app)/strategy/comparisons/page.tsx"
      route: "/strategy/comparisons"
    - file: "frontend/src/app/(app)/strategy/forecasts/page.tsx"
      route: "/strategy/forecasts"
    - file: "frontend/src/app/(app)/strategy/pathways/page.tsx"
      route: "/strategy/pathways"
    - file: "frontend/src/app/(app)/strategy/methodologies/page.tsx"
      route: "/strategy/methodologies"
    - file: "frontend/src/app/(app)/strategy/templates/page.tsx"
      route: "/strategy/templates"
    - file: "frontend/src/app/(app)/strategy/reports/page.tsx"
      route: "/strategy/reports"

tests:
  integration:
    - file: "backend/tests/integration/test_m44_strategy_integration.py"

documentation:
  confluence:
    page_id: "2981889"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2981889"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-5"
  stories:
    - key: "KAN-55"
      title: "M44 Strategy Simulation Engine"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create", "read", "execute_scenario"]
    - name: "compliance_manager"
      can: ["read"]
    - name: "viewer"
      can: ["read"]
  special_restrictions:
    - "M44 Forecasts: deterministisch, erklärbar, auditierbar, reproduzierbar"
    - "VERBOTEN: Generative AI Forecasting, Black-Box Modelle"
    - "Agenten dürfen strategische Risiken NICHT schließen — Human-Approval pflicht"
```

---

### 18 · Supply Chain Network Analysis

```yaml
feature:
  name: "Supply Chain Network Analysis"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/network/"
      class: "NetworkAnalysisService"
      methods:
        - "build_network_graph(org_id)"
        - "calculate_centrality()"
        - "find_clusters()"
        - "identify_critical_paths()"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/network/graph"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/network/nodes"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "DELETE"
      path: "/api/v1/network/nodes/{node_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/network/edges"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/network/analyze"
      auth: "Bearer JWT"
    - method: "POST"
      path: "/api/v1/network/simulate-disruption"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/network/centrality"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/network/clusters"
      auth: "Bearer JWT"
  models:
    - table: "network"
      file: "backend/infrastructure/persistence/models/network.py"
      key_fields: ["id", "organization_id", "node_type", "supplier_id", "parent_id", "tier"]
  migrations:
    - file: "backend/alembic/versions/058_m47_multi_region.py"
      description: "Multi-Region Supply Chain Nodes"

frontend:
  pages:
    - file: "frontend/src/app/(app)/network/page.tsx"
      route: "/network"
  components:
    - file: "frontend/src/components/network/"
      purpose: "Interaktive Netzwerk-Visualisierung"

documentation:
  confluence:
    page_id: "3014657"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3014657"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-5"
  stories:
    - key: "KAN-57"
      title: "Supply Chain Network Visualisierung"
      status: "To Do"
```

---

### 19 · Sector Intelligence

```yaml
feature:
  name: "Sector Intelligence"
  status: "active"
  horizon: "H2"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/external_intelligence/sector_benchmark_service.py"
      class: "SectorBenchmarkService"
      methods:
        - "get_sector_benchmarks(sector_code)"
        - "compare_supplier_to_sector(supplier_id, sector_code)"
        - "refresh_benchmarks()"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/sectors"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/sectors/{sector_id}/benchmarks"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/sector-intelligence/benchmarks"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/sector-intelligence/compare/{supplier_id}"
      auth: "Bearer JWT"
  models:
    - table: "sectors"
      file: "backend/infrastructure/persistence/models/sector.py"

tests:
  integration:
    - file: "backend/tests/integration/api/test_sectors_api.py"

documentation:
  confluence:
    page_id: "3047425"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3047425"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-3"
  stories:
    - key: "KAN-38"
      title: "Sector Intelligence Benchmarks"
      status: "To Do"
```

---

### 20 · API Platform & Webhooks

```yaml
feature:
  name: "API Platform & Webhooks"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/api_platform/"
      class: "APIPlatformService"
      methods:
        - "create_api_key(org_id, name, scopes)"
        - "revoke_api_key(key_id)"
        - "register_webhook(org_id, url, events)"
        - "trigger_webhook(event, payload)"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/platform/api-keys"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/platform/api-keys"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "DELETE"
      path: "/api/v1/platform/api-keys/{key_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/platform/webhooks"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "POST"
      path: "/api/v1/platform/webhooks"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "api_keys"
      file: "backend/infrastructure/persistence/models/api_key.py"
    - table: "webhooks"
      file: "backend/infrastructure/persistence/models/webhook.py"
  migrations:
    - file: "backend/alembic/versions/022_add_api_platform.py"
      description: "API-Platform: API Keys"
    - file: "backend/alembic/versions/023_add_webhook_payload.py"
      description: "Webhook-Payload-Logging"
    - file: "backend/alembic/versions/061_m48_1_integrations.py"
      description: "External Integrations Framework"

frontend:
  pages:
    - file: "frontend/src/app/(app)/integrations/page.tsx"
      route: "/integrations"
  api_client: "frontend/src/lib/api/platform.ts"

tests:
  unit:
    - file: "backend/tests/unit/application/test_api_platform.py"
  integration:
    - file: "backend/tests/integration/api/test_api_platform.py"

documentation:
  confluence:
    page_id: "3047442"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3047442"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-6"
  stories:
    - key: "KAN-75"
      title: "API Platform + Webhooks"
      status: "To Do"

permissions:
  roles:
    - name: "admin"
      can: ["create_key", "revoke_key", "manage_webhooks"]
  special_restrictions:
    - "API-Key darf nach Erstellung nur einmal angezeigt werden (nicht retrievable)"
```

---

### 21 · Audit & Security

```yaml
feature:
  name: "Audit Trail & Security Audit"
  status: "active"
  horizon: "TECH"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/security/"
      class: "AuditService"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/audit"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/audit/{event_id}"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/security-audit/findings"
      auth: "Bearer JWT"
      roles: ["admin"]
  models:
    - table: "audit_events"
      file: "backend/infrastructure/persistence/models/audit_event.py"
      key_fields: ["id", "organization_id", "user_id", "action", "resource_type",
                   "resource_id", "ip_address", "timestamp"]
    - table: "pentest_findings"
      file: "backend/infrastructure/persistence/models/pentest_finding.py"
    - table: "soc2_controls"
      file: "backend/infrastructure/persistence/models/soc2_control.py"
    - table: "production_checklist"
      file: "backend/infrastructure/persistence/models/production_checklist.py"
  migrations:
    - file: "backend/alembic/versions/006_add_audit_events_and_extend_workflow.py"
      description: "Audit-Events Tabelle"
    - file: "backend/alembic/versions/063_m49_security_audit.py"
      description: "Security Audit: Pentest-Findings, SOC2 Controls, Prod-Checklist"

frontend:
  pages:
    - file: "frontend/src/app/(app)/auditor/page.tsx"
      route: "/auditor"

tests:
  integration:
    - file: "backend/tests/integration/api/test_audit_api.py"

documentation:
  confluence:
    page_id: "3080193"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3080193"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-4"
  stories:
    - key: "KAN-48"
      title: "SOC2 Type II Controls"
      status: "To Do"
```

---

### 22 · Surveillance & Early Warning

```yaml
feature:
  name: "Surveillance & Early Warning System"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/surveillance/portfolio_monitor.py"
      class: "PortfolioMonitor"
    - file: "backend/application/surveillance/early_warning_engine.py"
      class: "EarlyWarningEngine"
    - file: "backend/application/surveillance/emerging_risk_engine.py"
      class: "EmergingRiskEngine"
    - file: "backend/application/surveillance/risk_drift_engine.py"
      class: "RiskDriftEngine"
    - file: "backend/application/surveillance/predictive_escalation_engine.py"
      class: "PredictiveEscalationEngine"
    - file: "backend/application/surveillance/correlation_engine.py"
      class: "CorrelationEngine"
    - file: "backend/application/surveillance/watchlist_service.py"
      class: "WatchlistService"
  models:
    - table: "surveillance"
      file: "backend/infrastructure/persistence/models/surveillance.py"

frontend:
  pages:
    - file: "frontend/src/app/(app)/surveillance/page.tsx"
      route: "/surveillance"

documentation:
  confluence:
    page_id: "3112961"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3112961"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-5"
  stories:
    - key: "KAN-56"
      title: "Early Warning & Portfolio Monitor"
      status: "To Do"
```

---

### 23 · Sustainability & Climate

```yaml
feature:
  name: "Sustainability & Climate Tracking"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/sustainability/carbon_service.py"
      class: "CarbonService"
    - file: "backend/application/sustainability/climate_service.py"
      class: "ClimateService"
    - file: "backend/application/sustainability/kpi_service.py"
      class: "SustainabilityKPIService"
    - file: "backend/application/sustainability/roadmap_service.py"
      class: "SustainabilityRoadmapService"
    - file: "backend/application/sustainability/scoring_service.py"
      class: "SustainabilityScoringService"
  models:
    - table: "sustainability"
      file: "backend/infrastructure/persistence/models/sustainability.py"
  migrations:
    - file: "backend/alembic/versions/046_m42_sustainability.py"
      description: "Sustainability-Tracking: Carbon, Climate, KPIs"

frontend:
  pages:
    - file: "frontend/src/app/(app)/sustainability/page.tsx"
      route: "/sustainability"

documentation:
  confluence:
    page_id: "3145729"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3145729"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-5"
  stories:
    - key: "KAN-58"
      title: "Carbon Footprint Tracking"
      status: "To Do"
```

---

### 24 · Operating System (Collaboration, Recommendations)

```yaml
feature:
  name: "EIOS Operating System (OS)"
  status: "active"
  horizon: "H3"
  last_updated: "2026-06-29"

backend:
  services:
    - file: "backend/application/collaboration/"
      class: "CollaborationService"
    - file: "backend/application/operating_system/"
      class: "OperatingSystemService"
  api_endpoints:
    - method: "GET"
      path: "/api/v1/operating-system"
      auth: "Bearer JWT"
      roles: ["admin"]
    - method: "GET"
      path: "/api/v1/recommendations"
      auth: "Bearer JWT"
    - method: "GET"
      path: "/api/v1/comments"
      auth: "Bearer JWT"
  models:
    - table: "operating_system"
      file: "backend/infrastructure/persistence/models/operating_system.py"
    - table: "comments"
      file: "backend/infrastructure/persistence/models/comment.py"
    - table: "decisions"
      file: "backend/infrastructure/persistence/models/decision.py"
    - table: "tasks"
      file: "backend/infrastructure/persistence/models/task.py"
    - table: "projects"
      file: "backend/infrastructure/persistence/models/project.py"
    - table: "processes"
      file: "backend/infrastructure/persistence/models/process.py"
    - table: "controls"
      file: "backend/infrastructure/persistence/models/control.py"
    - table: "policies"
      file: "backend/infrastructure/persistence/models/policy.py"
  migrations:
    - file: "backend/alembic/versions/017_add_collaboration.py"
      description: "Collaboration: Kommentare, Erwähnungen"
    - file: "backend/alembic/versions/040_m39_operating_system.py"
      description: "EIOS Operating System Tabellen"

frontend:
  pages:
    - file: "frontend/src/app/(app)/operating-system/page.tsx"
      route: "/operating-system"
    - file: "frontend/src/app/(app)/recommendations/page.tsx"
      route: "/recommendations"

documentation:
  confluence:
    page_id: "3178497"
    url: "https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3178497"
    last_updated: "2026-06-29"
    status: "current"

jira:
  epic: "KAN-5"
  stories:
    - key: "KAN-64"
      title: "EIOS Operating System"
      status: "To Do"
```

---

## Status-Tracking (alle Features)

| # | Feature | Backend | Frontend | Tests | Confluence | Jira |
|---|---------|---------|----------|-------|------------|------|
| 01 | Supplier Management | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2588673) | KAN-1 |
| 02 | Supplier Digital Twin & Health Engine | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2621441) | KAN-1 |
| 03 | External Intelligence & Sanctions | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2654209) | KAN-1 |
| 04 | Assessments & Findings | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2686977) | KAN-1 |
| 05 | Risk Management | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2719745) | KAN-1 |
| 06 | Evidence Management | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2457602) | KAN-1 |
| 07 | Compliance Lifecycle | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2457619) | KAN-2 |
| 08 | AI Copilot / RAG | ✓ | ⚠️ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2752513) | KAN-3 |
| 09 | Regulatory Reporting | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2785281) | KAN-2 |
| 10 | Auth & Organizations + MFA | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2818049) | KAN-4 |
| 11 | AI Agents & Governance | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2850817) | KAN-3 |
| 12 | Dashboard & Executive | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2850834) | KAN-1 |
| 13 | Workflows & Automation | ✓ | ⚠️ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2883585) | KAN-3 |
| 14 | Notifications | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2654226) | KAN-1 |
| 15 | Supplier Portal | ✓ | ⚠️ | ⚠️ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2916353) | KAN-2 |
| 16 | Financial ESG & GHG | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2949121) | KAN-5 |
| 17 | Strategy & M44 Forecasting | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/2981889) | KAN-5 |
| 18 | Supply Chain Network | ✓ | ✓ | ✗ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3014657) | KAN-5 |
| 19 | Sector Intelligence | ✓ | ⚠️ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3047425) | KAN-3 |
| 20 | API Platform & Webhooks | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3047442) | KAN-6 |
| 21 | Audit Trail & Security | ✓ | ✓ | ✓ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3080193) | KAN-4 |
| 22 | Surveillance & Early Warning | ✓ | ✓ | ✗ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3112961) | KAN-5 |
| 23 | Sustainability & Climate | ✓ | ✓ | ✗ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3145729) | KAN-5 |
| 24 | EIOS Operating System | ✓ | ✓ | ✗ | [⚠️ Draft](https://privaterelay-team-cdwul3gk.atlassian.net/wiki/spaces/EIOS/pages/3178497) | KAN-5 |

Legende: ✓ = vollständig · ⚠️ = unvollständig/draft · ✗ = fehlt

---

## Kritische Sicherheitsregeln (für alle Features gültig)

```
ANTHROPIC_API_KEY  → nur als Umgebungsvariable — NIEMALS hardcoden
OPENAI_API_KEY     → nur als Umgebungsvariable — NIEMALS hardcoden
SECRET_KEY         → nur als Umgebungsvariable — NIEMALS hardcoden
password_hash      → NIEMALS in UserResponse oder API-Response
SupplierUser.password_hash → NIEMALS in SupplierUser API Response
organization_id    → PFLICHT-Filter auf JEDER Datenbank-Query
M43 Scoring        → deterministisch, auditierbar, erklärbar — kein LLM
M44 Forecasting    → deterministisch, erklärbar, auditierbar — kein generatives AI
Agenten            → dürfen NUR empfehlen, eskalieren, notifizieren, zusammenfassen
                   → NIEMALS genehmigen, schließen, bestätigen, abschließen
```
