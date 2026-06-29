# Workflow Rules — EIOS

> Definiert welcher Prozess wann ausgelöst wird.
> Verbindlich für alle Implementierungen durch Claude Code.

---

## Entscheidungsbaum

```
Benutzerfrage / Aufgabe eingetroffen
          │
          ▼
  Confluence durchsuchen
          │
    ┌─────┴─────┐
    │           │
  Gefunden   Nicht gefunden
    │           │
    ▼           ▼
  CASE A    Code analysieren
                │
        ┌───────┼───────┐
        │       │       │
   Backend  Frontend   Beide
   fehlt    fehlt      fehlen
        │       │       │
     CASE C  CASE D  CASE E
        │
  Backend da,
  Frontend da,
  Doku fehlt
        │
     CASE B
```

---

## CASE A — Vollständig dokumentiert

**Bedingung:** Confluence-Seite existiert, Code stimmt überein.

**Aktion:**
1. Antwort auf Basis der Dokumentation geben
2. Quellenangabe: Confluence-Seite + URL
3. Wenn Code und Doku abweichen → Abweichung melden (siehe CASE B-Trigger)

**Kein Jira-Ticket, kein Code, keine Dokumentationsänderung.**

---

## CASE B — Code vorhanden, Dokumentation fehlt

**Bedingung:** Feature im Code gefunden, kein Confluence-Eintrag.

**Pflichtfelder der automatischen Analyse:**

```
Feature: [Name]
Status: Code vorhanden, Dokumentation fehlt

Backend:
  - Service: backend/services/[name].py
  - Endpunkte: [Methode] [Pfad]
  - Modelle: [Tabellen]

Frontend:
  - Komponente: frontend/src/[Pfad]
  - Route: [Route]

Tests:
  - Vorhanden: [ja/nein]
  - Abdeckung: [%]

Empfehlung:
  Dokumentation erstellen für Confluence-Seite "[Titel]"
  Unter Parent: [Confluence-Bereich]
```

**Danach:** Dokumentations-Entwurf erstellen → Genehmigung anfragen → Confluence aktualisieren.

---

## CASE C — Backend vorhanden, Frontend fehlt

**Bedingung:** API-Endpunkt existiert, keine UI-Komponente.

**Pflichtanalyse:**

```
Feature: [Name]
Status: Backend vorhanden, Frontend fehlt

Vorhandenes Backend:
  Endpunkt: POST /api/v1/[resource]
  Schema: [Request/Response]
  Auth: [Rollen]
  Service: [Datei]

Fehlende Frontend-Komponenten:
  - [Komponentenname] — Seite/Modal für [Funktion]
  - [Hook] — Datenfetching für [Endpunkt]
  - [Route] — /dashboard/[resource]

Geschätzter Aufwand: [S/M/L/XL]
  S = <1 Tag, M = 1-3 Tage, L = 3-7 Tage, XL = >7 Tage

Technische Risiken:
  - [Risiko 1]
  - [Risiko 2]

Vorgeschlagene Komponenten:
  [Detaillierter Implementierungsvorschlag]
```

**Dann:** Implementierungsvorschlag präsentieren → Genehmigung abwarten → Implementieren nach Reihenfolge in CLAUDE.md.

---

## CASE D — Frontend vorhanden, Backend fehlt

**Bedingung:** UI-Komponente gefunden, kein entsprechender API-Endpunkt.

**Technischer Bericht:**

```
⚠️ INKONSISTENZ ERKANNT

Feature: [Name]
Frontend: [Datei] — ruft [Endpunkt] auf
Backend: FEHLT — [Endpunkt] nicht implementiert

Mögliche Ursachen:
  □ Unvollständiges Feature (Backend noch in Entwicklung)
  □ Veralteter Branch (Backend wurde entfernt)
  □ UI Dummy / Prototyp (nie für Produktion gedacht)
  □ Architekturfehler (falscher Endpunkt referenziert)

Empfehlung:
  [Konkrete Empfehlung je nach wahrscheinlichster Ursache]

Nächste Schritte:
  → Klärung mit Projektverantwortlichem erforderlich
  → Kein automatisches Coding
```

