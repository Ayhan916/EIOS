# EIOS Feature Knowledge Graph

> Versioniert unter `docs/ai/feature-knowledge-graph.md`  
> Zuletzt aktualisiert: 2026-07-07  
> Quellen: 3 parallele Explore-Agents + verifizierte Dateipfade + API-Tests

---

## Kernprinzip

Jedes Feature ist in einem oder mehreren **Core Workflows** verankert.  
Pipeline-Richtung: Supplier → Assessment → Finding → Risk → Recommendation → CAP → Bericht.  
Kein Feature darf isoliert entwickelt oder dokumentiert werden.

---

## Core Workflows

| ID | Name | CSDDD-Artikel | Pipeline |
|----|------|--------------|---------|
| `WF-01` | Lieferketten-Sorgfaltspflicht | Art. 5–10 | Supplier → Scoping → Assessment → Finding → Risk → Recommendation → CAP → Verification → Board Report |
| `WF-02` | Grievance & Remedy | Art. 11–12 | Grievance → Remedy Case → Beneficiary → Action → Closure |
| `WF-03` | Compliance & Disclosure | Art. 16–23 | Requirement Mapping → Compliance Gap → Disclosure Response → Reporting Package → ESAP Export |
| `WF-04` | Stakeholder Engagement | Art. 13 | Stakeholder → Consultation → Feedback → Risk-Update |
| `WF-05` | Effectiveness Monitoring | Art. 15 | CAP → Effectiveness Indicator → Review → KPI Dashboard |

---

## Feature Knowledge Graph

---

### F-01 · Supplier Management

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/supplier.py` |
| **API Router** | `backend/interfaces/api/routers/suppliers.py` |
| **DB Model** | `backend/infrastructure/persistence/models/supplier.py` |
| **Migration** | `018_add_supplier_management.py`, `019_supplier_name_uniqueness.py`, `020_add_supplier_scores.py` |
| **Frontend Liste** | `/suppliers` → `frontend/src/app/(app)/suppliers/page.tsx` ✅ |
| **Frontend Detail** | `/suppliers/[id]` → `frontend/src/app/(app)/suppliers/[id]/page.tsx` ✅ |
| **Tests** | `tests/unit/domain/test_supplier.py`, `tests/unit/application/test_supplier_scorer.py`, `tests/integration/api/test_suppliers.py`, `test_supplier_hardening.py`, `test_supplier_intelligence.py` |

**API-Endpunkte:**
- `GET /suppliers/` — paginierte Liste (org-scoped)
- `POST /suppliers/` — Lieferant anlegen (analyst)
- `GET /suppliers/{id}` — Detail
- `PATCH /suppliers/{id}` — Update
- `DELETE /suppliers/{id}` — Löschen
- `GET /suppliers/{id}/assessments` — zugehörige Assessments
- `GET /suppliers/{id}/risk-profile` — Risikoprofil

**Berechtigungen:** `analyst` (write), alle authentifizierten User (read)  
**Upstream:** — (Root-Entität, kein FK-Upstream)  
**Downstream:** Assessment (`supplier_id`), SupplierScore (`supplier_id`), SupplierDigitalTwin, PrioritizationDecision  
**Workflow:** WF-01 Step 1

**Gaps:**
- Kein dedizierter Application-Service in `application/` (Logik in Router/Repository)
- Kein Supplier-Portal-Link aus Detail-Seite direkt sichtbar

---

### F-02 · Assessment

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/assessment.py` |
| **API Router** | `backend/interfaces/api/routers/assessments.py` |
| **DB Model** | `backend/infrastructure/persistence/models/assessment.py` |
| **Migration** | `007_extend_assessment_quality.py` (u.a.) |
| **Frontend Liste** | `/assessments` → `frontend/src/app/(app)/assessments/page.tsx` ✅ |
| **Frontend Detail** | `/assessments/[id]` → `frontend/src/app/(app)/assessments/[id]/page.tsx` ✅ |
| **Tests** | `tests/integration/api/test_assessments_api.py` |

**API-Endpunkte:**
- `POST /assessments/` — erstellen
- `GET /assessments/` — paginiert
- `GET /assessments/{id}` — Detail
- `GET /assessments/{id}/findings` — Findings
- `GET /assessments/{id}/risks` — Risks
- `GET /assessments/{id}/score-breakdown` — Scoring-Analyse
- `GET /assessments/{id}/evidence-chain` — Evidence-Lineage
- `GET /assessments/{id}/score-simulation` — What-if
- `GET /assessments/{id}/brief` — Executive Brief
- `PATCH /assessments/{id}` — Update / Approve

**Berechtigungen:** `analyst` (write/approve), alle authentifizierten User (read)  
**Upstream:** Organization (`organization_id`), Supplier (`supplier_id`, optional), Sector (`sector_id`, optional)  
**Downstream:** Finding (`assessment_id`), Risk (`assessment_id`), Recommendation (`assessment_id`), Evidence (M2M via `assessment_evidence`)  
**Workflow:** WF-01 Step 2

**Gaps:**
- Kein dedizierter Application-Service in `application/`
- Review-Workflow (DRAFT → IN_REVIEW → APPROVED) in Frontend nur teilweise sichtbar

---

