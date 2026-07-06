# CSDDD-012 — Impact Severity Calculator

**CSDDD-Referenz:** Art. 3 lit. d — Definition "Schwere" / Art. 8 Abs. 7 — Priorisierung nach Schwere  
**Phase:** 3 — Innovation & Differenzierung  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~7 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 3 CSDDD definiert "Schwere" einer negativen Auswirkung anhand von drei Parametern:
1. **Severity** (Schweregrad): Wie gravierend ist die Auswirkung?
2. **Scale** (Ausmaß): Wie viele Menschen / welche Fläche ist betroffen?
3. **Irremediability** (Unumkehrbarkeit): Wie schwer ist die Auswirkung rückgängig zu machen?

Aktuell werden Risiken in EIOS mit einem Gesamt-Score bewertet aber ohne diese drei Dimensionen explizit und systematisch zu erfassen. Ein dedizierter Calculator macht die Schwere-Bewertung CSDDD-konform und transparent.

---

## Stories

### CSDDD-012-S1 — Severity/Scale/Irremediability Eingabemodell
**Beschreibung:** Als Compliance-Manager möchte ich Risiken und Findings nach den drei CSDDD-Schwere-Dimensionen bewerten, damit meine Priorisierungsentscheidungen nachvollziehbar CSDDD Art. 3/8 entsprechen.

**Akzeptanzkriterien:**
- [ ] Für jedes Risk Assessment: Neuer Abschnitt "CSDDD Schwere-Bewertung"
- [ ] Drei Skalen je 1–5:
  - **Severity:** 1=Minimal, 2=Gering, 3=Moderat, 4=Erheblich, 5=Kritisch — mit Beispielen je Wert
  - **Scale:** 1=<10 Personen, 2=10-100, 3=100-1000, 4=1000-10000, 5=>10000 oder Ökosystem
  - **Irremediability:** 1=Vollständig reversibel, 2=Größtenteils reversibel, 3=Teilweise reversibel, 4=Schwer reversibel, 5=Irreversibel
- [ ] Bewertung optional (kann leer bleiben für Rückwärtskompatibilität), aber mit Hinweis "CSDDD Art. 8: Schwere-Bewertung empfohlen"
- [ ] Felder in bestehende Risk-Assessment-Formulare integrieren (kein eigenes neues Formular)

**Technische Analyse:**
- **Backend:** Migration: neue Felder in `risk_assessments` Tabelle: `csddd_severity`, `csddd_scale`, `csddd_irremediability` (Integer, nullable)
- **Backend:** Migrationsskript erstellen (NICHT ausführen)
- **Frontend:** Drei Slider oder Dropdown-Felder im bestehenden Risk-Assessment-Formular

**Abhängigkeiten:** Keine  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-012-S2 — Schwere-Score Berechnung & Visualisierung
**Beschreibung:** Als Compliance-Manager möchte ich aus den drei Dimensionen einen kombinierten Schwere-Score berechnet bekommen und diesen visualisiert sehen.

**Akzeptanzkriterien:**
- [ ] Kombinierter Schwere-Score: `(severity * 0.4) + (scale * 0.3) + (irremediability * 0.3)` — gewichtet, 1–5 Skala
- [ ] Score farbcodiert: 1.0–2.0 = Grün, 2.1–3.5 = Gelb, 3.6–4.5 = Orange, 4.6–5.0 = Rot
- [ ] Heatmap: Alle Risk Assessments auf 2D-Matrix (Severity × Scale), farbcodiert nach Irremediability
- [ ] Hover-Tooltip: Einzelwerte + Berechnung transparent
- [ ] Score-Gewichtung konfigurierbar (Admin-Einstellung, Änderungen in Audit Log)
- [ ] Deterministische Berechnung, kein LLM-Scoring

**Technische Analyse:**
- **Backend:** Service `application/scoring/impact_severity_calculator.py` — Pure Function
- **Backend:** Endpoint `GET /risk-assessments/{id}/impact-severity`
- **Backend:** Bulk-Endpoint: `GET /risk-assessments/impact-severity-matrix` — alle RAs der Org
- **Frontend:** Neue Heatmap-Komponente in Risk-Übersicht

**Abhängigkeiten:** CSDDD-012-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-012-S3 — Priorisierungsempfehlung & Export
**Beschreibung:** Als Compliance-Manager möchte ich basierend auf dem Impact-Severity-Score eine Priorisierungsempfehlung erhalten und diese für Prüfer exportieren können.

**Akzeptanzkriterien:**
- [ ] Automatische Priorisierungsempfehlung: Score > 3.5 → "Sofortiger Handlungsbedarf", 2.5–3.5 → "Planmäßiger Handlungsbedarf", < 2.5 → "Routinemäßige Überwachung"
- [ ] Empfehlung als Textbaustein in Risk-Details sichtbar mit Begründung
- [ ] Manuelle Überschreibung möglich (Pflicht-Begründung + Audit Trail)
- [ ] Export: Priorisierungsliste aller RAs sortiert nach Schwere-Score als PDF/CSV
- [ ] Integration in CSDDD-Jahresbericht: Top-10 schwerwiegendste Risiken automatisch einfließen

**Technische Analyse:**
- **Backend:** Priorisierungslogik in `impact_severity_calculator.py`
- **Backend:** Manuelle-Überschreibungs-Modell in DB (wer, wann, warum)
- **Frontend:** Badge in Risk-Tabelle: "Sofortiger Handlungsbedarf" etc.
- **Backend:** `build_csddd_report()` Erweiterung

**Abhängigkeiten:** CSDDD-012-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 3 Stories implementiert und tested
- [ ] Berechnungslogik deterministisch + Unit-tested mit Grenzwerten
- [ ] Manuelle Überschreibungen vollständig im Audit Log
- [ ] Migrationsskript erstellt (NICHT ausgeführt)
- [ ] Bestehende Risk-Tests weiterhin grün (nullable Felder = keine Breaking Changes)
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Impact Severity Calculator — Methodik"
- [ ] Changelog ergänzt
