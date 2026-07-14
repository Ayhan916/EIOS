# ROADMAP.md — Langfristige Produkt-Roadmap
**Status: APPROVED — Version 1.0 (2026-07-09)**
**Authority: Lead AI Architect + Product Owner**
**Review: Quartalsweise**

---

## Vision

EIOS wird zur führenden **Enterprise AI Risk Intelligence Platform** für regulatorische Due Diligence in Europa — auditierbar, erklärbar, skalierbar.

---

## Phase 1 — Intelligence Foundation
**Zeitraum: Q3 2026**
**Status: ✅ ABGESCHLOSSEN (2026-07-09)**
**Ziel: Solide, auditierbare Datenbasis und Kern-Risikoanalyse**

### Meilensteine

| Meilenstein | Feature | Ref | Status |
|-------------|---------|-----|--------|
| M1.1 | Metric Extraction → Claude Haiku | E1-F1 | ✅ DONE |
| M1.2 | Deterministischer RiskScoreCalculator | E2-F1 | ✅ DONE |
| M1.3 | Evidence Linking Invariante | E3-F1 | ✅ DONE |
| M1.4 | Prompt Versioning | E3-F3 | ✅ DONE |
| M1.5 | Hybrid Search (BM25 + pgvector) | E1-F2 | ✅ DONE |
| M1.6 | CSDDD Obligation Rule Engine | E2-F2 | ✅ DONE |
| M1.7 | Parent-Child Chunking | E1-F3 | ✅ DONE |
| M1.8 | Immutable Audit Log (Hash-Chain) | E3-F2 | ✅ DONE |
| M1.9 | Entity Linker | E2-F3 | ✅ DONE |
| M1.10 | ConfidenceCard Standardisierung | E4-F1 | ✅ DONE |
| M1.11 | Assessment Immutability Gate | E4-F2 | ✅ DONE |

### Bonus-Meilensteine (Phase 2 Preview — früher implementiert)

| Meilenstein | Feature | Ref | Status |
|-------------|---------|-----|--------|
| M1.12 | Risk Score Explainability Service | E5-F1 | ✅ DONE |
| M1.13 | AuditPackage Generator | E5-F2 | ✅ DONE |
| M1.14 | Supply Chain Graph (BFS Tier-2/3) | E5-F3 | ✅ DONE |

### Phase 1 Definition of Done
- ✅ RiskScore ist deterministisch, versioniert, auditierbar
- ✅ CSDDD-Obligations sind 100% gedeckt (alle 29 Artikel)
- ✅ Hybrid Search verbessert Copilot-Antwortqualität messbar
- ✅ Audit Log ist manipulationsresistent (Hash-Chain)
- ✅ Kein Finding ohne Evidence möglich
- ✅ 3862/3862 Unit-Tests grün (Migration 115)

---

## Phase 2 — Due Diligence Workflow Engine
**Zeitraum: Q4 2026**
**Ziel: Strukturierte, begleitete und dokumentierte Due-Diligence-Prozesse**

### Kernfunktionen

**2.1 Assessment Workflow Engine**
- Strukturierter Assessment-Prozess (Scope → Collection → Analysis → Review → Approval)
- Reviewer-Assignment + Notification
- Deadline-Tracking + Overdue-Alerts
- Human Review Gate als technischer Blocker (nicht nur UI-Hinweis)

**2.2 Supplier Self-Assessment Portal**
- Lieferanten können Fragebogen online ausfüllen
- Antworten werden automatisch in Evidence überführt
- Fortschritts-Tracking für Compliance-Manager

**2.3 Mitigation & Remedy Tracking**
- MitigationPlan mit Milestones + automatischen Status-Updates
- Remedy-Modul für CSDDD Art. 11 (Wiedergutmachung)
- Stakeholder Engagement Logging

**2.4 Risk Score Explainability**
- Factor Breakdown in UI (Balkendiagramm: "Warum ist dieser Lieferant HIGH Risk?")
- CSDDD Rule Trace ("Welcher Artikel trifft auf diesen Befund zu?")
- Evidence Chain Visualization

**2.5 AuditPackage Generator**
- Vollständiger Export für externe Prüfung
- Methodik-Dokumentation (Formula Version, Prompt Versions, Model Versions)
- SHA-256 Integritätsnachweis

### Phase 2 Definition of Done
- ✅ Due Diligence Assessment vollständig digital durchführbar
- ✅ Supplier kann Fragebogen selbst ausfüllen (ohne Email-Ping-Pong)
- ✅ AuditPackage kann Wirtschaftsprüfer ohne System-Zugang übergeben werden
- ✅ Jeder Risk Score ist in der UI vollständig erklärbar

---

## Phase 3 — Network Intelligence
**Zeitraum: Q1–Q2 2027**
**Ziel: Risikointelligenz über die gesamte Lieferkette (Tier-2/3)**

### Kernfunktionen

**3.1 Supply Chain Graph**
- Tier-2/3 Lieferantenbeziehungen visualisieren
- `supply_chain_edges`-Tabelle mit Graph-Traversal
- "Entdecke Tier-2-Lieferanten"-Workflow