### F-03 · Finding

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/finding.py` |
| **API Router** | `backend/interfaces/api/routers/findings.py` |
| **DB Model** | `backend/infrastructure/persistence/models/finding.py` |
| **Migration** | `016_add_evidence_intelligence.py` |
| **Frontend Liste** | `/findings` → `frontend/src/app/(app)/findings/page.tsx` ✅ |
| **Frontend Detail** | `/findings/[id]` → `frontend/src/app/(app)/findings/[id]/page.tsx` ✅ |
| **Tests** | Teil von `tests/integration/api/test_assessments_api.py` |

**API-Endpunkte:**
- `GET /findings/` — Liste by `assessment_id`
- `POST /findings/` — erstellen (analyst)
- `GET /findings/{id}` — Detail
- `PATCH /findings/{id}` — Update
- `GET /findings/{id}/related-risks` — verknüpfte Risks
- `DELETE /findings/{id}` — löschen

**Berechtigungen:** `analyst` (write), alle authentifizierten User (read)  
**Upstream:** Assessment (`assessment_id`, required)  
**Downstream:** Risk (M2M via `risk_finding`), Recommendation (M2M via `recommendation_finding`), Evidence (M2M via `finding_evidence`), CorrectiveActionPlan (`finding_id`)  
**Workflow:** WF-01 Step 3

**Gaps:**
- Kein dedizierter Application-Service
- Eigene Testdatei fehlt (nur in `test_assessments_api` enthalten)
- `FindingEvidenceLink`-Erstellung hat kein UI-Einstiegspunkt außer Drag-Drop auf Detail-Seite

---

### F-04 · Risk

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/risk.py` |
| **API Router** | `backend/interfaces/api/routers/risks.py` |
| **DB Model** | `backend/infrastructure/persistence/models/risk.py` |
| **Migration** | Teil des Kern-Schemas |
| **Frontend Liste** | `/risks` → `frontend/src/app/(app)/risks/page.tsx` ✅ |
| **Frontend Detail** | `/risks/[id]` → `frontend/src/app/(app)/risks/[id]/page.tsx` ✅ |
| **Tests** | `tests/integration/api/test_risks_api.py` |

**API-Endpunkte:**
- `POST /risks/` — erstellen (analyst)
- `GET /risks/` — Liste by `assessment_id` oder `sector_id`
- `GET /risks/{id}` — Detail
- `PATCH /risks/{id}` — Update (Status, Level, Owner)
- `DELETE /risks/{id}` — löschen

**Berechtigungen:** `analyst` (write), alle authentifizierten User (read)  
**Upstream:** Assessment (`assessment_id`, optional), Finding (M2M), Sector (`sector_id`, optional)  
**Downstream:** Recommendation (M2M via `recommendation_risk`), Control (M2M via `control_risk`), RequirementMapping  
**Workflow:** WF-01 Step 4

**Gaps:**
- Risk↔Finding-Verknüpfung nur manuell (kein Auto-Link beim Finding-Erstellen)
- Kein dedizierter Application-Service
- `assessment_id` optional → Risks können ohne Assessment existieren (Pipeline-Lücke)

---

### F-05 · Recommendation

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/recommendation.py` |
| **API Router** | `backend/interfaces/api/routers/recommendations.py` |
| **DB Model** | `backend/infrastructure/persistence/models/recommendation.py` |
| **Migration** | `008_add_recommendation_assessment_id.py`, `076_recommendation_evidence_fields.py` |
| **Frontend Liste** | `/recommendations` → `frontend/src/app/(app)/recommendations/page.tsx` ✅ |
| **Frontend Detail** | `/recommendations/[id]` → `frontend/src/app/(app)/recommendations/[id]/page.tsx` ✅ |
| **Tests** | Teil von `tests/integration/api/test_assessments_api.py` |

**API-Endpunkte:**
- `GET /recommendations/` — Liste by `assessment_id`
- `POST /recommendations/` — erstellen (analyst)
- `GET /recommendations/{id}` — Detail
- `PATCH /recommendations/{id}` — Update
- `PATCH /recommendations/{id}/assign` — zuweisen
- `PATCH /recommendations/{id}/close` — schliessen (analyst)

**Berechtigungen:** `analyst` (write/close), alle authentifizierten User (read)  
**Upstream:** Assessment (`assessment_id`, optional), Risk (M2M), Finding (M2M)  
**Downstream:** Decision (M2M via `decision_recommendation`)  
**Workflow:** WF-01 Step 5

**Gaps:**
- Kein dedizierter Application-Service
- Keine eigene Testdatei

---

### F-06 · Corrective Action Plan (CAP)

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/corrective_action_plan.py` — `SQLCAPRepository` |
| **API Router** | `backend/interfaces/api/routers/corrective_action_plan.py` |
| **DB Model** | `backend/infrastructure/persistence/models/corrective_action_plan.py` |
| **Migration** | `082_corrective_action_plans.py` |
| **Frontend Liste** | `/corrective-action-plans` → `frontend/src/app/(app)/corrective-action-plans/page.tsx` ✅ |
| **Frontend Detail** | `/corrective-action-plans/[id]` → `frontend/src/app/(app)/corrective-action-plans/[id]/page.tsx` ✅ |
| **Tests** | `tests/integration/api/test_corrective_action_plans_api.py` ✅ (11 Tests) |

