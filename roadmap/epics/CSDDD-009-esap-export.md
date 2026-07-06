# CSDDD-009 — ESAP Export

**CSDDD-Referenz:** Art. 16 Abs. 2 — Öffentliche Berichterstattung / ESAP  
**Phase:** 4 — Zukunftssicherung  
**Priorität:** NIEDRIG (Frist: ESAP-Pflicht ab ca. 2031)  
**Aktueller Stand:** 0% (ESAP-spezifisch) / 90% (allgemeiner Bericht) → Ziel: 100%  
**Gesamtaufwand:** ~10 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 16 CSDDD i.V.m. der ESAP-Verordnung (EU) 2023/2859 verpflichtet Unternehmen, ihre DD-Berichte maschinell lesbar im **European Single Access Point (ESAP)** einzureichen. Das ESAP-Portal der ESMA nimmt Daten in strukturierten Formaten an (primär XBRL/Inline XBRL). Die Pflicht gilt voraussichtlich ab 2031 für große Unternehmen.

**Aktueller EIOS-Stand:**
- CSDDD-Jahresbericht als PDF generierbar ✅
- Kein strukturiertes XBRL/XML-Export-Format
- Kein ESAP-spezifisches Reporting-Schema implementiert

---

## Stories

### CSDDD-009-S1 — ESAP-Datenmodell & Taxonomie-Mapping
**Beschreibung:** Als Compliance-Manager möchte ich wissen welche EIOS-Felder auf welche ESAP/XBRL-Konzepte gemappt werden, damit der Export-Prozess klar definiert ist.

**Akzeptanzkriterien:**
- [ ] Mapping-Dokument erstellt: EIOS-Feld → ESAP/XBRL-Konzept (basierend auf EFRAG/ESMA Taxonomie)
- [ ] Alle Pflichtfelder nach Art. 16 CSDDD abgedeckt: Beschreibung der Risiken, ergriffene Maßnahmen, Ergebnis der Maßnahmen, Genehmigungsstruktur
- [ ] Mapping in Konfigurationsdatei abgelegt (wartbar, versioniert)
- [ ] ESAP-Taxonomie-Version dokumentiert (wird sich bis 2031 noch ändern — Design auf Austauschbarkeit ausgerichtet)

**Technische Analyse:**
- **Backend:** Konfigurationsdatei `config/esap_taxonomy_mapping.yaml`
- **Backend:** Mapping-Validator als Unit-Test: prüft ob alle Pflichtfelder gemappt sind
- **Dokumentation:** Confluence-Seite mit Mapping-Tabelle und Taxonomie-Quelle

**Abhängigkeiten:** Keine  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-009-S2 — Strukturierter JSON/XML-Export
**Beschreibung:** Als Compliance-Manager möchte ich den CSDDD-Jahresbericht als strukturierte Datei (JSON + XML) exportieren, damit die Daten maschinell weiterverarbeitbar und ESAP-ready sind.

**Akzeptanzkriterien:**
- [ ] Export-Format: JSON (primär) + XML (XBRL-ähnlich, sekundär) mit Namespace-Unterstützung
- [ ] Alle Felder aus Art. 16 CSDDD abgedeckt
- [ ] Schema-Validierung vor Export: fehlerhafte Daten werden mit klarer Fehlermeldung abgewiesen
- [ ] Export inklusive aller verknüpften Artefakte: Risiken, CAPs, Remedy Cases, Stakeholder-Konsultationen
- [ ] Bestehender PDF-Export bleibt unverändert; JSON/XML ist additiv

**Technische Analyse:**
- **Backend:** Erweiterung von `build_csddd_report()` — neues Output-Format als Parameter
- **Backend:** Pydantic-Modelle für ESAP-Export-Schema — automatische Validierung
- **Backend:** Endpoint `GET /reports/csddd?format=json` / `?format=xml`
- **Frontend:** "Export" Dropdown in Report-Bereich: "PDF / JSON / XML"

**Abhängigkeiten:** CSDDD-009-S1  
**Story Points:** 4  
**Status:** 🔴 TODO

---

### CSDDD-009-S3 — ESAP-Upload-Vorbereitung
**Beschreibung:** Als Compliance-Manager möchte ich eine geführte Checkliste für den ESAP-Upload durchlaufen, damit sichergestellt ist dass alle Pflichtfelder korrekt ausgefüllt sind bevor das Dokument eingereicht wird.

**Akzeptanzkriterien:**
- [ ] Pre-Submission-Checkliste: Validiert alle Pflichtfelder, warnt bei leerem Pflichtfeld
- [ ] Vorschau: "So sieht Ihr Bericht in ESAP aus" — schematische Darstellung
- [ ] Handlungsanleitung: Schritt-für-Schritt wie das generierte XML in ESAP hochzuladen ist (Link zu ESMA-Dokumentation)
- [ ] Status-Tracking: "Bereit für Einreichung / Einreichung ausstehend / Eingereicht"
- [ ] Einreichungsdatum und -Nachweis dokumentierbar (manuell eintragen, da direkter API-Upload zu ESAP aktuell nicht möglich)

**Technische Analyse:**
- **Backend:** Neues Modell `ESAPSubmission` mit Feldern: `report_year`, `submitted_at`, `submitted_by`, `confirmation_reference`, `status`
- **Frontend:** Neuer Schritt in Report-Generierungs-Flow: "ESAP Export & Einreichung"
- **Hinweis:** Kein direkter ESAP-API-Upload in erster Version — ESAP API ist noch nicht final spezifiziert

**Abhängigkeiten:** CSDDD-009-S2  
**Story Points:** 4  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 3 Stories implementiert und tested
- [ ] Schema-Validierung schlägt bei Pflichtfeld-Lücken fehl (nicht silent)
- [ ] JSON-Schema-Datei für Export versioniert
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 16 — ESAP Export"
- [ ] Changelog ergänzt

---

> **Hinweis:** ESAP-Pflicht wird erst ca. 2031 aktiv. Epic kann bis Phase-4-Start zurückgestellt werden. Taxonomie-Mapping (S1) sollte trotzdem frühzeitig dokumentiert werden da sich Änderungen an EIOS-Datenmodellen sonst auf das Mapping auswirken.
