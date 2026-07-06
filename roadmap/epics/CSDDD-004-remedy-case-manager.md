# CSDDD-004 — Remedy Case Manager

**CSDDD-Referenz:** Art. 12 — Wiedergutmachung / Behebung tatsächlicher negativer Auswirkungen  
**Phase:** 1 — Kritische Compliance-Lücken  
**Priorität:** HOCH  
**Aktueller Stand:** 30% → Ziel: 100%  
**Gesamtaufwand:** ~10 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 12 CSDDD unterscheidet explizit zwischen (a) **Prävention** (Art. 10 — noch kein Schaden eingetreten) und (b) **Remedy** (Art. 12 — Schaden bereits eingetreten, Wiedergutmachung erforderlich). Remedy umfasst: Entschädigung, Wiederherstellung, Entschuldigung, Reparation, gesellschaftliche Entschädigung.

**Aktueller EIOS-Stand:**
- CAP (Corrective Action Plan) = Cessation / Prävention ✅ vollständig
- Kein dedikatiertes Remedy-Modul (Art. 12 Logik fehlt)
- Grievance Mechanism (Art. 14) empfängt Beschwerden, aber kein strukturiertes Remedy-Case-Management dahinter
- Keine Verknüpfung: Grievance → Remedy Case → Abschluss mit Nachweis

---

## Stories

### CSDDD-004-S1 — Remedy Case erstellen & klassifizieren
**Beschreibung:** Als Compliance-Manager möchte ich tatsächlich eingetretene negative Auswirkungen als Remedy Case dokumentieren und klassifizieren, damit ich Art. 12 CSDDD gezielt bearbeiten kann.

**Akzeptanzkriterien:**
- [ ] Remedy Case kann manuell oder aus Grievance-Eingang erstellt werden
- [ ] Pflichtfelder: Titel, Beschreibung des Schadens, Datum des Eintritts, Betroffene (Anzahl, Typ: Arbeitnehmer / Gemeinschaft / Umwelt / Sonstige), CSDDD-Rechte-Referenz (Multi-Select aus CSDDDRight Enum)
- [ ] Begünstigten-Tracking: Betroffene Personen oder Gemeinschaften können namentlich oder pseudonymisiert erfasst werden (Name/Referenz, Art der Betroffenheit, zugesagte Kompensation, erhaltene Kompensation, Bestätigungsdatum) — ermöglicht Tracking ob Remedy tatsächlich bei den Begünstigten angekommen ist
- [ ] Remedy-Typ (Multi-Select): Entschädigung, Wiederherstellung, Entschuldigung/Rehabilitation, Restitution, Gesellschaftliche Entschädigung, Garantie der Nicht-Wiederholung
- [ ] "Fremde Impacts" — Mitarbeit (Art. 12 Abs. 5): Remedy Case kann als "Eigener Impact" oder "Mitverursachter Impact (gemeinsam mit Dritten)" klassifiziert werden; bei Mitverursachung: Feld für Mitverantwortliche (andere Unternehmen) und Koordinations-Notizen
- [ ] Schweregrad: basierend auf Art. 3 CSDDD-Skala (Schwere / Umkehrbarkeit / Anzahl Betroffene)
- [ ] `organization_id` PFLICHT-Filter

**Technische Analyse:**
- **Backend:** Neues Modell `RemedyCase` mit Feldern: `id`, `organization_id`, `title`, `description`, `incident_date`, `affected_count`, `affected_type` (Enum), `rights` (Array[CSDDDRight]), `remedy_types` (Array[Enum]), `severity_score`, `source_grievance_id` (nullable FK), `status` (Enum: Open/InProgress/Completed/Verified), `impact_causation` (Enum: Own/JointWithThirdParty), `co_responsible_parties` (Text, nullable)
- **Backend:** Neues Modell `RemedyBeneficiary` mit FK zu `RemedyCase`: `reference` (pseudonymisiert), `affected_type`, `promised_compensation`, `received_compensation`, `confirmation_date`
- **Backend:** Router `interfaces/api/routers/remedy_cases.py` mit CRUD
- **Backend:** Grievance-Router: neuer Endpoint `POST /grievances/{id}/create-remedy-case`
- **Frontend:** Neuer Bereich "Remedy Cases" in Compliance oder als Tab im Grievance-Bereich

