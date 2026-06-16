# ENTERPRISE RELATIONSHIP MODEL

ID: ARM-0001

Version: 1.0

Status: DRAFT

Owner: Founder

---

# Purpose

The Enterprise Relationship Model defines how entities interact.

Relationships are first-class enterprise objects.

Relationships are never implicit.

---

# Relationship Principles

Every relationship shall have:

- Relationship ID
- Source Entity
- Target Entity
- Relationship Type
- Version
- Confidence
- Source Evidence
- Status
- Created At

---

# Relationship Types

## One-to-One

Example:

Company

↓

Risk Profile

---

## One-to-Many

Example:

Company

↓

Assessments

---

## Many-to-Many

Example:

Company

↓

ESG Topics

---

## Hierarchical

Example:

Organization

↓

Department

↓

Team

---

## Temporal

Example:

Risk

↓

Historical Version

↓

Current Version

---

## Evidence Relationship

Evidence

↓

Supports

↓

Knowledge Object

---

## Knowledge Relationship

Knowledge Object

↓

Explains

↓

Assessment

---

## Decision Relationship

Assessment

↓

Generates

↓

Recommendation

---

## Governance Relationship

Recommendation

↓

Approved By

↓

Founder Decision

---

# Cardinality Rules

Every relationship shall define:

- Minimum Cardinality

- Maximum Cardinality

- Required

- Optional

---

# Versioning Rules

Relationships shall never be overwritten.

New versions create new relationship instances.

---

# Explainability

Every relationship must answer:

Why does this relationship exist?

What evidence supports it?

What confidence does it have?

---

# Golden Rule

Relationships create intelligence.

Entities alone create only data.