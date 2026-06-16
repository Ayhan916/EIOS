# ENTERPRISE ENTITY CATALOG

ID: DBE-0001

Version: 1.0

Status: DRAFT

Owner: Founder

---

# Purpose

This document defines the canonical enterprise entities of EIOS.

Every business object shall be represented by exactly one enterprise entity.

---

# Dependencies

- AENT-0001

- AREL-0001

- AATTR-0001

- DBS-0001

---

# Related Documents

- AONTO-0001

- AAI-0001

- AMEM-0001

---

# Entity Standard

Every entity shall define:

- Entity ID

- Name

- Purpose

- Owner

- Primary Relationships

- Mandatory Attributes

- Lifecycle

---

# Enterprise Entities

## Organization

Purpose:

Represents a tenant organization.

Owner:

Platform

---

## User

Purpose:

Represents an authenticated person.

Owner:

Identity Management

---

## Sector

Purpose:

Represents an industry sector classified by NACE code.

Primary unit of ESG assessment per FR-002 (sector-level by default).

Owner:

ESG Domain

---

## Company

Purpose:

Represents a company assessed within a Sector context.

Company is a sub-entity of Sector and is not the primary assessment scope.

Owner:

ESG Domain

---

## Supplier

Purpose:

Represents a supplier linked to a Company and Sector.

Owner:

Supply Chain Domain

---

## Assessment

Purpose:

Represents an ESG assessment.

Owner:

Assessment Domain

---

## Evidence

Purpose:

Represents supporting evidence.

Owner:

Knowledge Domain

---

## Source

Purpose:

Represents an external or internal source.

Owner:

Knowledge Domain

---

## Risk

Purpose:

Represents an identified enterprise risk.

Owner:

Risk Domain

---

## Opportunity

Purpose:

Represents an identified opportunity.

Owner:

Strategy Domain

---

## Recommendation

Purpose:

Represents an AI or human recommendation.

Owner:

Recommendation Domain

---

## Decision

Purpose:

Represents a governance decision.

Owner:

Governance Domain

---

## Workflow

Purpose:

Represents an executable enterprise workflow.

Owner:

Workflow Domain

---

## Event

Purpose:

Represents an immutable enterprise event.

Owner:

Event Domain

---

## Agent

Purpose:

Represents an enterprise AI agent.

Owner:

AI Domain

---

## Memory

Purpose:

Represents institutional memory.

Owner:

Memory Domain

---

## Taxonomy

Purpose:

Represents a canonical taxonomy concept.

Owner:

Knowledge Domain

---

# Lifecycle Standard

Every entity shall support:

Created

↓

Validated

↓

Active

↓

Archived

↓

Logically Deleted

---

# Common Requirements

Every entity shall:

- have a UUID

- have a Version

- have a Status

- be Auditable

- be Explainable where applicable

---

# Golden Rule

Entities define what exists.

Relationships define how enterprise knowledge is created.