**API-Endpunkte:**
- `POST /corrective-action-plans/` — erstellen (analyst)
- `GET /corrective-action-plans/` — Liste (org-scoped)
- `GET /corrective-action-plans/kpis` — KPI-Zusammenfassung
- `GET /corrective-action-plans/by-finding/{finding_id}` — CAP eines Findings
- `GET /corrective-action-plans/{id}` — Detail
- `PATCH /corrective-action-plans/{id}` — Update
- `PATCH /corrective-action-plans/{id}/commit` → COMMITTED
- `PATCH /corrective-action-plans/{id}/start` → IN_PROGRESS
- `PATCH /corrective-action-plans/{id}/submit-evidence` → EVIDENCE_SUBMITTED
- `PATCH /corrective-action-plans/{id}/verify` → VERIFIED ⚠️ NUR Analyst
- `PATCH /corrective-action-plans/{id}/close` → CLOSED ⚠️ NUR Analyst
- `PATCH /corrective-action-plans/{id}/mark-insufficient` — zurück zu IN_PROGRESS

**Lifecycle:** `DRAFT → COMMITTED → IN_PROGRESS → EVIDENCE_SUBMITTED → VERIFIED → CLOSED`  
**Berechtigungen:** `analyst` (verify/close/mark-insufficient), authentifizierte User (create/update)  
**KI-Agenten verboten:** verify, close, mark-insufficient  
**Upstream:** Finding (`finding_id`, required), Organization (`organization_id`, required)  
**Downstream:** CAPEffectivenessSnapshot, Effectiveness Review  
**Workflow:** WF-01 Step 6, WF-05 Input

**Gaps:**
- CAP ist in `findings/[id]` als Tab-Komponente zusätzlich eingebettet
- Overdue-Erkennung implementiert, aber kein Dashboard-Widget

---

### F-07 · Evidence

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/evidence.py` |
| **API Router** | `backend/interfaces/api/routers/evidences.py` |
| **DB Model** | `backend/infrastructure/persistence/models/evidence.py` |
| **Migration** | `016_add_evidence_intelligence.py` (u.a. M45.2 S3-Erweiterung) |
| **Frontend Liste** | `/evidence` → `frontend/src/app/(app)/evidence/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT — kein `/evidence/[id]` |
| **Tests** | `tests/unit/application/test_m35_evidence.py`, `tests/integration/api/test_evidence_intelligence.py` |

**API-Endpunkte:**
- `POST /evidence/` — erstellen (analyst)
- `GET /evidence/` — paginierte Liste
- `POST /evidence/upload` — Datei-Upload (analyst)
- `GET /evidence/ingestion/{job_id}/status` — Ingestion-Status
- `GET /evidence/{id}` — Detail
- `PATCH /evidence/{id}` — Update
- `GET /evidence/{id}/chunks` — extrahierte Chunks
- `DELETE /evidence/{id}` — löschen

**Ingestion-Status:** `none → ingested → failed → ocr_required`  
**Berechtigungen:** `analyst` (write/upload), alle authentifizierten User (read)  
**Upstream:** Organization (`organization_id`), Assessment (M2M), Finding (M2M)  
**Downstream:** EvidenceChunk (1:N), FindingEvidenceLink (Traceability), ComplianceGap-Berechnung  
**Workflow:** WF-01 parallel zu Steps 2–4

**Gaps:**
- Kein Frontend-Detail-Page
- S3/Celery-Ingestion teilweise implementiert (M45.2)
- Kein semantisches Such-UI (Embedding-Suche API vorhanden, Frontend fehlt)

---

### F-08 · Compliance Gap

| Artefakt | Pfad |
|---------|------|
| **Backend Service** | `backend/application/compliance/gap_engine.py` — `compute_gaps()` |
| **API Router** | `backend/interfaces/api/routers/regulatory.py` (Compliance-Abschnitt) |
| **DB Model** | `backend/infrastructure/persistence/models/regulatory.py` — `ComplianceGapModel` |
| **Migration** | `025_add_regulatory_intelligence.py` |
| **Frontend Liste** | `/compliance/gaps` → `frontend/src/app/(app)/compliance/gaps/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | `tests/unit/application/test_m31_gap_engine.py`, `tests/unit/application/test_compliance.py` |

**API-Endpunkte:**
- `GET /compliance/gaps` — Liste (org-scoped)
- `GET /compliance/gaps/summary` — Zählung nach Severity/Typ/Framework
- `POST /compliance/gaps/recalculate` — neu berechnen
- `PATCH /compliance/gaps/{id}/resolve` — manuell schliessen

**Gap-Typen:** `missing_evidence`, `missing_disclosure`, `unresolved_finding`, `missing_control`  
**Berechtigungen:** `analyst` (recalculate/resolve), alle authentifizierten User (read)  
**Upstream:** RegulationRequirement (Seed-Daten), RequirementMapping, Finding, Risk, Evidence  
**Downstream:** Compliance Report, Disclosure Response, Due Diligence Report  
**Workflow:** WF-03 Step 2

**Gaps:**
- Keine automatische Neuberechnung (nur manueller POST)
- Kein Scheduler / Background-Task
- Frontend zeigt Liste, aber kein Drill-down zu Ursache-Entität

---

### F-09 · Requirement Mapping

| Artefakt | Pfad |
|---------|------|
| **Backend Service** | `backend/application/compliance/mapping_engine.py` — `create_manual_mapping()`, `auto_map_entity()` |
| **API Router** | `backend/interfaces/api/routers/regulatory.py` |
| **DB Model** | `backend/infrastructure/persistence/models/regulatory.py` — `RequirementMappingModel` |
| **Migration** | `025_add_regulatory_intelligence.py` |
| **Frontend** | `/compliance/center` → `frontend/src/app/(app)/compliance/center/page.tsx` ✅ (inline) |
| **Frontend Detail** | ❌ Kein dediziertes Detail-Page |
| **Tests** | `tests/unit/application/test_compliance.py`, `test_m31_gap_engine.py` |

**API-Endpunkte:**
- `POST /compliance/mappings` — manuell erstellen
- `GET /compliance/mappings` — Liste
- `DELETE /compliance/mappings/{id}` — löschen
- `POST /compliance/mappings/auto` — regelbasiertes Auto-Mapping

**Mapping-Methoden:** `manual`, `rule_based`, `ai_assisted`  
**Berechtigungen:** `analyst`  
**Upstream:** Finding, Risk, Recommendation + RegulationRequirement (Seed)  
**Downstream:** ComplianceGap (via `covered_requirement_ids`)  
**Workflow:** WF-03 Step 1

**Gaps:**
- Kein Bulk-Import von Mappings
- Versionierung/Änderungshistorie fehlt
- Confidence-Kalibrierung im Service vorhanden, im UI nicht exponiert

---

### F-10 · Board Signoff / Board Report

| Artefakt | Pfad |
|---------|------|
| **Backend Router** | `backend/interfaces/api/routers/board_signoff.py` |
| **DB Model (Signoff)** | `backend/infrastructure/persistence/models/board_signoff.py` — `BoardSignoffRequestModel`, `BoardDecisionModel` |
| **DB Model (Report)** | `backend/infrastructure/persistence/models/board_report.py` — `BoardReportModel` |
| **Migration** | `096_board_signoff.py`, `021_add_board_reports.py` |
| **Frontend Liste** | `/board-signoff` → `frontend/src/app/(app)/board-signoff/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | ❌ FEHLT — keine dedizierte Testdatei |

