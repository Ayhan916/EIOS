# REPOSITORY AUTHORITY

Version: 1.0

Status: AUTHORITATIVE

Owner: Founder

---

# Purpose

This document defines the authority hierarchy of the EIOS repository.

Whenever multiple documents appear to conflict, this hierarchy shall determine which source has precedence.

---

# Authority Hierarchy

Level 0

Founder Decisions

Highest authority.

---

Level 1

Founder Constitution

This document (REPOSITORY_AUTHORITY.md) and founding governance standards.

---

Level 2

Enterprise Blueprint Summary

Defines the overall enterprise structure and canonical object model.

---

Level 3

Governance Standards

Defines enterprise rules, standards and processes.

Governance overrides all lower levels.

---

Level 4

Architecture Models

Defines enterprise structure, models and patterns.

Architecture overrides implementation.

---

Level 5

Product Specifications

Defines product requirements, features and agent specifications.

---

Level 6

Implementation Standards

Defines executable realization, schemas and taxonomies.

Implementation shall conform to all higher levels.

---

Level 7

Sprint Backlogs

Define prioritized execution strategy and build plans.

They shall not contradict higher levels.

---

Level 8

Tasks

Represent temporary work items.

Tasks never override architecture or governance.

---

Level 9

Generated Artifacts

Outputs produced during implementation.

Generated artifacts are informative and shall not redefine authoritative artifacts.

---

# Navigation Entry Point

START_HERE.md is the repository orientation document.

It defines mission, identity and working principles for AI systems entering the repository.

It is NOT an authority level — it does not override any document in this hierarchy.

When START_HERE.md conflicts with a governance or architecture document, the governance or architecture document takes precedence per this hierarchy.

---

# Conflict Resolution

If two artifacts conflict:

1. Select the higher authority.

2. Explain the conflict.

3. Recommend the best enterprise solution.

4. If required, wait for Founder approval.

---

# Single Source of Truth

Never maintain multiple competing definitions.

Whenever possible:

- consolidate

- normalize

- simplify

---

### Canonical Concept Rule

Every enterprise concept shall have exactly one canonical definition.

For every concept there shall be:

* one authoritative artifact,
* one authoritative definition,
* one authoritative owner.

All other artifacts shall reference that definition instead of redefining it.

If multiple definitions exist, the repository shall be refactored until only one canonical definition remains.


# Golden Rule

Authority flows downward.

Implementation never defines architecture.

Architecture never overrides governance.

Governance never overrides Founder decisions.

## Same-Level Conflict Resolution

If two artifacts exist on the same authority level and define the same concept:

1. Prefer the artifact explicitly marked as **AUTHORITATIVE**.

2. If both are AUTHORITATIVE, prefer the artifact whose primary purpose is defining that concept.

3. If ambiguity still exists, do not make assumptions.

4. Report the conflict and request Founder guidance before introducing a new definition.

No AI system shall create an additional competing definition to resolve ambiguity.
