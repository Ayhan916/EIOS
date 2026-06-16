# ENTERPRISE DATABASE SCHEMA

ID: DBS-0001

Version: 1.0

Status: DRAFT

Owner: Founder

---

# Purpose

This document defines the canonical logical database schema of EIOS.

The schema serves as the authoritative source for all future database implementations.

Implementations may vary, but the enterprise model shall remain consistent.

---

# Dependencies

- ADATA-0001

- AENT-0001

- AREL-0001

- AATTR-0001

- ACON-0001

---

# Related Documents

- AAPI-0001

- AAI-0001

- AMEM-0001

- ABLUE-0001

---

# Design Principles

The schema shall be:

- normalized

- versioned

- auditable

- extensible

- explainable

---

# Core Entities

## Organization

Stores enterprise organizations.

---

## User

Stores platform users.

---

## Sector

Stores NACE-classified industry sectors.

Primary assessment scope per FR-002.

---

## Company

Stores companies assessed within a Sector context.

Company is a sub-entity of Sector, not the primary assessment scope.

---

## Supplier

Stores suppliers linked to a Company and Sector.

---

## Assessment

Stores ESG assessments.

---

## Evidence

Stores evidence objects.

---

## Source

Stores information sources.

---

## Recommendation

Stores recommendations.

---

## Risk

Stores identified risks.

---

## Opportunity

Stores identified opportunities.

---

## Decision

Stores governance decisions.

---

## Workflow

Stores workflow definitions.

---

## Event

Stores immutable enterprise events.

---

## Agent

Stores enterprise agent definitions.

---

## Memory

Stores enterprise memory objects.

---

## Taxonomy

Stores taxonomy concepts.

---

# Common Attributes

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

# Relationship Principles

Relationships shall use:

- foreign keys

- immutable identifiers

- explicit cardinality

Implicit relationships are prohibited.

---

# Soft Delete Policy

Business entities shall support logical deletion.

Physical deletion should be restricted to operational requirements.

---

# Audit Rule

Every modification shall generate:

- Event

- Audit Record

- Version Record

---

# Explainability Rule

Every AI-generated object shall reference:

- Evidence

- Source

- Confidence

- Reasoning

---

# Future Implementation Targets

This schema shall serve as the basis for:

- PostgreSQL

- SQLAlchemy

- Alembic

- FastAPI

- Pydantic

- OpenAPI

- Knowledge Graph

---

# Golden Rule

The database stores enterprise facts.

Meaning is defined by the enterprise ontology.