**API-Endpunkte:**
- `GET /board-signoff/dashboard` — KPI-Übersicht
- `POST /board-signoff/` — Genehmigungsanfrage erstellen
- `POST /board-signoff/{id}/approve` ⚠️ NUR Board-Mitglied/Admin (Art. 22 CSDDD)
- `POST /board-signoff/{id}/reject` ⚠️ NUR Board-Mitglied/Admin
- `POST /board-signoff/{id}/withdraw`
- `GET /board-signoff/{id}/decisions` — Audit-Trail

**Berechtigungen:** `admin`/Board-Member für approve/reject  
**KI-Agenten absolut verboten** (Art. 22 CSDDD — menschliche Verantwortung)  
**Upstream:** Beliebige Entität (polymorpher `entity_type`: `dd_policy`, `annual_report`, `scoping_study`, `cap_plan`, `remedy_settlement`, `other`)  
**Downstream:** BoardDecision (immutabler Audit-Trail), BoardReport, ESAP-Export  
**Workflow:** WF-01 Step 7, WF-03 End

**Gaps:**
- Kein Frontend-Detail-Page
- Keine Test-Abdeckung
- Kein E-Mail-Benachrichtigungsfluss an Board-Mitglieder

---

### F-11 · Due Diligence Report

| Artefakt | Pfad |
|---------|------|
| **Backend Services** | `backend/application/due_diligence/csddd_engine.py`, `environmental_engine.py`, `human_rights_engine.py`, `lksg_statement_engine.py`, `remediation_engine.py`, `preventive_measures_engine.py` |
| **API Router** | `backend/interfaces/api/routers/due_diligence.py` |
| **DB Model** | `backend/infrastructure/persistence/models/due_diligence.py` — `DueDiligenceReportModel` |
| **Migration** | `029_m32_1_due_diligence.py` |
| **Frontend** | `/due-diligence` → `frontend/src/app/(app)/due-diligence/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | ❌ FEHLT |

**API-Endpunkte:**
- `POST /due-diligence/reports/generate` — Bericht generieren + speichern
- `GET /due-diligence/reports/{id}/download` — PDF-Download
- `GET /due-diligence/human-rights` — Live Human-Rights-Bericht
- `GET /due-diligence/environmental` — Live Environmental-Bericht
- `GET /due-diligence/remediation` — Live Remediation-Bericht
- `GET /due-diligence/preventive-measures` — Präventivmassnahmen

**Berechtigungen:** `analyst` (generate), alle authentifizierten User (read)  
**Upstream:** Supplier, Assessment, Finding, Risk, Recommendation, ComplianceGap, Evidence  
**Downstream:** DueDiligenceReportModel (immutable Snapshot + PDF), ESAP-Export  
**Workflow:** WF-03 Step 5

**Gaps:**
- Keine Tests
- Kein Report-Scheduling
- Kein Versionierungs-Vergleich zwischen Berichten

---

### F-12 · Disclosure (ESRS/CSRD)

| Artefakt | Pfad |
|---------|------|
| **Backend Services** | `backend/application/disclosure/coverage_engine.py`, `readiness_engine.py`, `workflow.py` |
| **API Router** | `backend/interfaces/api/routers/disclosure.py` |
| **DB Models** | `backend/infrastructure/persistence/models/disclosure.py` — `DisclosureFrameworkModel`, `DisclosureRequirementModel`, `DisclosureResponseModel`, `ReportingPackageModel` |
| **Migration** | `028_m32_disclosure.py` |
| **Frontend** | `/disclosure` → `frontend/src/app/(app)/disclosure/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | ❌ FEHLT |