---

## CASE E — Alles fehlt (Neues Feature)

**Bedingung:** Kein Code, kein Frontend, keine Dokumentation.

**Automatisch erstelltes Jira-Ticket:**

```
Epic: [Zugehöriger Horizont oder TECH]
Story-Titel: [Feature-Name]

Beschreibung:
  [Vollständige fachliche Beschreibung]

Nutzen:
  [Warum ist dieses Feature wertvoll?]

Technische Analyse:
  Backend: [Zu implementierende Services/Endpunkte]
  Frontend: [Zu erstellende Komponenten]
  Datenbank: [Neue Modelle/Felder]
  Tests: [Testfälle]

Akzeptanzkriterien:
  - [ ] [Kriterium 1]
  - [ ] [Kriterium 2]
  - [ ] Tests grün
  - [ ] Dokumentation in Confluence

Aufwand: [S/M/L/XL]
Priorität: [High/Medium/Low]

Risiken:
  - [Risiko 1]
  - [Risiko 2]

Architekturvorschlag:
  [Skizze der Implementierung]
```

**Dann:** Ticket erscheint in Jira → Warten auf Genehmigung.

---

## Implementierungs-Checkliste (nach Genehmigung)

```
□ 1. CLAUDE.md gelesen und Coding Standards geprüft
□ 2. Bestehende ähnliche Implementierungen analysiert
□ 3. Domain Layer zuerst (Entities, Value Objects)
□ 4. Application Layer (Use Cases, Services)
□ 5. Infrastructure Layer (Repository, External Clients)
□ 6. Interface Layer (Router, Schemas)
□ 7. Frontend (Hook → Component → Route)
□ 8. Unit Tests geschrieben
□ 9. Integration Tests geschrieben
□ 10. Alle Tests grün (pytest ausführen)
□ 11. Security Checklist aus coding-standards.md abgehakt
□ 12. Confluence-Dokumentation erstellt/aktualisiert
□ 13. CHANGELOG.md aktualisiert
□ 14. Release Notes ergänzt
□ 15. Jira-Ticket auf "In Review" gesetzt
□ 16. PR-Beschreibung erstellt
```

---

## Prioritäten für Sprint-Planung

| Kriterium | Punkte |
|-----------|--------|
| Regulatorische Pflicht (LkSG/CSDDD/CSRD) | +3 |
| Pilotunde wartet darauf | +3 |
| Enterprise-Sales-Blocker | +2 |
| Sicherheitsrelevant | +2 |
| Technische Schuld mit Produktionsrisiko | +2 |
| Performance-Verbesserung | +1 |
| Nice-to-have Feature | +0 |

**Sprint-Planung:** Tickets mit höchster Punktzahl zuerst. Maximale Sprint-Kapazität: 20 Story Points.

---

## Eskalationsregeln

| Situation | Aktion |
|-----------|--------|
| Sicherheitslücke entdeckt | Sofort melden, Jira-Bug mit "Critical" anlegen, kein Merge |
| Datenleck-Risiko | Implementierung stoppen, Bericht erstellen |
| Widerspruch zwischen Regulierung und Implementierung | Analyse-Dokument erstellen, keine Änderung ohne Klärung |
| Unklare Anforderung | Fragen stellen, nicht raten |
| Konflikte zwischen Architektur und Anforderung | Architektur-Review-Ticket, kein Workaround |

---

## Automatisierungsgrenzlinie

**Claude Code handelt autonom (kein Approval nötig):**
- Code lesen und analysieren
- Tests lokal ausführen
- Dokumentationsentwürfe erstellen
- Jira-Tickets erstellen (nicht schließen)
- Confluence-Entwürfe anlegen

**Claude Code wartet auf Genehmigung:**
- Code in Produktion deployen
- Confluence-Seiten final aktualisieren
- Jira-Tickets schließen oder Status ändern
- Datenbankmigrationen ausführen
- Abhängigkeiten mit Breaking Changes updaten
- Features löschen oder deaktivieren
