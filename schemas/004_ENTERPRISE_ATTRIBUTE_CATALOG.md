# ENTERPRISE ATTRIBUTE CATALOG

ID: DBA-0001

Version: 1.0

Status: DRAFT

Owner: Founder

---

# Purpose

This document defines the canonical attributes for all enterprise entities in EIOS.

Every implementation shall derive its fields from this catalog.

---

# Dependencies

- DBE-0001

- DBR-0001

- DBS-0001

- AATTR-0001

---

# Related Documents

- AAPI-0001

- AAI-0001

- AMEM-0001

---

# Attribute Principles

Every attribute shall define:

- Attribute ID

- Name

- Data Type

- Required

- Default Value

- Validation Rule

- Description

---

# Common System Attributes

Every entity shall contain:

- id

- uuid

- version

- status

- created_at

- updated_at

- created_by

- updated_by

---

# Business Attributes

May include:

- name

- title

- description

- category

- subtype

- priority

- severity

- score

- confidence

---

# Governance Attributes

May include:

- approval_status

- approved_by

- approval_date

- review_status

---

# Explainability Attributes

AI-generated objects shall include:

- reasoning

- evidence_reference

- confidence_score

- explanation

---

# Traceability Attributes

May include:

- source_id

- assessment_id

- workflow_id

- event_id

- trace_id

---

# Data Types

Supported types:

- UUID

- String

- Text

- Integer

- Float

- Boolean

- Date

- DateTime

- JSON

- Array

- Reference

---

# Validation Rules

Attributes may be:

- required

- optional

- unique

- immutable

- calculated

---

# Naming Rules

Attribute names shall:

- use snake_case

- be descriptive

- avoid abbreviations where possible

Example:

created_at

Correct

createdAt

Incorrect

crt_dt

Incorrect

---

# AI Rule

AI systems shall infer entity structure from this catalog before generating schemas or code.

---

# Golden Rule

Attributes define enterprise meaning.

Implementations define technical realization.