**API-Endpunkte:**
- `GET /reporting/frameworks` — ESRS/CSRD/GRI/ISSB-Frameworks
- `GET /reporting/dashboard` — Org-Disclosure-Dashboard
- `POST /reporting/responses` — Antwort erstellen
- `POST /reporting/responses/{id}/submit` — Draft → In Review
- `POST /reporting/responses/{id}/approve` ⚠️ NUR Analyst/Admin
- `POST /reporting/packages/generate` — Package publizieren
- `GET /reporting/packages/{id}/download` — PDF

**Status-Lifecycle:** `Draft → In Review → Approved → Published`  
**Coverage-Score:** Quantität 30% + Qualität 30% + Diversität 20% + Konfidenz 20%  
**Berechtigungen:** `analyst` (submit/approve), alle authentifizierten User (read)  
**Upstream:** DisclosureFramework/Requirement (Seed), Assessment, Finding, Risk, Evidence  
**Downstream:** ReportingPackage (immutable Snapshot), BoardSignoff, ESAP-Export  
**Workflow:** WF-03 Step 3–4

**Gaps:**
- Keine Tests
- Keine Auto-Befüllung von Antworten aus vorhandenen Findings
- Kein Frontend-Detail für individuelle Disclosure-Responses

---

### F-13 · ESAP Export (Art. 16 CSDDD)

| Artefakt | Pfad |
|---------|------|
| **Backend Service** | `backend/application/csddd/esap_exporter.py` — `build_export()`, `to_json()`, `to_xml()` |
| **API Router** | `backend/interfaces/api/routers/esap_export.py` |
| **DB Model** | `backend/infrastructure/persistence/models/esap.py` — `ESAPSubmissionModel` |
| **Migration** | `098_phase4_csddd.py` |
| **Frontend** | `/esap-export` → `frontend/src/app/(app)/esap-export/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | ❌ FEHLT |

**API-Endpunkte:**
- `GET /esap/taxonomy` — EIOS→ESAP/XBRL-Mapping
- `GET /esap/export` — JSON oder XML Export
- `GET /esap/validate` — Vorab-Validierung
- `POST /esap/submissions` — Einreichung anlegen
- `POST /esap/submissions/{id}/submit` — als eingereicht markieren

**Status:** `draft → ready → submitted`  
**Berechtigungen:** `admin`  
**Upstream:** DD Policy, Risk, CAP, Remedy Case, Board Signoff, Effectiveness Review, Stakeholder  
**Downstream:** ESAPSubmissionModel (Audit-Trail)  
**Workflow:** WF-03 Step 6 (Terminal)

**Gaps:**
- Keine Tests
- Kein automatisches Schema-Validierung gegen offizielle EFRAG-Taxonomie
- Direkte ESAP-Plattform-Integration steht ca. ab 2031 zur Verfügung

---

### F-14 · Compliance Report

| Artefakt | Pfad |
|---------|------|
| **Backend Service** | `backend/application/reporting/service.py` — `ReportService.generate()` |
| **API Router** | `backend/interfaces/api/routers/reports.py`, `regulatory.py` |
| **DB Model** | `backend/infrastructure/persistence/models/regulatory.py` — `ComplianceReportModel` |
| **Migration** | `025_add_regulatory_intelligence.py` |
| **Frontend** | `/compliance/reports` → `frontend/src/app/(app)/compliance/reports/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT (direkter Download) |
| **Tests** | `tests/unit/application/test_compliance.py` |

**API-Endpunkte:**
- `POST /reports/generate` — Executive-PDF für Assessment
- `GET /compliance/reports` — Liste
- `GET /compliance/reports/{id}/download` — Download
- `GET /compliance/reports/csrd-gap` — CSRD-Gap-Bericht
- `GET /compliance/reports/esrs-readiness` — ESRS-Readiness-Bericht
- `GET /compliance/reports/csddd-due-diligence` — CSDDD-Bericht

**Berechtigungen:** `analyst`  
**Upstream:** Assessment, Finding, Evidence, Risk, Recommendation, ReviewAction, ComplianceGap  
**Downstream:** ComplianceReportModel (immutable Snapshot + PDF)  
**Workflow:** WF-03 End, WF-01 End

**Gaps:**
- Kein Scheduling
- Kein Multi-Language-PDF-Export
- Kein Template-Customizing

---

