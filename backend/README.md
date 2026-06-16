# EIOS Backend

Status: ACTIVE

Owner: Founder

---

# Mission

The backend is the execution engine of EIOS.

It implements the enterprise architecture defined in the repository.

The backend shall never redefine business concepts.

It shall implement them.

---

# Architectural Principles

The backend follows:

- Domain-Driven Design (DDD)

- Clean Architecture

- SOLID Principles

- Single Source of Truth

- Enterprise Governance

---

# Layer Structure

domain/

Business concepts

↓

application/

Business use cases

↓

infrastructure/

Technical implementations

↓

interfaces/

External communication

↓

app/

Composition and startup

---

# Rule

Dependencies always point inward.

Infrastructure depends on Domain.

Domain depends on nothing.

---

# Golden Rule

Business rules must never depend on frameworks.