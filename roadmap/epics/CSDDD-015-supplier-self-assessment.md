# CSDDD-015 — Supplier Self-Assessment CSDDD

**CSDDD-Referenz:** Art. 10 Abs. 2 lit. a — Fragebögen / Selbstauskunft von Lieferanten  
**Phase:** 3 — Innovation & Differenzierung  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~8 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 10 Abs. 2 lit. a CSDDD erlaubt den Einsatz von **Selbstauskunfts-Fragebögen** als Präventionsmaßnahme für mittelbare Geschäftspartner (Tier 2+). Ein strukturierter, CSDDD-konformer Fragenkatalog der direkt an Lieferanten versendet werden kann ist ein erheblicher Prozessvorteil.

**Differenzierungspotential:**
- CSDDD-spezifischer Fragenkatalog (über allgemeine ESG-Fragebögen hinaus)
- Automatische Gap-Erkennung aus Antworten
- Lieferant-Portal für einfache Einreichung ohne EIOS-Login

---

## Stories

### CSDDD-015-S1 — CSDDD-Fragebogen-Builder
**Beschreibung:** Als Compliance-Manager möchte ich CSDDD-spezifische Selbstauskunfts-Fragebögen für Lieferanten erstellen und konfigurieren, damit ich Art. 10 Abs. 2 lit. a systematisch umsetze.

**Akzeptanzkriterien:**
- [ ] Vordefinierter CSDDD-Fragenkatalog mit mind. 25 Fragen — CSDDD-Artikel-referenziert:
  - Section A: Unternehmensstruktur (Art. 7)
  - Section B: Menschenrechte-Policies (Art. 10 + Anhang I)
  - Section C: Umweltmaßnahmen (Art. 10 + Anhang II)
  - Section D: Beschwerdeverfahren (Art. 14)
  - Section E: Sublieferanten (Kaskadenklausel Art. 10 Abs. 2 lit. b)
- [ ] Fragebogen-Builder: Compliance-Manager kann Fragen aktivieren/deaktivieren, Reihenfolge ändern, eigene Fragen hinzufügen
- [ ] Fragetypen: Ja/Nein, Multiple Choice, Freitext, Datei-Upload, Skala 1–5
- [ ] Vorlage speicherbar und für mehrere Lieferanten wiederverwendbar
- [ ] Automatische Gewichtung: Jede Frage hat CSDDD-Artikel-Bezug → für spätere Gap-Analyse

**Technische Analyse:**
- **Backend:** Modelle `AssessmentTemplate` + `AssessmentQuestion` mit CSDDD-Artikel-FK
- **Backend:** Seed-Daten: 25 Standard-Fragen bei Erstinstallation
- **Frontend:** Neuer Bereich "Fragebögen" in Supplier-Modul mit Drag-and-Drop-Builder

**Abhängigkeiten:** Keine  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-015-S2 — Lieferanten-Portal Fragebogen-Einreichung
**Beschreibung:** Als Lieferant möchte ich den Fragebogen über ein einfaches Web-Portal ausfüllen ohne einen EIOS-Account zu benötigen, damit die Teilnahmeschwelle gering ist.

**Akzeptanzkriterien:**
- [ ] Einzigartiger, zeitlich begrenzter Link (JWT-Token, 30 Tage gültig) wird an Lieferanten-E-Mail versendet
- [ ] Portal-Seite: `/supplier/assessment/{token}` — außerhalb des Auth-Flows
- [ ] Lieferant sieht: Unternehmensname des Auftraggebers, Fragebogen-Titel, Frist, Fragen
- [ ] Fortschritt wird gespeichert (Lieferant kann unterbrechen und fortfahren)
- [ ] Einreichung mit Bestätigungs-Checkbox: "Ich bestätige die Richtigkeit der Angaben"
- [ ] Nach Einreichung: Dankes-Seite + Referenzcode
- [ ] submitted_by_email und IP-Adresse NIEMALS in API-Response (analog Grievance-Pattern)
- [ ] Rate-Limiting: max. 10 Einreichungen pro IP pro Stunde

**Technische Analyse:**
- **Backend:** Endpoint `GET /supplier-assessment/{token}` — gibt Fragebogen-Struktur zurück (kein Auth)
- **Backend:** Endpoint `POST /supplier-assessment/{token}/submit` — speichert Antworten
- **Backend:** `submitted_by_email` nur intern sichtbar, nie in API-Response
- **Backend:** Token = JWT mit `assessment_id`, `supplier_id`, `expires_at`
- **Frontend:** Neues öffentliches Route-Segment `/supplier/assessment/[token]/page.tsx`

**Abhängigkeiten:** CSDDD-015-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-015-S3 — Automatische Gap-Analyse aus Antworten
**Beschreibung:** Als Compliance-Manager möchte ich nach Eingang eines ausgefüllten Fragebogens automatisch eine Gap-Analyse sehen, damit ich schnell erkenne wo Handlungsbedarf beim Lieferanten besteht.

**Akzeptanzkriterien:**
- [ ] Automatische Auswertung nach Einreichung: Antworten werden gegen CSDDD-Mindestanforderungen geprüft
- [ ] Gap-Report je Lieferant: Welche CSDDD-Anforderungen sind laut Selbstauskunft nicht erfüllt?
- [ ] Traffic-Light-Bewertung je Sektion (A–E): Rot/Gelb/Grün
- [ ] Empfohlene Folgemaßnahmen: Automatisch generierte Aktionspunkte je Gap (deterministisch, nicht KI-basiert)
- [ ] Gap-Report kann als Basis für CAP genutzt werden: "CAP aus Gap-Report erstellen" Button
- [ ] Compliance-Manager wird per E-Mail benachrichtigt wenn Fragebogen eingereicht wurde

**Technische Analyse:**
- **Backend:** Service `application/supplier_assessment/gap_analyzer.py` — Pure Function
- **Backend:** Regelwerk: `{"question_id": "Q5", "expected_answer": "yes", "csddd_article": "Art.14", "gap_weight": 3}` — Konfigurationsdatei
- **Backend:** Endpoint `GET /supplier-assessments/{id}/gap-report`
- **Frontend:** Gap-Report-Ansicht im Supplier-Detail mit Traffic-Lights und Aktionspunkten

**Abhängigkeiten:** CSDDD-015-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 3 Stories implementiert und tested
- [ ] `submitted_by_email` und IP NIEMALS in API-Response
- [ ] Token-Ablauf getestet: abgelaufener Token → 401 mit klarer Fehlermeldung
- [ ] Gap-Analyse deterministisch + Unit-tested
- [ ] Rate-Limiting auf öffentliche Endpoints
- [ ] `organization_id` auf allen internen Queries
- [ ] Confluence-Seite erstellt: "Supplier Self-Assessment CSDDD — Leitfaden"
- [ ] Changelog ergänzt
