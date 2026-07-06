# CSDDD-013 — Board Sign-off Trail

**CSDDD-Referenz:** Art. 22 — Pflichten der Unternehmensleitung  
**Phase:** 3 — Innovation & Differenzierung  
**Priorität:** MITTEL  
**Aktueller Stand:** 80% → Ziel: 100%  
**Gesamtaufwand:** ~9 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 22 CSDDD verpflichtet die **Unternehmensleitung** (Vorstand/Geschäftsführung), die DD-Strategie zu überwachen und in strategischen Entscheidungen zu berücksichtigen. Variable Vergütung muss an DD-Umsetzung geknüpft werden (Art. 22 Abs. 2 — optionaler Mechanismus). Konkret:
- Unternehmensleitung *muss* DD-Berichte genehmigen
- Unternehmensleitung *muss* over-reachende Findings eskaliert bekommen
- Vorstandsbeschlüsse zu DD-Strategie müssen dokumentiert sein

**Aktueller EIOS-Stand:**
- Approvals-Mechanismus in Auditor-Bereich ✅ vorhanden
- Kein dediziertes "Board-Level" Genehmigungsmodul mit eigenem Audit Trail
- Kein Mechanismus für Vorstandsbeschlüsse zu DD-Strategie
- Keine DD-KPI-Verknüpfung mit Vergütungsrahmen

---

## Stories

### CSDDD-013-S1 — Board-Genehmigungsworkflow für DD-Berichte
**Beschreibung:** Als Compliance-Manager möchte ich CSDDD-Jahresberichte und Scoping Studies zur Genehmigung an die Unternehmensleitung einreichen, damit Art. 22 CSDDD nachweislich erfüllt ist.

**Akzeptanzkriterien:**
- [ ] Neue Rolle: "Executive" — kann Berichte genehmigen (aber keine operativen Daten bearbeiten)
- [ ] Genehmigungsanfrage: Compliance-Manager schickt Dokument zur Genehmigung an Executive-Rolle
- [ ] Executive erhält E-Mail mit direktem Link zum Dokument + "Genehmigen" / "Kommentar anfordern" Buttons
- [ ] Genehmigung speichert: Genehmigende Person, Zeitstempel, IP-Hash (DSGVO), Dokumenten-Hash (SHA-256)
- [ ] Genehmigte Dokumente sind unveränderlich (Status = "Board-Approved" = locked)
- [ ] KI-Agent darf NIEMALS im Namen von Executive genehmigen

**Technische Analyse:**
- **Backend:** Neue Rolle `EXECUTIVE` in Berechtigungssystem
- **Backend:** Modell `BoardApproval` mit Feldern: `document_type`, `document_id`, `approved_by`, `approved_at`, `ip_hash`, `document_hash`
- **Backend:** Endpoint `POST /board-approvals` — nur für EXECUTIVE-Rolle
- **Backend:** E-Mail-Benachrichtigung mit Magic-Link (zeitlich begrenzt)
- **Frontend:** Neuer Board-Approval-Tab in Reports/Governance-Bereich

**Abhängigkeiten:** CSDDD-002-S1 (DD-Politik), CSDDD-008-S3 (Scoping Study)  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-013-S2 — Vorstandsbeschluss-Dokumentation
**Beschreibung:** Als Compliance-Manager möchte ich Vorstandsbeschlüsse zur DD-Strategie im System dokumentieren, damit ich Art. 22 CSDDD nachweisen kann dass die Unternehmensleitung aktiv in die DD-Steuerung eingebunden ist.

**Akzeptanzkriterien:**
- [ ] Neue Entität `BoardResolution` mit Feldern: Datum, Titel, Beschlusstext, Beschluss-Typ (DD-Strategie / Policy-Änderung / Budget-Freigabe / Risiko-Eskalation / Sonstiges), Protokoll-Upload (PDF optional), Status (Beschlossen/In Umsetzung/Abgeschlossen)
- [ ] Board Resolutions sind an eine oder mehrere DD-Aktivitäten verknüpfbar (z.B. "Beschluss: Lieferant X wird trotz Risiko weiter geführt — Begründung: …")
- [ ] Unveränderlich nach Speicherung (nur Admin kann löschen, mit Löschbegründung)
- [ ] Jahresübersicht: Alle Board Resolutions des Berichtsjahres → für CSDDD-Jahresbericht

