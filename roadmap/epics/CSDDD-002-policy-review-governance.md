# CSDDD-002 — Policy Review & DD-Governance

**CSDDD-Referenz:** Art. 7 — Integration der Due Diligence in Unternehmenspolitik  
**Phase:** 1 — Kritische Compliance-Lücken  
**Priorität:** HOCH  
**Aktueller Stand:** 40% → Ziel: 100%  
**Gesamtaufwand:** ~8 Story Points  
**Status:** 🟢 DONE  

---

## Kontext & Anforderung

Art. 7 CSDDD schreibt vor, dass Unternehmen eine DD-Politik einführen und diese **mindestens alle 24 Monate** überprüfen und aktualisieren müssen. Die Politik muss: (a) die Werte des Unternehmens beschreiben, (b) die geplanten Ansätze für DD darlegen, (c) einen Verhaltenskodex für Mitarbeiter/Lieferanten enthalten, (d) öffentlich zugänglich sein.

**Aktueller EIOS-Stand:**
- DD-Prozesse (Risk, CAP, Findings) existieren ✅
- Kein Mechanismus für die strukturierte Ablage und Versionierung der DD-Politik
- Kein automatischer 24-Monats-Review-Zyklus
- Kein Nachweis über Verfügbarkeit / Veröffentlichungsdatum der Politik

---

## Stories

### CSDDD-002-S1 — DD-Politik Repository
**Beschreibung:** Als Compliance-Manager möchte ich die Due-Diligence-Politik des Unternehmens im System ablegen und versionieren, damit Prüfer auf die aktuelle und historische Version zugreifen können.

**Akzeptanzkriterien:**
- [ ] Politik kann als Dokument (PDF, DOCX) oder strukturierter Text gespeichert werden
- [ ] Versionierung: Jede Aktualisierung erstellt eine neue Version (nicht überschreiben)
- [ ] Metadaten pro Version: Gültig-ab-Datum, Genehmigt-von (Name + Rolle), Veröffentlicht-am, Nächste-Review-Fälligkeit (automatisch: +24 Monate)
- [ ] Dokument kann als "öffentlich zugänglich" markiert werden → erzeugt öffentlichen Link ohne Auth
- [ ] `organization_id` PFLICHT-Filter auf allen Queries

**Technische Analyse:**
- **Backend:** Neues Modell `DDPolicy` mit Feldern: `id`, `organization_id`, `version`, `title`, `content_text` (optional), `file_url` (optional), `approved_by`, `approved_role`, `valid_from`, `published_at`, `next_review_due`, `is_public`, `status` (Enum: Draft/Active/Archived)
- **Backend:** File-Upload Endpoint analog bestehender Evidence-Upload-Logik
- **Backend:** Endpoint `GET /policies/current` — öffentlich, kein Auth wenn `is_public=True`
- **Frontend:** Neuer Bereich "Governance & Policies" in Settings oder Compliance-Bereich

**Abhängigkeiten:** Keine  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-002-S2 — 24-Monats-Review-Zyklus
**Beschreibung:** Als Compliance-Manager möchte ich automatisch erinnert werden wenn eine DD-Politik ihren 24-Monats-Review-Termin erreicht, damit keine Frist versäumt wird.

**Akzeptanzkriterien:**
- [ ] System berechnet `next_review_due = valid_from + 24 Monate` automatisch bei Aktivierung
- [ ] E-Mail-Benachrichtigung 60 Tage vor Fälligkeit an Compliance-Manager-Rolle
- [ ] E-Mail-Benachrichtigung 30 Tage vor Fälligkeit (Eskalation)
- [ ] Dashboard-Banner wenn Fälligkeit überschritten
- [ ] Review-Prozess: Bestehende Politik kann als Basis für neue Version geklont werden
- [ ] Review-Status in Governance-Übersicht: "Aktuell / Review fällig / Überfällig"

**Technische Analyse:**
- **Backend:** Background-Job (Celery Beat oder FastAPI LifeSpan) — tägliche Prüfung `next_review_due`
- **Backend:** E-Mail-Service analog bestehender Notification-Logik
- **Frontend:** Dashboard-Widget "Policy Review Status" + Banner-Komponente
- **Frontend:** "Review starten" Button öffnet neuen Entwurf basierend auf aktiver Version

**Abhängigkeiten:** CSDDD-002-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-002-S3 — Verhaltenskodex-Modul
**Beschreibung:** Als Compliance-Manager möchte ich den Verhaltenskodex für Lieferanten und Mitarbeiter strukturiert im System abbilden, damit Lieferanten ihn bei Onboarding anerkennen müssen.

**Akzeptanzkriterien:**
- [ ] Code of Conduct als separate Entität mit eigenem Versionszyklus (kann aber an DD-Politik gekoppelt sein)
- [ ] Lieferant muss bei Onboarding / Annual Review aktiv bestätigen: "Ich habe gelesen und stimme zu" + Datum + Name
- [ ] Bestätigungen sind unveränderlich gespeichert (Audit Trail)
- [ ] Report: Welche Lieferanten haben noch nicht bestätigt?
- [ ] Automatische Erinnerung wenn Bestätigung ausläuft (konfigurierbar: 12 oder 24 Monate)

**Technische Analyse:**
- **Backend:** Neues Modell `CodeOfConduct` + `CoCAcceptance` (supplier_id, coc_version, accepted_at, accepted_by_name, ip_hash)
- **Backend:** Endpoint `POST /suppliers/{id}/coc-acceptance` — kein Rückgabewert außer Bestätigungs-ID
- **Backend:** ip_hash statt ip_raw (DSGVO)
- **Frontend:** Supplier-Onboarding-Flow ergänzen um CoC-Bestätigungsschritt

**Abhängigkeiten:** CSDDD-002-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-002-S4 — Governance-Dashboard
**Beschreibung:** Als Management möchte ich eine zentrale Übersicht aller governance-relevanten Fristen (Politik-Reviews, CoC-Bestätigungen, Reporting-Deadlines), um keine regulatorischen Pflichten zu versäumen.

**Akzeptanzkriterien:**
- [ ] Kalender- oder Listen-Ansicht aller anstehenden Fristen
- [ ] Kategorien: DD-Politik Review, CoC-Bestätigung Lieferanten, CSDDD-Jahresbericht, Art. 22 Board-Review
- [ ] Status: Erledigt / Ausstehend / Überfällig
- [ ] Exportierbar als Kalender-Datei (.ics) für Integration in Outlook / Google Calendar
- [ ] Filter nach Kategorie und Verantwortlichem

**Technische Analyse:**
- **Backend:** Aggregations-Endpoint `GET /governance/calendar` — sammelt Fristen aus Policy, CoCAcceptance, Reports
- **Frontend:** Neuer Tab "Governance-Kalender" in Settings oder Compliance-Übersicht
- **Frontend:** .ics-Export via Browser-Download (kein Server-Side-Rendering nötig)

**Abhängigkeiten:** CSDDD-002-S1, CSDDD-002-S2  
**Story Points:** 1  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] IP-Adressen nur als Hash gespeichert (DSGVO)
- [ ] Öffentliche Policy-Links ohne Auth abrufbar
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 7 — DD-Politik & Governance"
- [ ] Changelog ergänzt