### F-15 · Grievance (CSDDD Art. 11/14 · LkSG §8)

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/grievance.py` |
| **API Router** | `backend/interfaces/api/routers/grievance.py` |
| **DB Model** | `backend/infrastructure/persistence/models/supplier_portal.py` (Zeile ~367) — Tabelle `grievance_reports` |
| **Migration** | `077_grievance_mechanism.py` |
| **Frontend Intern** | Teil von `/stakeholders` ✅ |
| **Frontend Extern** | Supplier-Portal (öffentlich, ohne Auth) |
| **Frontend Detail** | ❌ FEHLT — kein `/grievances/[id]` im Haupt-App |
| **Tests** | Referenziert in `test_compliance.py` u.a. |

**API-Endpunkte:**
- `POST /grievances/submit` ⚠️ ÖFFENTLICH — kein Auth (anonyme Einreichung)
- `GET /grievances/status/{reference_code}` ⚠️ ÖFFENTLICH (Statusabfrage)
- `GET /grievances/` — intern, Liste (analyst)
- `GET /grievances/{id}` — intern, Detail
- `PATCH /grievances/{id}/status` — Status-Update (analyst)
- `POST /grievances/{id}/create-remedy-case` — Remedy Case erstellen

**Sicherheit:** `submitted_by_email`, `submitted_by_name`, `submitter_ip` — **NIEMALS in API-Response** (PII)  
**Berechtigungen:** Öffentlich (submit/status), `analyst` (intern)  
**Upstream:** Organization (optional), Supplier (optional)  
**Downstream:** Finding (auto-created bei `status=investigating`), Remedy Case  
**Workflow:** WF-02 Step 1

**Gaps:**
- Kein dediziertes Frontend für internes Grievance-Management
- Grievance→Finding-Auto-Erstellung nicht implementiert (nur manuell dokumentiert)

---

### F-16 · Remedy Case (CSDDD Art. 12)

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/remedy_case.py` |
| **API Router** | `backend/interfaces/api/routers/remedy_cases.py` |
| **DB Models** | `backend/infrastructure/persistence/models/remedy_case.py` — `RemedyCaseModel`, `RemedyBeneficiaryModel`, `RemedyActionModel`, `RemedyAuditLogModel` |
| **Migration** | `088_remedy_cases.py` |
| **Frontend Liste** | `/remedy-cases` → `frontend/src/app/(app)/remedy-cases/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | `test_remediation.py` (referenziert) |

**API-Endpunkte:**
- `POST /remedy-cases/` — erstellen
- `GET /remedy-cases/` — Liste
- `PATCH /remedy-cases/{id}/close` ⚠️ NUR Analyst — **KI-Agenten verboten**
- `POST /remedy-cases/{id}/beneficiaries` — Begünstigte anlegen
- `POST /remedy-cases/{id}/actions` — Massnahmen anlegen
- `GET /remedy-cases/{id}/audit-log`
- `GET /reports/remedy-summary` — Jahresbericht

**Berechtigungen:** `analyst` (close/manage), alle authentifizierten User (read)  
**Upstream:** Grievance (`source_grievance_id`, optional), Organization  
**Downstream:** RemedyBeneficiary, RemedyAction, RemedyAuditLog, ESAP-Export  
**Workflow:** WF-02 Step 2–5

**Gaps:**
- Kein Frontend-Detail-Page
- Kein UI für Beneficiary/Action-Management

---

### F-17 · Stakeholder Engagement (CSDDD Art. 13)

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/stakeholder.py` |
| **API Router** | `backend/interfaces/api/routers/stakeholders.py` |
| **DB Models** | `backend/infrastructure/persistence/models/stakeholder.py` — `StakeholderModel`, `StakeholderConsultationModel`, `StakeholderFeedbackModel` |
| **Migration** | `086_stakeholder_engagement.py` |
| **Frontend Liste** | `/stakeholders` → `frontend/src/app/(app)/stakeholders/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | Referenziert in mehreren Test-Dateien |

**API-Endpunkte:**
- `GET/POST /stakeholders/`
- `GET/PATCH/DELETE /stakeholders/{id}`
- `GET /stakeholders/map-data` — Geodaten
- `GET /stakeholders/report/engagement`
- `GET/POST /stakeholders/consultations/`
- `GET /stakeholders/consultations/{id}/feedback` (analyst)
- `POST /stakeholders/consultations/{id}/feedback` ⚠️ ÖFFENTLICH

**Sicherheit:** `submitted_by_email`, `submitted_by_name`, `submitter_ip` — **NIEMALS in API-Response**  
**Berechtigungen:** Öffentlich (Feedback), `analyst` (manage)  
**Upstream:** Organization, Activity Chain (optional), Risk/Finding/CAP (Consultation-Links)  
**Downstream:** Engagement-Bericht, ESAP-Export  
**Workflow:** WF-04 Step 1–3

**Gaps:**
- Kein Detail-Page für Stakeholder oder Consultation
- Feedback-Review nur via API, kein UI für Analysten

---

### F-18 · Effectiveness Review (CSDDD Art. 15)

| Artefakt | Pfad |
|---------|------|
| **Backend Repository** | `backend/infrastructure/persistence/repositories/effectiveness.py` |
| **API Router** | `backend/interfaces/api/routers/effectiveness.py` |
| **DB Models** | `backend/infrastructure/persistence/models/effectiveness.py` — `EffectivenessIndicatorModel`, `EffectivenessReviewModel`, `ReviewLineModel` |
| **Migration** | `089_effectiveness_monitoring.py` |
| **Frontend Liste** | `/effectiveness` → `frontend/src/app/(app)/effectiveness/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | `test_kpi_calculator.py` (referenziert) |

**API-Endpunkte:**
- `GET/POST /effectiveness/indicators/`
- `POST/GET /effectiveness/reviews/`
- `POST /effectiveness/reviews/{id}/lines` — Messwert upsert
- `POST /effectiveness/reviews/{id}/submit`
- `POST /effectiveness/reviews/{id}/close` ⚠️ NUR Analyst — **KI-Agenten verboten**
- `GET /effectiveness/cap/{cap_id}/snapshot`
- `POST /effectiveness/cap/{cap_id}/baseline`
- `POST /effectiveness/cap/{cap_id}/closed-score` ⚠️ NUR Analyst
- `GET /effectiveness/dashboard` — 6-Metrik-Monitor

