# CSDDD-001 — Stakeholder Engagement Module

**CSDDD-Referenz:** Art. 13 — Einbeziehung von Interessenträgern  
**Phase:** 1 — Kritische Compliance-Lücken  
**Priorität:** HOCH  
**Aktueller Stand:** 20% → Ziel: 100%  
**Gesamtaufwand:** ~13 Story Points  
**Status:** 🟢 DONE  

---

## Kontext & Anforderung

Art. 13 CSDDD verpflichtet Unternehmen, betroffene Interessenträger (Arbeitnehmer, Gewerkschaften, Zivilgesellschaft, Lieferantengemeinschaften) in die Due-Diligence-Prozesse einzubeziehen — sowohl bei der Identifikation von Risiken als auch bei der Entwicklung von Maßnahmen.

**Aktueller EIOS-Stand:**
- Grievance Mechanism (Art. 14) ✅ vollständig implementiert
- Kein strukturierter Prozess für die *aktive* Einbeziehung von Stakeholdern
- Keine Dokumentation von Konsultationen und deren Ergebnissen
- Keine Stakeholder-Datenbank / Registrierung von betroffenen Parteien

---

## Stories

### CSDDD-001-S1 — Stakeholder-Registrierung
**Beschreibung:** Als Compliance-Manager möchte ich betroffene Interessenträger im System erfassen und kategorisieren, damit der Nachweis der Einbeziehung dokumentiert ist.

**Akzeptanzkriterien:**
- [ ] Stakeholder kann mit Name, Typ (Arbeitnehmer / NGO / Gewerkschaft / Lieferantengemeinschaft / Behörde / Sonstige), Kontaktdaten und Sprache angelegt werden
- [ ] Jeder Stakeholder ist einer oder mehreren Aktivitätsketten / Regionen / Risikothemen zugeordnet
- [ ] Stakeholder-Liste ist filterbar nach Typ, Region, Aktivitätskette
- [ ] Pflichtfeld: Begründung warum dieser Stakeholder als "betroffen" klassifiziert ist (Art. 13 Abs. 1 Anforderung)
- [ ] `organization_id` PFLICHT-Filter auf allen Queries

**Technische Analyse:**
- **Backend:** Neues Modell `Stakeholder` in `domain/models/`, neue Tabelle `stakeholders` mit Feldern: `id`, `organization_id`, `name`, `type` (Enum), `contact_email`, `language`, `activity_chain_ids` (Array), `justification`, `created_at`
- **Backend:** Router `interfaces/api/routers/stakeholders.py` mit CRUD-Endpoints
- **Frontend:** Neue Seite `/stakeholders` mit Tabelle + "Stakeholder hinzufügen"-Modal
- **Migration:** Alembic Migration erforderlich

**Abhängigkeiten:** Keine  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-001-S2 — Konsultations-Protokoll
**Beschreibung:** Als Compliance-Manager möchte ich Konsultationen mit Stakeholdern dokumentieren (Datum, Teilnehmer, Thema, Ergebnis), damit ich den Nachweis der aktiven Einbeziehung führen kann.

**Akzeptanzkriterien:**
- [ ] Konsultation kann einem oder mehreren Stakeholdern zugeordnet werden
- [ ] Felder: Datum, Format (Meeting / Workshop / Fragebogen / Audit / Sonstiges), Themen (Multi-Select aus Risikokategorien), Beschreibung, Ergebnis/Erkenntnisse, Anhänge (Upload)
- [ ] Pflichtfeld "Barrieren zur Teilnahme" (Art. 13 Abs. 1 Anforderung): dokumentiert ob Stakeholder auf Hindernisse gestoßen sind (Sprache / Zugang / Ressourcen / Repressalien-Angst) und wie diese adressiert wurden — auch "keine Barrieren" muss explizit ausgewählt werden
- [ ] Konsultation kann mit einem DD-Prozess (Risk, Finding, CAP) verknüpft werden
- [ ] Automatische Benachrichtigung wenn > 12 Monate keine Konsultation für einen Stakeholder stattgefunden hat
- [ ] Export als PDF mit CSDDD-Konformitätsvermerk

**Technische Analyse:**
- **Backend:** Neues Modell `StakeholderConsultation` mit FK zu `Stakeholder` und optionalem FK zu `RiskAssessment` / `Finding` / `CorrectiveActionPlan`
- **Backend:** Router `interfaces/api/routers/stakeholder_consultations.py`
- **Frontend:** Tab in Stakeholder-Detailseite + Protokoll-Formular
- **Frontend:** Dashboard-Widget: "Stakeholder ohne Konsultation > 12 Monate"

