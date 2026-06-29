# Documentation Rules — EIOS

> Regeln für das Erstellen, Aktualisieren und Versionieren von Dokumentation.
> Confluence ist die Single Source of Truth. Diese Datei definiert wie.

---

## Grundsatz

Jede Confluence-Seite spiegelt exakt den aktuellen Stand des Codes wider.
Abweichungen sind Fehler — keine Ausnahmen.

---

## Confluence-Seitenstruktur (EIOS Space)

```
EIOS (Root — Page ID: 426178)
│
├── System Overview
├── Technical Architecture
│   ├── Clean Architecture
│   ├── Security & Auth
│   └── Database Schema
│
├── Features & Module
│   ├── Supplier Management
│   ├── Health Engine
│   ├── Sanctions Screening
│   ├── Compliance Lifecycle
│   ├── Reporting
│   └── AI Copilot
│
├── API Reference
│   ├── Authentication
│   ├── Suppliers API
│   ├── Assessments API
│   └── Reports API
│
├── Regulatorische & Fachliche Grundlagen (Page ID: 1212417)
│   ├── LkSG
│   ├── CSDDD
│   ├── CSRD
│   ├── SFDR
│   ├── Sanktionsrecht
│   ├── ESG-Grundlagen
│   └── Glossar
│
├── Vollumfängliche Systemdokumentation (Page ID: 688130)
│
├── Video Präsentation (Page ID: 720898)
│
└── Operations
    ├── Deployment
    ├── Monitoring
    └── Runbooks
```

---

## Pflichtinhalte jeder Feature-Dokumentationsseite

```markdown
## Zweck
Ein Satz: Was macht dieses Feature? Für wen?

## Beschreibung
2–4 Absätze: Vollständige fachliche Beschreibung. Auch für Branchenfremde verständlich.

## Architektur
- Backend-Service(s): Datei + Klasse + Methoden
- API-Endpunkte: Methode, Pfad, Auth-Anforderung
- Datenbankmodelle: Tabellen + relevante Felder
- Frontend-Komponenten: Datei + Route
- Externe Abhängigkeiten: welche Services/APIs

## Voraussetzungen & Berechtigungen
- Welche Rolle braucht ein Nutzer?
- Welche Umgebungsvariablen müssen gesetzt sein?
- Welche anderen Features müssen aktiv sein?

## Schritt-für-Schritt Anleitung
Nummerierte Schritte für den Endanwender.

## API-Beispiele
### Request
```http
POST /api/v1/suppliers
Authorization: Bearer {token}
Content-Type: application/json

{ "name": "Acme Corp", "country": "DE" }
```

### Response (200)
```json
{ "id": "...", "name": "Acme Corp", "health_score": 75 }
```

### Fehlerfälle
| Code | Bedeutung | Lösung |
|------|-----------|--------|
| 400 | Ungültige Eingabe | Felder prüfen |
| 403 | Keine Berechtigung | Rolle prüfen |
| 404 | Nicht gefunden | ID prüfen |

## Best Practices
- Konkrete Empfehlungen für produktiven Einsatz

## FAQ
- Häufige Fragen mit Antworten

## Verwandte Seiten
- Links zu verwandten Confluence-Seiten

## Changelog
| Datum | Version | Änderung |
|-------|---------|---------|
| 2026-06-29 | 1.0 | Erstellt |
```

---

## Wann wird Dokumentation erstellt?

| Auslöser | Aktion |
|----------|--------|
| Neues Feature implementiert | Neue Confluence-Seite als Entwurf |
| Bestehendes Feature geändert | Betroffene Seite aktualisieren |
| API-Endpunkt hinzugefügt | API-Reference-Seite ergänzen |
| Datenbankmodell geändert | Architekturseite aktualisieren |
| Sicherheitsrelevante Änderung | Security-Seite + Release Notes |
| Bug mit Nutzerauswirkung behoben | FAQ ergänzen |

---

## Entwurf vs. Veröffentlicht

**Entwurf (Draft):**
- Wird als Confluence-Seite erstellt mit Prefix `[ENTWURF]` im Titel
- Warte auf Genehmigung des Projektverantwortlichen
- Inhalt kann sich noch ändern

**Veröffentlicht:**
- Prefix `[ENTWURF]` entfernen
- Seite in die richtige Hierarchie einordnen
- Andere Seiten verlinken

---

## Veraltete Dokumentation

Wenn Code gelöscht oder verändert wurde:

1. Confluence-Seite suchen
2. Seite mit Banner markieren:
   ```
   ⚠️ DIESE SEITE IST MÖGLICHERWEISE VERALTET
   Letzter Codestand: [Datum]
   Bitte Projektverantwortlichen informieren.
   ```
3. Jira-Ticket erstellen: "Dokumentation veraltet: [Seitenname]"

---

## Changelog-Format (CHANGELOG.md)

```markdown
## [Unreleased]

### Added
- Supplier Digital Twin: 8-dimensionaler Health Score

### Changed
- Sanktions-Matching-Schwellenwert von 0.40 auf 0.45 erhöht

### Fixed
- password_hash erschien in SupplierUser API Response (#KAN-42)

### Security
- JWT-Token-Validierung auf RS256 umgestellt

## [1.2.0] — 2026-06-29
...
```

---

## Release Notes Format

```markdown
# Release Notes — EIOS v1.2.0

**Release-Datum:** 2026-06-29
**Typ:** Minor Release

## Highlights
- Kurze, nicht-technische Zusammenfassung für Stakeholder

## Neue Features
- [KAN-3] CSRD iXBRL Validator — automatische Validierung...

## Verbesserungen
- [KAN-37] Health Score Berechnung 40% schneller

## Bugfixes
- [KAN-42] password_hash aus API Response entfernt

## Breaking Changes
- Keine

## Migration
- Keine Datenbankmigrationen erforderlich
```

---

## Confluence API — Technischer Zugriff

```python
# Helper-Datei: /tmp/confluence_helper.py
from confluence_helper import create_page, ROOT_ID

# Neue Seite erstellen
page_id = create_page("Titel", BODY_HTML, parent_id=ROOT_ID)

# Seite aktualisieren (PUT mit Version-Bump)
# → update_page(page_id, "Titel", BODY_HTML) implementieren wenn nötig
```

Confluence-Domain: `privaterelay-team-cdwul3gk.atlassian.net`
Space Key: `EIOS`
Root Page ID: `426178`
