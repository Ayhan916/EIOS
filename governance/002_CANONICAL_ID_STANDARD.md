# CANONICAL ID STANDARD

ID: GIS-0001

Version: 1.0

Status: APPROVED

Owner: Founder

---

# Purpose

This document defines the official identifier system of EIOS.

Every enterprise object shall have one unique identifier.

Identifiers shall never be reused.

---

# Principles

Identifiers shall be:

- unique

- stable

- immutable

- human-readable

- machine-readable

---

# Format

PREFIX-NNNN

Example:

FDR-0001

ADR-0007

AENT-0003

---

# Reserved Prefixes

FDR

Founder Decision Record

---

ADR

Architecture Decision Record

---

REQ

Requirement

---

PRD

Product Requirement

---

AARC

Enterprise Architecture

---

ADATA

Enterprise Data Architecture

---

ADOM

Enterprise Domain Model

---

AENT

Enterprise Entity Model

---

AREL

Enterprise Relationship Model

---

AATTR

Enterprise Attribute Model

---

ACON

Enterprise Constraint Model

---

AONTO

Enterprise Ontology Model

---

AEVT

Enterprise Event Model

---

ASTATE

Enterprise State Model

---

AWORK

Enterprise Workflow Model

---

APERM

Enterprise Permission Model

---

AAPI

Enterprise API Model

---

ASEC

Enterprise Security Model

---

AINT

Enterprise Integration Model

---

AAI

Enterprise AI Model

---

AMEM

Enterprise Memory Model

---

AEVAL

Enterprise Evaluation Model

---

AAGENT

Enterprise Agent Model

---

AGOV

Enterprise Governance Model

---

AOBS

Enterprise Observability Model

---

ADEP

Enterprise Deployment Model

---

ABLUE

Enterprise Blueprint

---

# Rules

A prefix may belong to exactly one concept.

A concept may have exactly one prefix.

---

# Golden Rule

Identifiers are enterprise contracts.

They shall never change once assigned.