**3.2 Cross-Supplier Risk Correlation**
- Gleicher Rohstoff bei mehreren Lieferanten aus Hochrisikoland → Portfolio-Risk
- Risikokonzentration erkennen (geografisch, nach Commodity, nach Sector)
- Shared-Risk Alerts

**3.3 Sector Benchmark Engine**
- Branchenvergleiche für Risk Scores (Automotive Tier-1 Benchmark)
- Perzentil-Einordnung: "Ihr Lieferant X ist im schlechtesten 20%-Sektor"
- NACE-Code-basierte Sektorklassifikation

**3.4 Real-time Signal Monitoring**
- News-Feed-Integration (RSS, Webhooks)
- Alert-Rules: IF Signal_Type=HumanRightsAllegation AND Severity>=HIGH → Alert
- Watchlist-Management

**3.5 Predictive Risk Indicators**
- Temporal Trend Analyse (Risk Score verbessert/verschlechtert sich?)
- Early Warning System für Supply Chain Disruptions
- Seasonal Risk Patterns

### Phase 3 Definition of Done
- ✅ Tier-2-Lieferanten für TOP-100-Lieferanten bekannt
- ✅ Portfolio-Risk-Dashboard (Gesamt-Exposure)
- ✅ Real-time Alerts für kritische Signale (< 1h Latenz)
- ✅ Benchmark-Daten für 5 Hauptsektoren verfügbar

---

## Phase 4 — Regulatory Disclosure Automation
**Zeitraum: Q3–Q4 2027**
**Ziel: Automatisierte regulatorische Berichte und Behördeneinreichungen**

### Kernfunktionen

**4.1 CSRD-konforme Berichterstattung**
- GRI-Standard-Mapping für alle erhobenen Metriken
- ESRS-Datenpunkte automatisch befüllen
- Gap-Analyse: "Was fehlt noch für CSRD-Konformität?"

**4.2 Multi-Framework Mapping**
- CSDDD ↔ LkSG ↔ CSRD ↔ UNGP Cross-Reference
- "Welche Anforderung erfüllt mehrere Frameworks gleichzeitig?"
- Framework-übergreifendes Compliance-Dashboard

**4.3 Regulatory Filing Support**
- Export in Behörden-kompatible Formate (XBRL, XML, PDF)
- Versionierte Einreichungs-Historie
- Änderungstracking für erneute Einreichungen

**4.4 Board Reporting**
- Automatisierter Monthly ESG Risk Report für Boards
- KPI-Tracking: CSDDD-Compliance-Score Ø über alle Lieferanten
- Trend-Visualisierung (Risiko Portfolio über Zeit)

### Phase 4 Definition of Done
- ✅ CSRD-konforme Datenpunkte automatisch aus vorhandenen Metriken befüllbar
- ✅ Jede Regulierung mit vollständigem Artikel-Katalog und Obligations hinterlegt
- ✅ Board Report kann in < 30 Minuten generiert werden
- ✅ XBRL-Export validiert gegen offizielle Schema-Definition

---

## Technologie-Evolutionsplan

| Zeitpunkt | Technologie | Entscheidung |
|-----------|------------|-------------|
| Phase 1 | PostgreSQL + pgvector | Beibehalten |
| Phase 1 | Claude Haiku für Extraktion | ✅ Migrieren (ADR-007) |
| Phase 2 | Task Queue (Celery/ARQ) | Evaluieren für Async-Verarbeitung |
| Phase 2 | Redis für Caching | Evaluieren für Query-Cache |
| Phase 3 | GraphDB (Neo4j/AWS Neptune) | Evaluieren für Supply Chain Graph |
| Phase 3 | Kafka für Event Streaming | Evaluieren für Real-time Monitoring |
| Phase 4 | Multi-Tenant Architektur | ADR erforderlich vor Implementierung |

---

## Nicht-funktionale Ziele

| Metrik | Phase 1 | Phase 2 | Phase 4 |
|--------|---------|---------|---------|
| Copilot Latenz (p95) | < 5s | < 3s | < 2s |
| Extraction Precision | > 70% | > 85% | > 90% |
| Retrieval Precision@10 | > 60% | > 75% | > 85% |
| System Uptime | 99.0% | 99.5% | 99.9% |
| Audit Log Retention | 7 Jahre | 7 Jahre | 7 Jahre |
| Concurrent Users | 50 | 500 | 5.000 |

---

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|-----------|
| Anthropic API Kosten zu hoch | Mittel | Hoch | ModelRouter: Haiku für alles außer Copilot |
| Groq Free Tier Limit | Hoch | Mittel | Phase 1: Migration auf Haiku |
| CSDDD-Artikel-Interpretation unklar | Mittel | Hoch | Legal Review der Obligation-Tabelle |
| Datenqualität Lieferanten-Dokumente | Hoch | Mittel | Parent-Child Chunking, Qualitätsscore |
| Supply Chain Graph zu dünn | Mittel | Mittel | Discovery-Pipeline + Externe Datenquellen |

---

*Diese Roadmap wird quartalsweise gegen neue regulatorische Anforderungen und Produktprioritäten überprüft.*