**Review-Status:** `draft → submitted → approved → closed`  
**Berechtigungen:** `analyst` (submit/close), alle User (read)  
**Upstream:** CorrectiveActionPlan (CAP), EffectivenessIndicator-Bibliothek  
**Downstream:** Dashboard-Metriken, Jahresbericht, ESAP-Export  
**Workflow:** WF-05 Step 2–4

**Gaps:**
- Kein Detail-Page für Reviews
- CAP-Snapshot-UI fehlt

---

### F-19 · Supplier Score

| Artefakt | Pfad |
|---------|------|
| **Backend Service** | `backend/application/scoring/supplier_scorer.py` — `calculate_risk_score()`, `calculate_esg_scores()`, `calculate_trend()` |
| **Backend Repository** | `backend/infrastructure/persistence/repositories/supplier_score.py` |
| **API Router** | Integriert in `/suppliers/` und `/dashboard` |
| **DB Model** | `backend/infrastructure/persistence/models/supplier_score.py` |
| **Migration** | `020_add_supplier_scores.py` |
| **Frontend** | `/suppliers/[id]` → Analytics-Tab ✅, Supplier-Liste-Spalte ✅ |
| **Tests** | `tests/unit/application/test_supplier_scorer.py` ✅ |

**Score-Dimensionen:** ESG-Score (0–100), Environmental/Social/Governance, Risk-Score (0–100), Risk-Band, Trend, Sektor-Percentile  
**Berechtigungen:** alle authentifizierten User (read), immutable (kein Update)  
**Upstream:** Assessment (Finding-Anzahl), Risk, CAP-Status, Zertifikate  
**Downstream:** PrioritizationDecision, SupplierDigitalTwin, Executive-Dashboard  
**Workflow:** WF-01 parallel (kontinuierlich)

**Gaps:**
- Kein Recalculation-Trigger im UI
- Score-History-Vergleich nicht sichtbar (Daten vorhanden)

---

### F-20 · Supplier Digital Twin

| Artefakt | Pfad |
|---------|------|
| **Backend Services** | `backend/application/intelligence_engine/twin_service.py`, `pipeline_service.py`, `collector_orchestrator.py`, `health_engine.py`, `supplier_matcher.py` |
| **API Router** | `backend/interfaces/api/routers/supplier_twin.py` |
| **DB Models** | `backend/infrastructure/persistence/models/supplier_digital_twin.py` — `SupplierDigitalTwinModel`, `IntelligenceTimelineEventModel` |
| **Migration** | `064_supplier_digital_twin.py`, `065_supplier_twin_extensions.py` |
| **Frontend** | `/suppliers/[id]` → "Twin"-Tab ✅ |
| **Tests** | Intelligence-Engine-Unit-Tests |

**API-Endpunkte:**
- `GET /suppliers/{id}/twin` — 8 Health-Dimensionen
- `GET /suppliers/{id}/twin/timeline` — Intelligence-Timeline
- `POST /suppliers/{id}/twin/process` — Signal-Pipeline triggern
- `GET /intelligence/feed` — org-weiter Feed

**Health-Dimensionen (0–100):** `esg`, `compliance`, `financial`, `geopolitical`, `cyber`, `human_rights`, `environmental`, `operational`  
**Datenquellen (live):** EU Sanctions (EEAS), OFAC SDN, UN Security Council, World Bank Governance, GDELT News  
**Upstream:** Externe Signale, Assessment, Risk, Zertifikate  
**Downstream:** Health-Dashboard, Risk-Alerts, Recommendation (auto-create)  
**Workflow:** WF-01 parallel (Monitoring)

**Gaps:**
- State-Transition-Log (Twin-Zustandsänderungen) fehlt
- Source-Credibility-Scoring nicht im UI exponiert

---

### F-21 · Prioritization Decision (CSDDD Art. 8/10)

| Artefakt | Pfad |
|---------|------|
| **Backend Service** | `backend/application/due_diligence/prioritization_engine.py` — `compute_prioritization()` |
| **Backend Repository** | `backend/infrastructure/persistence/repositories/prioritization.py` |
| **API Router** | `backend/interfaces/api/routers/prioritization.py` |
| **DB Model** | `backend/infrastructure/persistence/models/prioritization.py` |
| **Migration** | `078_prioritization_decisions.py` |
| **Frontend** | ❌ FEHLT — kein dediziertes UI |
| **Tests** | Referenziert in Integration-Tests |

**API-Endpunkte:**
- `POST /prioritization/compute` — Org-Ranking neu berechnen
- `GET /prioritization/` — aktuelles Ranking
- `PATCH /prioritization/{id}/override` ⚠️ NUR Analyst (mit Pflicht-Kommentar)

**Gewichtung:** Severity 40% + Probability 35% + Betroffene Personen 25%  
**Berechtigungen:** `analyst` (compute/override), alle User (read)  
**Upstream:** SupplierScore, Finding-Severity, Kapazitätsplanung  
**Downstream:** Scoping Study, CSDDD-Art.-10-Audit-Trail  
**Workflow:** WF-01 Step 0 (vor Assessment)

**Gaps:**
- **Kein Frontend überhaupt** — kritische Lücke für CSDDD-Art.-10-Nachweis
- Manual-Override-UI fehlt

---

### F-22 · Scoping Study (CSDDD Art. 8 Abs. 3)

