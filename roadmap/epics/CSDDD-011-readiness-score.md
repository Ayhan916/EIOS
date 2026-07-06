# CSDDD-011 — CSDDD Readiness Score

**CSDDD-Referenz:** Art. 7–16 (übergreifend) — Eigene Innovation  
**Phase:** 3 — Innovation & Differenzierung  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~8 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Kein einzelner CSDDD-Artikel fordert einen "Readiness Score" — dieser ist eine **eigene Innovation** die EIOS von Wettbewerbern differenziert. Der Score gibt Unternehmen eine einzige, verständliche Zahl (0–100) die zeigt wie gut sie für eine CSDDD-Behördenprüfung aufgestellt sind. Vergleichbar mit M43-Score für individuelle Risiken, aber auf Organisations-Ebene für CSDDD-Compliance.

**Differenzierungspotential:**
- Direkte Zertifizierungs-Analogie: "Ihr CSDDD Readiness Score: 72/100 — Prüfungsbereit ab Score 80"
- Benchmarking innerhalb der Branche (anonym, optional)
- Fortschrittsanzeige über Zeit

---

## Stories

### CSDDD-011-S1 — Score-Berechnungsmodell definieren
**Beschreibung:** Als Produktverantwortlicher möchte ich ein deterministisches und auditables Berechnungsmodell für den CSDDD Readiness Score definieren, damit der Score valide und erklärbar ist.

**Akzeptanzkriterien:**
- [ ] Scorecard-Modell mit 12 Dimensionen (je 0–100, gewichtet):
  1. DD-Politik vorhanden & aktuell (Art. 7) — Gewicht 10%
  2. Scoping Study aktuell (Art. 8) — Gewicht 8%
  3. Risikoidentifikation abgedeckt (Art. 8) — Gewicht 10%
  4. Priorisierung dokumentiert (Art. 9) — Gewicht 7%
  5. Präventionsmaßnahmen implementiert (Art. 10) — Gewicht 10%
  6. CAP-Abschlussquote (Art. 11) — Gewicht 8%
  7. Remedy Cases gemanagt (Art. 12) — Gewicht 8%
  8. Stakeholder-Konsultationen (Art. 13) — Gewicht 8%
  9. Grievance-Mechanismus aktiv (Art. 14) — Gewicht 7%
  10. Wirksamkeitsmonitoring (Art. 15) — Gewicht 8%
  11. Jahresbericht vorhanden (Art. 16) — Gewicht 8%
  12. Contractual Assurance abgedeckt (Art. 10) — Gewicht 8%
- [ ] Score ist deterministisch: gleiche Inputdaten = gleicher Score
- [ ] Jede Dimension erläutert welche Datenpunkte sie berechnet
- [ ] Gewichtungen konfigurierbar (Admin-Einstellung)

**Technische Analyse:**
- **Backend:** Service `application/scoring/csddd_readiness_scorer.py` — Pure Function
- **Backend:** Inputs: alle EIOS-Entitäten der Organisation (Policy, ScopingStudy, RiskAssessment, etc.)
- **Backend:** Output: `ReadinessScore` Objekt mit `total`, `dimensions[]`, `calculation_date`, `data_snapshot_hash`
- **Wichtig:** `data_snapshot_hash` — SHA-256 über Inputdaten → Score ist auditierbar und wiederholbar

**Abhängigkeiten:** Alle Phase-1/2 Epics sollten zuerst implementiert sein damit die Dimensionen befüllt werden können  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-011-S2 — Score-Dashboard & Visualisierung
**Beschreibung:** Als Compliance-Manager möchte ich meinen CSDDD Readiness Score auf einem visuellen Dashboard sehen, mit Drilldown auf jede Dimension und klaren Handlungsempfehlungen.

**Akzeptanzkriterien:**
- [ ] Haupt-KPI: Große Score-Anzeige (z.B. "78/100") mit Farbring (rot/gelb/grün)
- [ ] Status-Labels: 0–59 = "Nachholbedarf", 60–79 = "Auf Kurs", 80–94 = "Prüfungsbereit", 95–100 = "Exzellent"
- [ ] Radar-Chart: 12 Dimensionen als Spinnennetz-Diagramm — Stärken und Schwächen sofort sichtbar
- [ ] Detailtabelle: Je Dimension: Score, Beschreibung, Fehlende Maßnahmen, Link zur Maßnahmen-Seite
- [ ] Score-Verlauf: Liniendiagramm Score über Zeit (monatliche Snapshots)
- [ ] "Quick Wins" Sektion: Top-3 Maßnahmen die den Score am schnellsten verbessern würden

**Technische Analyse:**
- **Backend:** Endpoint `GET /readiness/score` — berechnet aktuellen Score und gibt mit Dimensionen zurück
- **Backend:** Endpoint `GET /readiness/history` — Verlauf der letzten 12 Monate
- **Backend:** Täglicher Background-Job: Score berechnen und als Snapshot speichern
- **Frontend:** Neues Dashboard-Modul "CSDDD Readiness" (prominent platziert)
- **Frontend:** Recharts Radar-Chart + Liniendiagramm

**Abhängigkeiten:** CSDDD-011-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-011-S3 — Score-Zertifikat & Bericht
**Beschreibung:** Als Management möchte ich einen formellen "CSDDD Readiness Report" exportieren können, der unseren Score mit Begründung dokumentiert — für Board-Präsentationen und Stakeholder.

**Akzeptanzkriterien:**
- [ ] PDF-Export: EIOS-Readiness-Certificate mit aktuellem Score, Datum, Organisation, allen Dimensionen
- [ ] Disclaimer: "Dieser Score basiert auf Selbstauskunft in EIOS. Er ersetzt keine Rechts- oder Compliance-Beratung."
- [ ] Score-Zertifikat kann per Link geteilt werden (öffentlich zugänglicher Link mit Ablaufdatum, nur Score + Datum — keine internen Detaildaten)
- [ ] Benachrichtigung an Management wenn Score unter konfigurierbaren Schwellenwert fällt (z.B. < 70)

**Technische Analyse:**
- **Backend:** PDF-Generierung mit EIOS-Branding
- **Backend:** Öffentlicher Share-Link: signierter Token, enthält nur Score + Datum + Org-Name, kein Drilldown
- **Frontend:** "Zertifikat teilen" Button mit kopierbarem Link + QR-Code

**Abhängigkeiten:** CSDDD-011-S1, CSDDD-011-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 3 Stories implementiert und tested
- [ ] Score deterministisch: Unit-Test mit fixen Inputs produziert immer gleichen Score
- [ ] `data_snapshot_hash` verifiziert Reproduzierbarkeit
- [ ] Disclaimer auf allen Score-Darstellungen und -Exporten
- [ ] Öffentlicher Share-Link enthält KEINE internen Compliance-Details
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Readiness Score — Methodik"
- [ ] Changelog ergänzt