**Abhängigkeiten:** Keine  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-004-S2 — Remedy-Maßnahmen-Planung
**Beschreibung:** Als Compliance-Manager möchte ich für jeden Remedy Case konkrete Maßnahmen definieren und ihren Fortschritt verfolgen.

**Akzeptanzkriterien:**
- [ ] Maßnahmen können einem Remedy Case hinzugefügt werden (analog CAP-Tasks)
- [ ] Felder je Maßnahme: Beschreibung, Verantwortlicher, Fälligkeit, Geschätzte Kosten (optional), Status (Todo/InProgress/Done)
- [ ] Unterscheidung zwischen internen Maßnahmen (EIOS-Nutzer) und externen Maßnahmen (z.B. Zahlung an Betroffene)
- [ ] Gesamtstatus des Remedy Case berechnet sich automatisch aus Maßnahmen-Status
- [ ] Maßnahmen-Änderungen werden in Audit Log protokolliert

**Technische Analyse:**
- **Backend:** Neues Modell `RemedyAction` mit FK zu `RemedyCase`
- **Backend:** Audit Log: bestehende Audit-Log-Logik auf RemedyCase anwenden
- **Frontend:** Maßnahmen-Liste im Remedy-Case-Detail mit Inline-Bearbeitung

**Abhängigkeiten:** CSDDD-004-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-004-S3 — Remedy-Nachweis & Abschluss
**Beschreibung:** Als Compliance-Manager möchte ich Nachweise für abgeschlossene Remedy-Maßnahmen hochladen und den Case formal abschließen, damit Prüfer die vollständige Dokumentation einsehen können.

**Akzeptanzkriterien:**
- [ ] Dokument-Upload (PDF, JPG, etc.) je Remedy Case (max. 50 MB)
- [ ] Nachweis-Typen: Zahlungsbeleg, Schriftliche Bestätigung Betroffener, Foto/Video, Gutachten, Drittnachweis
- [ ] Abschluss-Workflow: Compliance-Manager reicht ab → Manager/Admin genehmigt → Status = "Verified"
- [ ] KI-Agent darf Remedy Case NICHT abschließen oder genehmigen
- [ ] Abgeschlossene Cases erzeugen unveränderliche Abschluss-Snapshot-Datei (PDF-Export)
- [ ] Verknüpfung mit CSDDD-Jahresbericht: Remedy Cases fließen automatisch in Art. 16 Report ein

**Technische Analyse:**
- **Backend:** Endpoint `PATCH /remedy-cases/{id}/close` — nur Manager/Admin-Rolle
- **Backend:** Datei-Upload analog Evidence-Upload-Logik (bestehende Storage-Anbindung)
- **Backend:** Bei Abschluss: PDF-Snapshot via WeasyPrint/ReportLab generieren
- **Frontend:** Abschluss-Dialog mit Pflichtfeld "Abschluss-Begründung" + Upload

**Abhängigkeiten:** CSDDD-004-S2  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-004-S4 — Remedy-Bericht für Jahresbericht
**Beschreibung:** Als Compliance-Manager möchte ich alle Remedy Cases des Berichtsjahres in einem strukturierten Report zusammenfassen, der direkt in den CSDDD-Jahresbericht integriert werden kann.

**Akzeptanzkriterien:**
- [ ] Report enthält: Anzahl Remedy Cases, Schweregrad-Verteilung, Betroffene gesamt, Remedy-Typen-Verteilung
- [ ] Einzelauflistung aller verifizierten Cases mit: Titel, Datum, Maßnahmen, Status
- [ ] Noch offene Cases werden separat ausgewiesen mit Begründung warum offen
- [ ] Format: Strukturierter Abschnitt der direkt in den CSDDD-Jahresbericht (Art. 16) eingefügt werden kann
- [ ] Export: PDF + CSV

**Technische Analyse:**
- **Backend:** Neuer Endpoint `GET /reports/remedy-summary?year=2025` — aggregiert aus `RemedyCase`
- **Frontend:** Neuer Tab in Reports-Bereich: "Remedy & Wiedergutmachung"
- **Integration:** Bestehender `build_csddd_report()` in `csddd_engine.py` um Remedy-Abschnitt erweitern

**Abhängigkeiten:** CSDDD-004-S1, CSDDD-004-S3  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] KI-Agent-Sperre auf Close/Verify-Endpoint verifiziert
- [ ] Dokument-Upload ohne Schadcode-Bypass (Mime-Type Validierung)
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 12 — Remedy Case Management"
- [ ] Changelog ergänzt