**Abhängigkeiten:** CSDDD-001-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-001-S3 — Stakeholder-Feedback-Eingang
**Beschreibung:** Als Stakeholder möchte ich strukturiertes Feedback zu einem laufenden DD-Prozess einreichen, damit meine Perspektive in die Risikoanalyse einfließt.

**Akzeptanzkriterien:**
- [ ] Öffentliches Feedback-Formular (ohne Login) über einzigartigen Link je Konsultation
- [ ] Felder: Risikoeinschätzung, betroffene Rechte (Multi-Select aus CSDDDRight Enum), Beschreibung, Kontaktfreigabe (optional, DSGVO-konform)
- [ ] Eingegangenes Feedback wird im Konsultationsprotokoll angehängt
- [ ] submitted_by_email wird NIEMALS in API-Responses zurückgegeben (analog Grievance-Pattern)
- [ ] Rate-Limiting: max. 5 Einreichungen pro IP / Stunde

**Technische Analyse:**
- **Backend:** Endpoint `POST /stakeholders/consultations/{token}/feedback` — öffentlich, kein Auth
- **Backend:** Anonymisierungs-Schema: feedback gespeichert, E-Mail nur intern sichtbar für Admin-Rolle
- **Frontend:** Separates Formular `/feedback/{token}` — außerhalb des Auth-Flows
- **Security:** CSRF-Token, Honeypot-Feld, IP-Rate-Limiting via middleware

**Abhängigkeiten:** CSDDD-001-S2  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-001-S4 — Einbeziehungsnachweis-Report
**Beschreibung:** Als Compliance-Manager möchte ich einen strukturierten Nachweis der Stakeholder-Einbeziehung für den Jahresbericht generieren.

**Akzeptanzkriterien:**
- [ ] Report listet alle Konsultationen des Berichtszeitraums nach Stakeholder-Typ
- [ ] Report zeigt welche Themen konsultiert wurden und was die Erkenntnisse waren
- [ ] Abgleich: Welche Risikothemen wurden ohne Stakeholder-Input bewertet? (Gap-Indikator)
- [ ] Export: PDF + CSV
- [ ] CSDDD Art. 13 Abs. 2 Nachweis: Dokumentation wie Stakeholder-Input die Maßnahmen beeinflusst hat

**Technische Analyse:**
- **Backend:** Neuer Endpoint `GET /reports/stakeholder-engagement` — aggregiert Konsultationen, Stakeholder, verknüpfte DD-Aktivitäten
- **Frontend:** Neuer Report-Tab im bestehenden Reports-Bereich
- **Template:** Ähnlich wie bestehende CSDDD/LkSG Report-Struktur

**Abhängigkeiten:** CSDDD-001-S1, CSDDD-001-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-001-S5 — Stakeholder-Map (Visualisierung)
**Beschreibung:** Als Management möchte ich eine visuelle Übersicht aller Stakeholder-Beziehungen und deren Aktivitätsketten-Zuordnung, um die Abdeckung auf einen Blick zu beurteilen.

**Akzeptanzkriterien:**
- [ ] Grafische Darstellung: Stakeholder gruppiert nach Typ, farbcodiert nach letzter Konsultation (grün/gelb/rot)
- [ ] Tooltip zeigt: Name, letztes Konsultationsdatum, offene Feedbacks
- [ ] Klick auf Stakeholder öffnet Detailseite
- [ ] Filter: Region, Aktivitätskette, Risikobereich

**Technische Analyse:**
- **Frontend:** Neue Visualisierungs-Komponente mit D3.js oder Recharts (je nach vorhandener Dependency)
- **Backend:** Endpoint `GET /stakeholders/map-data` liefert aggregierte Daten für Visualisierung
- **Performance:** Daten gecacht (5 min TTL), nicht pro-Request berechnet

**Abhängigkeiten:** CSDDD-001-S1, CSDDD-001-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 5 Stories implementiert und tested
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] Unit Tests Backend (pytest) — alle neu Routen abgedeckt
- [ ] Stakeholder-Daten niemals ohne `organization_id`-Filter
- [ ] `submitted_by_email` / `contact_email` nie in API-Response ohne Admin-Rolle
- [ ] Confluence-Seite erstellt: "CSDDD Art. 13 — Stakeholder Engagement"
- [ ] Changelog ergänzt
