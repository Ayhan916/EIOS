# ENTERPRISE DEPENDENCY MATRIX

ID: GDM-0001

Version: 1.0

Status: ACTIVE

Owner: Founder

---

# Purpose

This document defines the canonical dependency relationships between all major enterprise artifacts of EIOS.

It enables impact analysis, implementation planning and AI reasoning.

---

# Principles

Dependencies shall be:

* explicit
* directional
* version-aware
* auditable
* machine-readable

---

# Dependency Types

* Governs
* Depends On
* References
* Extends
* Implements
* Validates

---

# Enterprise Dependency Matrix

| Artifact                 | Depends On           | Purpose                     |
| ------------------------ | -------------------- | --------------------------- |
| Founder Constitution     | None                 | Highest authority           |
| Enterprise Blueprint     | Founder Constitution | Defines architecture        |
| Governance Standards     | Founder Constitution | Governs repository          |
| Taxonomies               | Enterprise Blueprint | Defines enterprise concepts |
| Schemas                  | Taxonomies           | Defines enterprise data     |
| Agent Specifications     | Schemas              | Defines AI capabilities     |
| Implementation Standards | Schemas, Agents      | Defines build process       |
| Master Build Prompt      | All above            | Defines implementation      |
| Source Code              | Master Build Prompt  | Implements EIOS             |

---

# Impact Analysis Rule

Every artifact modification shall identify:

* Directly affected artifacts

* Indirectly affected artifacts

* AI impact

* API impact

* Database impact

* Governance impact

---

# Circular Dependency Rule

Circular dependencies are prohibited unless explicitly documented and approved.

---

# AI Rule

AI systems shall resolve dependencies before generating implementation artifacts.

---

# Repository Rule

No enterprise artifact shall exist without an identifiable dependency path.

---

# Golden Rule

Architecture is a dependency graph, not a collection of files.
