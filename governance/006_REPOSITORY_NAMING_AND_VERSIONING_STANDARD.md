# REPOSITORY NAMING AND VERSIONING STANDARD

ID: GNVS-0001

Version: 1.0

Status: APPROVED

Owner: Founder

---

# Purpose

This document defines the official naming and versioning rules for the EIOS repository.

Consistency enables automation.

---

# File Naming Rules

File names shall:

- use UPPER_CASE for canonical architecture documents

- use underscores instead of spaces

- avoid special characters

- remain stable after publication

Example:

025_ENTERPRISE_BLUEPRINT_SUMMARY.md

Correct

---

Enterprise Blueprint Summary.md

Incorrect

---

# Directory Rules

Directories shall represent logical domains.

Examples:

architecture/

governance/

product/

implementation/

tasks/

taxonomies/

schemas/

agents/

---

# Version Format

MAJOR.MINOR

Examples:

1.0

1.1

2.0

---

# Version Rules

Major version:

Breaking change

Minor version:

Backward compatible improvement

Patch-level changes shall be recorded in the changelog but do not require a new document identifier.

---

# Status Values

Allowed values:

- DRAFT

- REVIEW

- APPROVED

- ACTIVE

- DEPRECATED

- ARCHIVED

---

# Change Log

Every major document shall contain:

- Version

- Date

- Author

- Summary of Change

---

# Identifier Rule

Document filenames are not identifiers.

Canonical IDs are identifiers.

Example:

Filename:

018_ENTERPRISE_AI_MODEL.md

Canonical ID:

AAI-0001

---

# Compatibility Rule

Deprecated documents shall:

- remain accessible

- reference their successor

- never silently disappear

---

# AI Rule

AI systems shall use canonical IDs for reasoning and filenames only for navigation.

---

# Golden Rule

Names improve readability.

Identifiers guarantee consistency.