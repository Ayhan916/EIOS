# PROJECT_VISION.md
**Status: APPROVED — Version 1.0 (2026-07-09)**
**Authority: Lead AI Architect**
**Change Control: New ADR required for any modification**

---

## Was ist EIOS?

EIOS ist eine **Enterprise AI Risk Intelligence Platform** für regulatorische Risikoanalyse und Supply-Chain Due Diligence.

Die Plattform hilft Unternehmen dabei, ihre gesetzlichen Sorgfaltspflichten nach CSDDD, LkSG, CSRD und verwandten Regelwerken systematisch, nachvollziehbar und auditierbar zu erfüllen.

---

## Warum existiert die Plattform?

### Das Problem

Unternehmen mit komplexen globalen Lieferketten stehen vor drei unlösbaren Widersprüchen:

**Widerspruch 1 — Daten vs. Pflichten**
Sorgfaltspflichten verlangen Wissen über Tier-2- und Tier-3-Lieferanten. Dieses Wissen liegt verteilt in tausenden Dokumenten, News-Feeds, NGO-Berichten und internen Audits — unstrukturiert, mehrsprachig, widersprüchlich.

**Widerspruch 2 — Geschwindigkeit vs. Nachvollziehbarkeit**
Compliance-Teams müssen schnell reagieren. Regulatoren verlangen lückenlose Dokumentation jeder Entscheidung. Manuelle Prozesse schaffen beides nicht gleichzeitig.

**Widerspruch 3 — Breite vs. Tiefe**
Eine globale Lieferkette hat Tausende Lieferanten. Tiefe Due-Diligence-Analysen sind nur für einige wenige möglich. CSDDD verlangt aber Risikopriorisierung über die gesamte Kette.

### Die Lösung

EIOS löst diese Widersprüche durch:

1. **Automatische Wissensextraktion** — strukturierte Metriken, Signale und Fakten aus unstrukturierten Dokumenten
2. **Deterministisches Risiko-Scoring** — nachvollziehbare, versionierte Formel statt LLM-Schätzung
3. **Evidenz-basierte Analyse** — jede Aussage verknüpft mit Quelle, Seite, Datum, Zuverlässigkeit
4. **Regulierungs-Rule-Engine** — CSDDD-Obligations deterministisch gemappt, kein LLM für Rechtsfragen
5. **Vollständiger Audit Trail** — jede Entscheidung reproduzierbar, manipulationsresistent, exportierbar

---

## Zielgruppe

| Rolle | Primäre Nutzung |
|-------|----------------|
| Chief Sustainability Officer | Executive Dashboard, Portfolio-Risikoübersicht |
| Compliance Manager | Due Diligence Assessments, CSDDD-Gap-Analyse |
| Supply Chain Manager | Lieferanten-Risikoprofil, Tier-2/3-Transparenz |
| Legal Counsel | Audit Package, regulatorische Nachweise |
| Wirtschaftsprüfer (extern) | AuditPackage-Export, Methodik-Dokumentation |
| Regulator | Disclosure Reports, Remediation-Nachweise |

---

## Was die Plattform tut

- Dokumente (Annual Reports, ESG Reports, NGO-Berichte) analysieren und strukturiert indexieren
- Qualitative Signale und quantitative Metriken extrahieren
- Lieferanten-Risikoprofile aufbauen und automatisch aktualisieren
- CSDDD-Compliance-Gaps deterministisch identifizieren
- Due Diligence Assessments strukturieren, begleiten und dokumentieren
- Risks mit Lifecycle, Score und Evidenz verwalten
- Mitigation Plans und Remedies tracken
- Vollständige Audit Packages für Prüfungen generieren
- KI-gestützte Analyse (Copilot) für Compliance-Fragen bereitstellen

---

## Was die Plattform ausdrücklich NICHT tut

| Nicht-Ziel | Begründung |
|-----------|-----------|
| ❌ Compliance-Entscheidungen autonom treffen | Nur Menschen dürfen Risiken akzeptieren, Findings genehmigen, Gaps schließen (ADR-005) |
| ❌ Rechtliche Beratung ersetzen | Die Plattform identifiziert Obligations, interpretiert aber keine Einzelfälle |
| ❌ Echtzeitüberwachung aller Medien | Monitoring ist sampling-basiert, kein vollständiges Medien-Coverage |
| ❌ Garantierte Vollständigkeit | Datenqualität hängt von verfügbaren Dokumenten ab — ConfidenceCard zeigt Lücken |
| ❌ Branchenagnostisches ESG-Tool | Fokus auf regulatorische Risikoanalyse, nicht allgemeine ESG-Berichterstattung |
| ❌ ERP-/CRM-Ersatz | Integration mit bestehenden Systemen, kein Ersatz |
| ❌ KI als Source of Truth | LLMs sind Synthesizer — Daten, Formeln und Regeln sind Source of Truth (ADR-001) |

---

## Qualitätsprinzipien

**Enterprise Quality over Feature Velocity**
Jede Funktion muss fachlich korrekt, technisch sauber, regulatorisch belastbar, nachvollziehbar, skalierbar, wartbar und testbar sein.

**Evidence First**
Kein Finding, kein Risk, kein Compliance-Gap ohne nachvollziehbare Quellenreferenz.

**Determinism where it counts**
Risk Scores, CSDDD-Obligation-Mapping und Compliance-Entscheidungen sind deterministisch und reproduzierbar.

**Human-in-the-Loop**
Kritische Entscheidungen (Assessment-Genehmigung, Risk-Eskalation, Gap-Schließung) erfordern menschliche Freigabe.

---

## Strategische Positionierung (3–5 Jahre)

Phase 1: Intelligence Platform (aktuell)
— Dokumentenanalyse, Risiko-Scoring, Copilot, CSDDD-Grundfunktionen

Phase 2: Due Diligence Workflow Engine
— Strukturierte Assessments, Supplier Self-Assessment Portal, Remediation Tracking

Phase 3: Network Intelligence
— Tier-2/3-Lieferkettengraph, Cross-Supplier-Risikokorrelation, Sektor-Benchmarks

Phase 4: Regulatory Disclosure Automation
— CSRD-konforme Berichte, automatisierte Behördeneinreichungen, Multi-Framework-Mapping

---

*Dieses Dokument ist Teil der Architecture Memory. Änderungen erfordern eine neue ADR und Freigabe.*
