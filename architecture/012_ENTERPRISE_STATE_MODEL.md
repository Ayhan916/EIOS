# ENTERPRISE STATE MODEL

ID: ASTATE-0001

Version: 1.0

Status: DRAFT

Owner: Founder

---

# Purpose

The Enterprise State Model defines every possible lifecycle state of enterprise objects.

Every entity shall always be in exactly one valid state.

---

# State Principles

States shall be:

- explicit
- deterministic
- auditable
- versioned
- reversible when permitted

---

# Standard Lifecycle

Created

↓

Draft

↓

Validated

↓

Reviewed

↓

Approved

↓

Active

↓

Suspended

↓

Archived

↓

Deleted (logical only)

---

# Allowed Transitions

Created → Draft

Draft → Validated

Validated → Reviewed

Reviewed → Approved

Approved → Active

Active → Suspended

Suspended → Active

Active → Archived

Archived → Deleted

---

# Forbidden Transitions

Created → Active

Draft → Archived

Deleted → Active

Archived → Draft

---

# Approval Rules

Objects requiring governance approval:

- Assessment

- Recommendation

- Policy

- Benchmark

- Decision

shall not enter ACTIVE state before approval.

---

# AI Objects

AI-generated objects shall initially have:

State:

Draft

Until validated by defined rules.

---

# Version Rule

Changing the state shall create:

- Event

- Audit Entry

- Version Record

---

# Explainability Rule

Every state transition shall answer:

- Who?

- When?

- Why?

- Based on what evidence?

---

# State Categories

Operational

Governance

AI

Knowledge

System

---

# Golden Rule

No object changes without a state transition.

No state transition occurs without an event.