# IMPLEMENTATION QUEUE

Status: ACTIVE

Owner: Founder

Purpose:

This document defines the actual implementation queue for EIOS.

Tasks are executed from top to bottom unless the Founder approves otherwise.

---

# ACTIVE

## TASK-0001

Repository Cleanup

Status:

TODO

Deliverables:

- Remove duplicate artifacts

- Remove obsolete artifacts

- Normalize naming

- Normalize references

---

## TASK-0002

Repository Master Index

Status:

TODO

Deliverables:

- Index all authoritative artifacts

- Verify ownership

- Verify dependencies

---

## TASK-0003

Gap Analysis

Status:

TODO

Deliverables:

- Missing artifacts

- Duplicate artifacts

- Merge candidates

---

## TASK-0004

Enterprise Core Implementation

Status:

TODO

---

## TASK-0005

Enterprise Memory

Status:

TODO

---

## TASK-0006

Knowledge Graph

Status:

TODO

---

## TASK-0007

Assessment Engine

Status:

TODO

---

## TASK-0008

Risk Engine

Status:

TODO

---

## TASK-0009

Recommendation Engine

Status:

TODO

---

## TASK-0010

Workflow Engine

Status:

TODO

---

## TASK-0011

Agent Framework

Status:

TODO

---

## TASK-0012

API Layer

Status:

TODO

---

## TASK-0013

Frontend

Status:

TODO

---

## TASK-0014

Testing & Validation

Status:

TODO

---

## TASK-0015 ← NÄCHSTE PRIORITÄT

CSDDD Sector Risk Register (RAG + Szenario-Simulation)

Status: APPROVED — bereit zur Implementierung

Genehmigt: 2026-07-01

Detail: tasks/CLAUDE_TASK_003_CSDDD_SECTOR_RISK_REGISTER.md

Phasen:
- Phase 1: Domain Foundation (2 Tage)
- Phase 2: Statische Basis-Matrix 20 Sektoren × 21 CSDDD-Rechte (3 Tage)
- Phase 3: RAG Kalibrierungspipeline via Groq (3 Tage)
- Phase 4: News → Szenario-Trigger (2 Tage)
- Phase 5: Simulation Engine deterministisch (2 Tage)
- Phase 6: API + Catena-X Output (2 Tage)
- Phase 7: Tests (2 Tage)

---

# Rule

Only one ACTIVE implementation task shall exist at a time.

A task must be completed before the next implementation task begins unless the Founder explicitly decides otherwise.

---

# Wie Claude dieses File nutzt

Zu Beginn jeder Session: IMPLEMENTATION_QUEUE.md lesen → aktive Task-Datei öffnen → Status-Checkboxen prüfen → dort weitermachen wo aufgehört wurde.

Nach jeder abgeschlossenen Phase: Checkbox in CLAUDE_TASK_003... auf [x] setzen + Protokoll-Zeile ergänzen.