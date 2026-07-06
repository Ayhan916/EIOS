# EIOS — CSDDD Compliance Roadmap
## Basis: Directive (EU) 2024/1760 — Konsolidierte Fassung 18. März 2026

> Vollständigkeitsabgleich: 15 Epics · 52 Stories · 4 Phasen  
> Erstellt auf Basis der Gap-Analyse gegen CSDDD Art. 7–16 + Art. 22 + Anhang I  
> Status-Legende: 🔴 TODO · 🟡 IN PROGRESS · 🟢 DONE

---

## Gesamtstatus

| Artikel | Titel | Aktueller Stand | Ziel | Epic |
|---------|-------|----------------|------|------|
| Art. 7 | Integration in Unternehmenspolitik | 40% | 100% | CSDDD-002 |
| Art. 8 | Identifikation & Bewertung | 85% | 100% | CSDDD-008 |
| Art. 9 | Priorisierung | 100% | — | ✅ Fertig |
| Art. 10 | Prävention + Contractual Assurance | 60% | 100% | CSDDD-006, CSDDD-007, CSDDD-015 |
| Art. 11 | Cessation / CAP | 100% | — | ✅ Fertig |
| Art. 12 | Remedy / Wiedergutmachung | 30% | 100% | CSDDD-004 |
| Art. 13 | Stakeholder Engagement | 20% | 100% | CSDDD-001 |
| Art. 14 | Grievance Mechanism | 100% | — | ✅ Fertig |
| Art. 15 | Monitoring der Wirksamkeit | 50% | 100% | CSDDD-003 |
| Art. 16 | Öffentliche Berichterstattung | 100% | — | ✅ Fertig |
| Art. 22 | Pflichten der Unternehmensleitung | 100% | — | ✅ Fertig |
| Art. 2/3 | Activity Chain Downstream | 0% | 100% | CSDDD-005 |
| Art. 2 | Schwellenwert-Monitor | 100% | — | ✅ Fertig |

---

## Phasen-Übersicht

### Phase 1 — Kritische Compliance-Lücken *(Priorität: HOCH — Auditor-relevant)*
> Ziel: Schließt alle Lücken die bei einer Behördenprüfung sofort auffallen

| Epic | Titel | Stories | Aufwand | Status |
|------|-------|---------|---------|--------|
| [CSDDD-001](epics/CSDDD-001-stakeholder-engagement.md) | Stakeholder Engagement Module | 5 | ~13 SP | 🟢 DONE |
| [CSDDD-002](epics/CSDDD-002-policy-review-governance.md) | Policy Review & DD-Governance | 4 | ~8 SP | 🟢 DONE |
| [CSDDD-003](epics/CSDDD-003-effectiveness-monitoring.md) | Effectiveness Monitoring Workflow | 4 | ~10 SP | 🟢 DONE |
| [CSDDD-004](epics/CSDDD-004-remedy-case-manager.md) | Remedy Case Manager | 4 | ~10 SP | 🟢 DONE |

### Phase 2 — Fehlende Module *(Priorität: MITTEL — strukturelle Vollständigkeit)*
> Ziel: Deckt alle Art. 10 Anforderungen und die Activity Chain vollständig ab

| Epic | Titel | Stories | Aufwand | Status |
|------|-------|---------|---------|--------|
| [CSDDD-005](epics/CSDDD-005-downstream-activity-chain.md) | Downstream Activity Chain | 4 | ~13 SP | 🟢 DONE |
| [CSDDD-006](epics/CSDDD-006-contractual-assurance.md) | Contractual Assurance Module | 4 | ~11 SP | 🟢 DONE |
| [CSDDD-007](epics/CSDDD-007-sme-support-tracker.md) | SME Support Tracker | 3 | ~7 SP | 🟢 DONE |
| [CSDDD-008](epics/CSDDD-008-scoping-study.md) | Scoping Study Workflow | 4 | ~10 SP | 🟢 DONE |

### Phase 3 — Innovation & Differenzierung *(Priorität: MITTEL — Wettbewerbsvorteil)*
> Ziel: Features die EIOS zum Marktführer machen — über Mindestanforderungen hinaus

| Epic | Titel | Stories | Aufwand | Status |
|------|-------|---------|---------|--------|
| [CSDDD-011](epics/CSDDD-011-readiness-score.md) | CSDDD Readiness Score | 3 | ~8 SP | 🟢 DONE |
| [CSDDD-012](epics/CSDDD-012-impact-severity-calculator.md) | Impact Severity Calculator | 3 | ~7 SP | 🟢 DONE |
| [CSDDD-013](epics/CSDDD-013-board-signoff-trail.md) | Board Sign-off Trail | 4 | ~9 SP | 🟢 DONE |
| [CSDDD-015](epics/CSDDD-015-supplier-self-assessment.md) | Supplier Self-Assessment CSDDD | 3 | ~8 SP | 🟢 DONE |

### Phase 4 — Zukunftssicherung *(Priorität: NIEDRIG — langfristig)*
> Ziel: Regulatory Radar, ESAP 2031, Threshold Monitor

| Epic | Titel | Stories | Aufwand | Status |
|------|-------|---------|---------|--------|
| [CSDDD-009](epics/CSDDD-009-esap-export.md) | ESAP Export (ab 2031) | 3 | ~10 SP | 🟢 DONE |
| [CSDDD-010](epics/CSDDD-010-threshold-monitor.md) | Threshold Monitor | 3 | ~6 SP | 🟢 DONE |
| [CSDDD-014](epics/CSDDD-014-regulatory-change-radar.md) | Regulatory Change Radar | 4 | ~11 SP | 🟢 DONE |

---

## Gesamtaufwand

| Phase | Epics | Stories | Story Points |
|-------|-------|---------|-------------|
| Phase 1 | 4 | 17 | ~41 SP |
| Phase 2 | 4 | 15 | ~41 SP |
| Phase 3 | 4 | 13 | ~32 SP |
| Phase 4 | 3 | 10 | ~27 SP |
| **Gesamt** | **15** | **55** | **~141 SP** |

---

## Abarbeitungsreihenfolge (empfohlen)

```
CSDDD-001 → CSDDD-002 → CSDDD-004 → CSDDD-003
     ↓
CSDDD-008 → CSDDD-005 → CSDDD-006 → CSDDD-007
     ↓
CSDDD-011 → CSDDD-012 → CSDDD-013 → CSDDD-015
     ↓
CSDDD-010 → CSDDD-014 → CSDDD-009
```

---

*Letzte Aktualisierung: 2026-07-06*  
*Basis: CSDDD 2024/1760 konsolidiert + Gap-Analyse EIOS v1.0*