**Technische Analyse:**
- **Backend:** Neues Modell `BoardResolution`
- **Backend:** Endpoint: `POST /board-resolutions` — Executive + Admin Rolle
- **Frontend:** Neue Seite in Governance-Bereich: "Vorstandsbeschlüsse"

**Abhängigkeiten:** CSDDD-013-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-013-S3 — DD-KPI Vergütungs-Dashboard
**Beschreibung:** Als HR-Manager / Vorstand möchte ich die DD-Performance-KPIs der Unternehmensleitung verfolgen, die als Grundlage für variable Vergütungskomponenten dienen können (Art. 22 Abs. 2 CSDDD optionale Empfehlung).

**Akzeptanzkriterien:**
- [ ] Dashboard zeigt DD-KPIs: CSDDD Readiness Score (aus CSDDD-011), Offene Critical Risks, CAP-Abschlussquote, Stakeholder-Konsultations-Erfüllung
- [ ] KPIs für konfigurierbare Berichtszeiträume (Quartal, Halbjahr, Jahr)
- [ ] KPI-Zielsetzung: Zielwert kann pro KPI gesetzt werden → Ampelstatus (grün/gelb/rot)
- [ ] Export: KPI-Übersicht als PDF für Vergütungsausschuss oder Aufsichtsrat
- [ ] Disclaimer: "EIOS liefert Datenbasis. Vergütungsentscheidungen verbleiben bei der Unternehmensleitung."

**Technische Analyse:**
- **Backend:** Aggregations-Endpoint `GET /board/dd-kpi-dashboard?period=2025-Q1`
- **Backend:** Modell `DDKPITarget` für Zielwerte
- **Frontend:** Neues Board-Dashboard — zugänglich für Executive + Admin Rollen

**Abhängigkeiten:** CSDDD-011 (Readiness Score), CSDDD-013-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-013-S4 — Executive-Eskalationskanal
**Beschreibung:** Als Compliance-Manager möchte ich kritische Findings direkt an die Unternehmensleitung eskalieren können, damit Art. 22 Abs. 1 lit. c (Überwachungspflicht) erfüllt ist.

**Akzeptanzkriterien:**
- [ ] "An Vorstand eskalieren" Button bei Risk Assessments mit Score > 4.0 oder Remedy Cases Schwere > 4.0
- [ ] Eskalation erstellt automatisch eine Board Resolution Draft (CSDDD-013-S2) zur Prüfung
- [ ] Executive erhält E-Mail mit Kurzfassung: Risiko, Score, Empfehlung des Compliance-Teams
- [ ] Eskalation ohne Reaktion der Executive-Rolle nach 14 Tagen → automatische Erinnerung
- [ ] Eskalations-Log in Audit Trail

**Technische Analyse:**
- **Backend:** Endpoint `POST /escalations/to-board` — erstellt `BoardResolution` im Draft-Status + sendet E-Mail
- **Backend:** Background-Job: tägliche Prüfung auf unbeantwortete Eskalationen > 14 Tage
- **Frontend:** Eskalations-Button in Risk-Detail + Remedy-Case-Detail

**Abhängigkeiten:** CSDDD-013-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] EXECUTIVE-Rolle korrekt abgegrenzt: kann genehmigen aber keine operativen Daten bearbeiten
- [ ] KI-Agent-Sperre auf Board-Genehmigungsendpoint verifiziert
- [ ] `ip_hash` statt `ip_raw` für DSGVO
- [ ] Genehmigte Dokumente unveränderlich (Status + Hash gespeichert)
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 22 — Board Governance & Sign-off"
- [ ] Changelog ergänzt