| Artefakt | Pfad |
|---------|------|
| **Backend Router** | `backend/interfaces/api/routers/scoping.py` |
| **DB Models** | `ScopingConfigModel`, `ScopingStudyModel`, `ScopingConfigAuditLogModel` |
| **Migration** | `090_scoping_study.py` |
| **Frontend** | `/scoping` → `frontend/src/app/(app)/scoping/page.tsx` ✅ |
| **Frontend Detail** | ❌ FEHLT |
| **Tests** | Referenziert |

**API-Endpunkte:**
- `GET/POST /scoping/config/`
- `POST /scoping/analyze`
- `POST/GET /scoping/studies/`
- `POST /scoping/studies/{id}/submit`
- `POST /scoping/studies/{id}/approve` ⚠️ NUR Analyst — **KI-Agenten verboten**
- `POST /scoping/studies/{id}/clone`

**Upstream:** Supplier, PrioritizationDecision, Sector-Daten  
**Downstream:** Assessment-Auslösung, CSDDD-Compliance-Nachweis  
**Workflow:** WF-01 Step 0–1

**Gaps:**
- Kein Frontend-Detail-Page
- Approval nur via API, kein UI

---

## Gap-Register (Priorisiert)

| Prio | Feature | Gap | Typ |
|------|---------|-----|-----|
| ✅ | F-06 CAP | Keine Tests → 11 Tests geschrieben (2026-07-07) | Geschlossen |
| ✅ | F-06 CAP | Kein Detail-Page → `/corrective-action-plans/[id]` gebaut (2026-07-07) | Geschlossen |
| ✅ | F-05 Recommendation | Kein Detail-Page → `/recommendations/[id]` gebaut (2026-07-07) | Geschlossen |
| ✅ | F-21 Prioritization | Kein Frontend → `/compliance/prioritization` bereits vorhanden | Geschlossen |
| 🟠 | F-10 Board Signoff | Keine Tests | Fehlende Tests |
| 🟠 | F-11 Due Diligence Report | Keine Tests | Fehlende Tests |
| 🟠 | F-12 Disclosure | Keine Tests | Fehlende Tests |
| 🟠 | F-13 ESAP Export | Keine Tests | Fehlende Tests |
| 🟠 | F-16 Remedy Case | Kein Frontend-Detail-Page | Fehlendes Frontend |
| 🟠 | F-08 Compliance Gap | Kein Auto-Recalculate | Fehlende Automatisierung |
| 🟡 | F-04 Risk | `assessment_id` optional → Pipeline-Lücke | Datenmodell |
| 🟡 | F-07 Evidence | Kein Frontend-Detail-Page | Fehlendes Frontend |
| 🟡 | F-17 Stakeholder | Kein Detail-Page | Fehlendes Frontend |
| 🟡 | F-18 Effectiveness | Kein Detail-Page | Fehlendes Frontend |
| 🟡 | F-19 Supplier Score | Kein Recalculation-Trigger im UI | Fehlende Aktion |
| 🟡 | F-01–F-06 | Keine dedizierten Application-Services | Architektur |

---

## Workflow-Pipeline-Visualisierung

```
WF-01 · Lieferketten-Sorgfaltspflicht
─────────────────────────────────────────────────────────────────
[F-22 Scoping] → [F-21 Prio] → [F-01 Supplier] → [F-02 Assessment]
                                                         │
                    ┌────────────────────────────────────┤
                    │                                    │
              [F-07 Evidence]                    [F-03 Finding]
              (parallel)                                 │
                                          ┌──────────────┤
                                          │              │
                                    [F-04 Risk]   [F-06 CAP]
                                          │              │
                                    [F-05 Rec]    [F-18 Effect.]
                                          │
                                    [F-10 Board]
                                          │
                                    [F-14 Report]

WF-02 · Grievance & Remedy
───────────────────────────────────────────
[F-15 Grievance] → [F-16 Remedy Case]
      │                    │
   [Finding]         [Beneficiary]
                           │
                      [F-13 ESAP]

WF-03 · Compliance & Disclosure
──────────────────────────────────────────────────────
[F-09 Req.Mapping] → [F-08 Gap] → [F-12 Disclosure]
                                          │
                                   [F-14 Report]
                                          │
                                   [F-11 DD Report]
                                          │
                                   [F-13 ESAP Export]

WF-04 · Stakeholder Engagement
────────────────────────────────────────────────────
[F-17 Stakeholder] → [Consultation] → [Feedback]
                                          │
                                    [Risk-Update]

WF-05 · Effectiveness Monitoring
──────────────────────────────────────────────────
[F-06 CAP] → [F-18 Effectiveness Review] → [Dashboard]
                                                │
                                          [ESAP Export]
```

---

## Sicherheitsregeln (konsolidiert)

| Endpunkt | Regel |
|---------|-------|
| `/board-signoff/{id}/approve\|reject` | KI-Agenten absolut verboten (Art. 22 CSDDD) |
| `/corrective-action-plans/{id}/verify\|close` | KI-Agenten verboten |
| `/effectiveness/reviews/{id}/close` | KI-Agenten verboten |
| `/scoping/studies/{id}/approve` | KI-Agenten verboten |
| `/remedy-cases/{id}/close` | KI-Agenten verboten |
| `submitted_by_email`, `submitted_by_name`, `submitter_ip` | NIEMALS in API-Response (Grievance, Stakeholder) |
| `password_hash` | NIEMALS in User/SupplierUser API-Response |
| Alle DB-Queries | `organization_id`-Filter PFLICHT |
