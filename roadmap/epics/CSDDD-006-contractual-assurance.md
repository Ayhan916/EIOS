# CSDDD-006 — Contractual Assurance Module

**CSDDD-Referenz:** Art. 10 Abs. 2 lit. b — Vertragliche Zusicherungen von Geschäftspartnern  
**Phase:** 2 — Fehlende Module  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~11 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 10 Abs. 2 lit. b CSDDD schreibt vor, dass Unternehmen von mittelbaren Geschäftspartnern (Tier 2+) vertragliche Zusicherungen einholen, wonach diese: (1) die Verhaltensanforderungen einhalten, (2) entsprechende Zusicherungen an ihre Lieferanten weitergeben (Kaskadenklausel). Diese Kaskade muss dokumentiert sein.

**Aktueller EIOS-Stand:**
- Lieferanten-Onboarding ✅
- Code-of-Conduct-Bestätigung (nach CSDDD-002) geplant
- Kein Mechanismus für Vertragsklausel-Tracking (welche Verträge enthalten DD-Klauseln)
- Keine Kaskadenprüfung (hat Tier 2 seine Lieferanten vertraglich gebunden?)

---

## Stories

### CSDDD-006-S1 — Vertragsklausel-Register
**Beschreibung:** Als Compliance-Manager möchte ich pro Lieferant dokumentieren ob und welche Vertragsklauseln zu DD-Anforderungen vereinbart sind, damit ich Art. 10 Abs. 2 lit. b jederzeit nachweisen kann.

**Akzeptanzkriterien:**
- [ ] Pro Lieferant/Partner: Neuer Tab "Vertragsklauseln"
- [ ] Felder: Vertragstyp (Rahmenvertrag / Einzelvertrag / Dienstleistungsvertrag), Vertragsversion, Datum, Enthaltene Klauseln (Multi-Select: DD-Verpflichtung / Prüfrecht / Audit-Recht / Datenweitergabe / Kaskadenklausel / Vertragsstrafe), Dokument-Upload (PDF)
- [ ] Status: "Vertrag enthält DD-Klauseln" (Ja/Nein/In Verhandlung)
- [ ] Warnung wenn Lieferant Tier 1 aber keine Kaskadenklausel für Tier 2
- [ ] `organization_id` PFLICHT-Filter

**Technische Analyse:**
- **Backend:** Neues Modell `SupplierContract` mit FK zu `Supplier`, Felder: `contract_type`, `version`, `contract_date`, `clauses` (Array[Enum]), `document_url`, `cascade_confirmed`
- **Backend:** Router `interfaces/api/routers/supplier_contracts.py`
- **Frontend:** Neuer Tab in Supplier-Detailseite

**Abhängigkeiten:** Keine  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-006-S2 — Kaskadenprüfungs-Workflow
**Beschreibung:** Als Compliance-Manager möchte ich prüfen ob Tier-1-Lieferanten ihre eigenen Lieferanten (Tier 2) ebenfalls vertraglich gebunden haben, damit die Kaskadenklausel (Art. 10 Abs. 2 lit. b Satz 2) erfüllt ist.

**Akzeptanzkriterien:**
- [ ] Tier-1-Lieferant kann bestätigen: "Meine Sublieferanten sind ebenfalls vertraglich gebunden" (mit Datum + Bestätigendem)
- [ ] Alternativ: Tier-1 lädt Nachweis-Dokument hoch (z.B. eigener Lieferantenvertrag)
- [ ] System zeigt je Tier-1: Kaskadenklausel-Status (Bestätigt / Ausstehend / Nicht vorhanden)
- [ ] Automatische Erinnerung wenn Kaskadenbestätigung > 24 Monate alt
- [ ] Kaskaden-Lücken werden in Compliance-Gap-Report ausgewiesen

**Technische Analyse:**
- **Backend:** Neues Modell `CascadeConfirmation` mit FK zu `Supplier` (Tier-1), Feldern: `confirmed_by`, `confirmed_at`, `document_url`, `expires_at` (= `confirmed_at + 24 Monate`)
- **Backend:** Endpoint `POST /suppliers/{id}/cascade-confirmation`
- **Backend:** Gap-Report-Query: Lieferanten Tier 1 ohne `CascadeConfirmation` oder mit abgelaufener Bestätigung

**Abhängigkeiten:** CSDDD-006-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-006-S3 — Vertragsklausel-Compliance-Report
**Beschreibung:** Als Compliance-Manager möchte ich einen Überblick über den Vertragsstatus aller Lieferanten erhalten, damit ich Lücken proaktiv schließen kann.

**Akzeptanzkriterien:**
- [ ] Report listet alle Lieferanten mit Vertragsklausel-Status
- [ ] Ampelfarben: Grün = vollständig + Kaskade, Gelb = teilweise, Rot = keine Klauseln
- [ ] Separate Sektion: "Tier-1 ohne Kaskadennachweis" (höchstes regulatorisches Risiko)
- [ ] Export als CSV und PDF
- [ ] Zeitliche Ansicht: Wie viele Lieferanten haben in den letzten 12 Monaten ihren Vertragsstatus verbessert?

**Technische Analyse:**
- **Backend:** Aggregations-Endpoint `GET /reports/contractual-assurance`
- **Frontend:** Neuer Tab in Reports-Bereich

**Abhängigkeiten:** CSDDD-006-S1, CSDDD-006-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-006-S4 — Vertragsklausel-Vorlagen-Bibliothek
**Beschreibung:** Als Compliance-Manager möchte ich auf standardisierte Vertragsklausel-Vorlagen zugreifen (basierend auf CSDDD + branchenüblichen Standards), damit Vertragsverhandlungen mit Lieferanten schneller gehen.

**Akzeptanzkriterien:**
- [ ] Bibliothek mit mind. 5 vordefinierten Klausel-Vorlagen (Deutsch + Englisch): DD-Grundverpflichtung, Audit-Recht, Kaskadenklausel, Melde-/Informationspflicht, Vertragsstrafe bei Verstoß
- [ ] Vorlagen können kopiert, angepasst und als "Organisationsvorlage" gespeichert werden
- [ ] Vorlagen mit juristischem Disclaimer: "Dies ist keine Rechtsberatung"
- [ ] Download als .docx für direkte Verwendung im Vertragsentwurf

**Technische Analyse:**
- **Backend:** Neues Modell `ClauseTemplate` — globale Templates (organization_id=NULL) + org-spezifische
- **Frontend:** Neue Seite "Klausel-Bibliothek" — Tabelle + Vorschau + Export
- **DOCX-Export:** Python-seitig: `python-docx` Library

**Abhängigkeiten:** Keine (parallel zu S1 entwickelbar)  
**Story Points:** 3  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] Dokument-Uploads: Mime-Type Validierung, max. 20 MB
- [ ] Juristischer Disclaimer auf Klausel-Vorlagen
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 10 — Contractual Assurance"
- [ ] Changelog ergänzt
