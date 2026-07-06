# CSDDD-007 — SME Support Tracker

**CSDDD-Referenz:** Art. 10 Abs. 2 lit. d — Unterstützung für KMU-Lieferanten  
**Phase:** 2 — Fehlende Module  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~7 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 10 Abs. 2 lit. d CSDDD verlangt, dass große Unternehmen ihren KMU-Lieferanten zielgerichtete und verhältnismäßige Unterstützung leisten, wenn diese die Anforderungen der DD-Politik allein nicht erfüllen können (finanzielle Ressourcen, technische Expertise). Diese Unterstützung muss dokumentiert werden.

**Aktueller EIOS-Stand:**
- Keine KMU-Kennzeichnung bei Lieferanten
- Kein Mechanismus zur Dokumentation von Unterstützungsleistungen
- Keine Verbindung zwischen KMU-Status und risikoadjustierter Prüftiefe

---

## Stories

### CSDDD-007-S1 — KMU-Kennzeichnung & Kategorisierung
**Beschreibung:** Als Compliance-Manager möchte ich Lieferanten nach Unternehmensgröße klassifizieren, damit ich KMU-spezifische Unterstützungspflichten korrekt zuordnen kann.

**Akzeptanzkriterien:**
- [ ] Lieferant-Modell erhält Felder: `employee_count`, `annual_revenue_eur`, `sme_status` (Enum: Micro/Small/Medium/Large — nach EU-Definition 2003/361/EG)
- [ ] Automatische SME-Klassifizierung: Micro (<10 MA, <2M€), Small (<50 MA, <10M€), Medium (<250 MA, <50M€), Large (≥250 oder ≥50M€)
- [ ] SME-Status sichtbar in Lieferanten-Listen und -Detailseiten (Badge)
- [ ] Filter in Lieferantenliste: "Nur KMU / Nur große Unternehmen"
- [ ] SME-Status in Risikobewertung berücksichtigt: KMU erhalten angepasste Fragebögen

**Technische Analyse:**
- **Backend:** Alembic Migration: neue Felder in `suppliers` Tabelle (Migrationsskript erstellen, NICHT ausführen)
- **Backend:** Service-Methode `classify_sme_status(employee_count, revenue)` — deterministisch, keine KI
- **Frontend:** Supplier-Formular: neue Felder + automatische Berechnung SME-Status
- **Frontend:** Badge-Komponente: "KMU" (grün) / "Großunternehmen" (blau)

**Abhängigkeiten:** Keine  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-007-S2 — Unterstützungsleistungs-Dokumentation
**Beschreibung:** Als Compliance-Manager möchte ich Unterstützungsleistungen für KMU-Lieferanten dokumentieren, damit ich Art. 10 Abs. 2 lit. d CSDDD nachweisen kann.

**Akzeptanzkriterien:**
- [ ] Pro KMU-Lieferant: Bereich "Unterstützungsleistungen"
- [ ] Leistungstypen: Schulung, Finanzielle Unterstützung, Technische Beratung, Gemeinsame Audit-Kosten, Tool-Zugang, Kapazitätsaufbau, Sonstiges
- [ ] Felder: Typ, Beschreibung, Datum, Geschätzter Wert (EUR, optional), Ansprechpartner, Status (Geplant/Durchgeführt/Abgebrochen)
- [ ] Nachweis-Upload möglich (z.B. Schulungsunterlagen, Rechnungen)
- [ ] Lieferant kann informiert werden per E-Mail wenn Unterstützung gewährt wurde

**Technische Analyse:**
- **Backend:** Neues Modell `SupportMeasure` mit FK zu `Supplier`, Felder wie oben
- **Backend:** Router `interfaces/api/routers/support_measures.py`
- **Frontend:** Neuer Tab in Supplier-Detailseite (nur sichtbar wenn `sme_status` = Micro/Small/Medium)

**Abhängigkeiten:** CSDDD-007-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-007-S3 — KMU-Unterstützungs-Report
**Beschreibung:** Als Compliance-Manager möchte ich einen jährlichen Überblick über alle erbrachten KMU-Unterstützungsleistungen generieren, damit dieser Abschnitt im CSDDD-Jahresbericht belegt ist.

**Akzeptanzkriterien:**
- [ ] Report zeigt: Anzahl unterstützter KMU, Gesamtwert der Leistungen, Aufteilung nach Leistungstyp
- [ ] Einzelauflistung aller Leistungen des Berichtszeitraums
- [ ] KMU die Unterstützung erhalten haben aber trotzdem keine Verbesserung zeigen: separater Hinweis
- [ ] Export: PDF + CSV
- [ ] Integration in `build_csddd_report()`: automatisch in Jahresbericht einfließen

**Technische Analyse:**
- **Backend:** Endpoint `GET /reports/sme-support?year=2025`
- **Backend:** `csddd_engine.py` Erweiterung um SME-Support-Abschnitt
- **Frontend:** Neuer Tab in Reports-Bereich

**Abhängigkeiten:** CSDDD-007-S1, CSDDD-007-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 3 Stories implementiert und tested
- [ ] SME-Klassifizierung deterministisch und ohne KI
- [ ] Migrationsskript erstellt (NICHT ausgeführt)
- [ ] `organization_id` auf allen Queries
- [ ] E-Mail-Benachrichtigung tested
- [ ] Confluence-Seite erstellt: "CSDDD Art. 10 — KMU-Unterstützung"
- [ ] Changelog ergänzt
