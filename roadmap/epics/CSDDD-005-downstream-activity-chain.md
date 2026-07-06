# CSDDD-005 — Downstream Activity Chain

**CSDDD-Referenz:** Art. 2 Abs. 1, Art. 3 — Geltungsbereich: Downstream-Aktivitätskette  
**Phase:** 2 — Fehlende Module  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~13 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

CSDDD 2024/1760 erweitert den Geltungsbereich gegenüber der ursprünglichen LkSG-Logik explizit auf die **Downstream-Aktivitätskette** (Art. 2 Abs. 1 lit. g: "Vertrieb, Transport, Lagerung und Entsorgung durch Geschäftspartner"). EIOS bildet aktuell nur Upstream (Lieferanten / Tier 1–N) ab — Downstream fehlt vollständig.

**Downstream-Akteure im Sinne CSDDD:**
- Distributoren / Händler
- Logistik- und Transportdienstleister
- Lizenznehmern (wenn Produktion involviert)
- Entsorgungsdienstleister

---

## Stories

### CSDDD-005-S1 — Downstream-Partner Datenmodell
**Beschreibung:** Als Compliance-Manager möchte ich Downstream-Geschäftspartner im System erfassen und von Upstream-Lieferanten klar unterscheiden, damit CSDDD Art. 2 vollständig abgebildet ist.

**Akzeptanzkriterien:**
- [ ] Bestehende Supplier-Entität erhält neues Pflichtfeld `chain_direction`: Enum `UPSTREAM` / `DOWNSTREAM` / `BOTH`
- [ ] Downstream-Partner können folgende Typen haben: Distributor, Logistik, Lizenznehmer, Entsorgung, Händler, Sonstige
- [ ] Downstream-Partner sind in Supplier-Listen und -Filtern filterbar
- [ ] Bestehende Upstream-Lieferanten bekommen Migrationsskript: `chain_direction = UPSTREAM` als Default
- [ ] Datenbankmigraton: Alembic Migration — NIEMALS automatisch ausführen, nur erstellen

**Technische Analyse:**
- **Backend:** Migration: `ALTER TABLE suppliers ADD COLUMN chain_direction VARCHAR(20) DEFAULT 'upstream'`
- **Backend:** `SupplierType` Enum erweitern oder neues `ChainDirection` Enum
- **Backend:** Alle bestehenden Supplier-Endpoints: `chain_direction` als optionaler Filterparameter
- **Frontend:** Supplier-Onboarding-Formular: neues Pflichtfeld "Kettenposition"
- **Frontend:** Supplier-Tabelle: neue Spalte mit Badge "Upstream" / "Downstream"

**Abhängigkeiten:** Keine  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-005-S2 — Downstream-Risikobewertung
**Beschreibung:** Als Compliance-Manager möchte ich Downstream-Partner in die Risikobewertung einbeziehen, damit auch Risiken beim Vertrieb, Transport und der Entsorgung meiner Produkte erfasst werden.

**Akzeptanzkriterien:**
- [ ] Bestehende RiskAssessment-Logik funktioniert auch für Downstream-Partner
- [ ] Downstream-spezifische Risikokategorien ergänzen: Entsorgungsrisiko, Transportrisiko, Vertriebsrisiko
- [ ] Downstream-Risiken im Risk-Dashboard separat auswertbar (eigener Filter "Downstream")
- [ ] Mapping: CSDDD-Rechte aus Anhang I die besonders Downstream-relevant sind (z.B. RIGHT_TO_SAFE_WORK für Transportarbeiter)
- [ ] Scoring-Algorithmus deterministisch und auditierbar (kein LLM-basiertes Scoring)

**Technische Analyse:**
- **Backend:** `RiskCategory` Enum um TRANSPORT, DISPOSAL, DISTRIBUTION erweitern
- **Backend:** `build_csddd_report()` in `csddd_engine.py` um Downstream-Abschnitt erweitern
- **Frontend:** Filter-Toggle "Upstream / Downstream / Beide" in Risk-Übersicht
- **Frontend:** Separate Statistik-Kachel: "Downstream-Risiken"

**Abhängigkeiten:** CSDDD-005-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-005-S3 — Kettenvisualisierung (Upstream + Downstream)
**Beschreibung:** Als Compliance-Manager möchte ich die vollständige Aktivitätskette (Upstream + Downstream) meines Unternehmens visuell darstellen, damit ich auf einen Blick sehe wo Risiken in welchem Kettenabschnitt liegen.

**Akzeptanzkriterien:**
- [ ] Visualisierung: Mein Unternehmen in der Mitte, Upstream-Lieferanten links, Downstream-Partner rechts
- [ ] Tier-Darstellung: Lieferanten nach Tier-Tiefe (Tier 1, 2, 3) angeordnet
- [ ] Farbcodierung nach Risiko-Score (grün/gelb/orange/rot)
- [ ] Klick auf Knoten öffnet Kurzinfo-Panel: Name, Typ, Score, letzte Bewertung
- [ ] Filter: Nur risikobehaftete Knoten anzeigen (Threshold konfigurierbar)
- [ ] Export: PNG/SVG für Jahresbericht

**Technische Analyse:**
- **Backend:** Neuer Endpoint `GET /supply-chain/visualization-data` — liefert Graph-Daten (Nodes + Edges mit Risk-Scores)
- **Frontend:** Neue Visualisierungs-Seite `/supply-chain` mit React Flow oder D3.js
- **Frontend:** Toolbar: Filter, Zoom, Export-Button
- **Performance:** Bei > 500 Knoten: nur Tier 1+2 rendern, Rest mit "Mehr anzeigen" expandierbar

**Abhängigkeiten:** CSDDD-005-S1, CSDDD-005-S2  
**Story Points:** 5  
**Status:** 🔴 TODO

---

### CSDDD-005-S4 — Downstream-Auditierungs-Workflow
**Beschreibung:** Als Compliance-Manager möchte ich Audits für Downstream-Partner durchführen können, analog zu Upstream-Lieferanten-Audits.

**Akzeptanzkriterien:**
- [ ] Bestehender Audit-Workflow (falls vorhanden) auch für Downstream-Partner nutzbar
- [ ] Falls kein Audit-Workflow existiert: Einfaches "Audit Record" Modell: Datum, Prüfer, Methode, Befund, Score
- [ ] Downstream-Audits im Monitoring-Dashboard sichtbar
- [ ] Automatische Erinnerung: Downstream-Partner ohne Audit in den letzten 24 Monaten

**Technische Analyse:**
- **Backend:** Bestehende Audit-Logik prüfen — ggf. `supplier_id` erlaubt bereits Downstream-Partner wenn Modell angepasst
- **Backend:** Notification-Job für überfällige Downstream-Audits
- **Frontend:** Filter-Ergänzung in Audit-Übersicht

**Abhängigkeiten:** CSDDD-005-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] Migrationsskript erstellt (NICHT ausgeführt)
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] Bestehende Upstream-Tests weiterhin grün
- [ ] Kettenvisualisierung mit > 100 Knoten getestet (Performance)
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 2/3 — Downstream Activity Chain"
- [ ] Changelog ergänzt
