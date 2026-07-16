# EIOS — Competitor Feature Roadmap
## Analyse: EcoVadis · Workiva · Sphera · Watershed · Greenomy · Diligent

> Erstellt: 2026-07-16  
> Basis: Marktanalyse ESG/Supply-Chain-Compliance-Software  
> Bereits implementiert (KAN-99): Confidence-Ampel ✅ · Export ✅ · Batch-Review-Queue ✅  
> Status-Legende: 🔴 Offen · 🟡 In Planung · 🟢 Done

---

## Priorität 1 — Kritisch (CSRD-Pflicht oder Core-Differenziator)

### C-01 — Materiality Matrix (Doppelte Wesentlichkeit)
**Wettbewerber:** EcoVadis, Greenomy, Workiva  
**Warum kritisch:** CSRD Artikel 3 schreibt eine Double-Materiality-Bewertung vor. Ohne dieses Feature ist EIOS für CSRD-pflichtige Unternehmen unvollständig.  
**Was fehlt:** Route `/materiality` — interaktive 2D-Matrix mit den Achsen "Finanzielle Auswirkung" (Outside-In) vs. "Auswirkung auf Gesellschaft/Umwelt" (Inside-Out). Themen als Punkte eintragbar, Schwellenwert-Linie, Export als PDF.  
**Aufwand:** ~3–4 Tage  
**Status:** 🔴 Offen

---

### C-02 — Disclosure Gap Tracker
**Wettbewerber:** Workiva (Kern-Feature), Greenomy (EU-Taxonomie + SFDR)  
**Warum kritisch:** Zeigt genau welche Datenpunkte für CSRD/GRI/TCFD fehlen — mit %-Fortschritt pro Standard. Enterprise-Kunden fragen das als erstes: "Wie weit sind wir?"  
**Was fehlt:** Seite `/disclosure/gap-tracker` — listet alle Pflichtangaben pro Framework, markiert welche bereits erfasst sind (aus bestehenden Metriken/Assessments), berechnet Vollständigkeit.  
**Aufwand:** ~2–3 Tage  
**Status:** 🔴 Offen

---

## Priorität 2 — Hoher Wert (Kundenbindung + Sales)

### C-03 — Peer Benchmarking / Branchenvergleich
**Wettbewerber:** EcoVadis (Herzstück), Sphera  
**Was fehlt:** `/benchmarks/industry` — Vergleich eigener ESG-Metriken (CO₂/Umsatz, Recyclingrate, Frauenanteil etc.) gegen Sektordurchschnitt und Top-10%-Grenze. Visualisierung als Gauge oder Balken. Datengrundlage: aggregierte anonymisierte Werte aus EIOS-Dokumenten-Pool.  
**Aufwand:** ~3–4 Tage (Backend: Aggregationslogik; Frontend: Chart-Komponente)  
**Status:** 🔴 Offen

---

### C-04 — Supplier Scorecard mit historischem Trend
**Wettbewerber:** EcoVadis, Sphera  
**Was fehlt:** Normierter 0–100 ESG-Score pro Lieferant (aus Assessment-Ergebnissen berechnet) mit Zeitreihe (Q1/Q2/Q3/Q4). Auf `/suppliers/[id]` als eigener Tab "Scorecard". Trend-Pfeil (↑↓) + Delta zum Vorquartal.  
**Aufwand:** ~2 Tage  
**Status:** 🔴 Offen

---

### C-05 — Task-Manager / Action Items
**Wettbewerber:** Workiva, Diligent  
**Was fehlt:** Zentrales internes Task-Board (`/tasks`) — Aufgaben mit Zuweisung an Teammitglieder, Fälligkeitsdatum, Status (Offen/In Bearbeitung/Erledigt), Verknüpfung mit Findings/Risks/Assessments. E-Mail-Benachrichtigung bei Fälligkeit. EIOS hat CAPs aber kein allgemeines Task-System.  
**Aufwand:** ~3–4 Tage (Backend: tasks-Tabelle + Notifications; Frontend: Board-View)  
**Status:** 🔴 Offen

---

## Priorität 3 — Mittelfristig

### C-06 — CDP/GRI-Daten-Import
**Wettbewerber:** Sphera, Workiva  
**Was fehlt:** Automatisches Einlesen öffentlicher Lieferantendaten aus der CDP-Registry und dem GRI-Nachhaltigkeitsbericht-Portal. Lieferantenprofil wird automatisch mit publizierten CO₂-Daten angereichert.  
**Aufwand:** ~3–5 Tage (API-Integration CDP + GRI)  
**Status:** 🔴 Offen

---

### C-07 — SFDR / PAI-Reporting
**Wettbewerber:** Greenomy (Spezialität), Novata (PE/VC)  
**Was fehlt:** Structured reporting für SFDR Principal Adverse Impacts (14 Pflicht-Indikatoren + 2 optionale je Kategorie). Relevant für Finanzinstitute die EIOS nutzen.  
**Aufwand:** ~4–5 Tage  
**Status:** 🔴 Offen

---

### C-08 — Multi-Framework-Mapping
**Wettbewerber:** Workiva (Kern-Differenziator)  
**Was fehlt:** Ein Datenpunkt (z.B. "Scope-1-Emissionen 2023: 12.400 t CO₂e") wird automatisch den entsprechenden Feldern in GRI 305-1, CSRD E1-6, TCFD Metric C1 und CDP C6.1 zugeordnet. Spart Doppelerfassung.  
**Aufwand:** ~5–7 Tage (Mapping-Tabellen + UI)  
**Status:** 🔴 Offen

---

## Bereits implementiert (aus KAN-99)

| Feature | Status | Datum |
|---------|--------|-------|
| Confidence-Ampel (Extraktions-Konfidenz pro Metrik) | ✅ DONE | 2026-07-16 |
| Export (Excel/CSV/JSON) | ✅ DONE | 2026-07-16 |
| Batch-Review Queue (Multi-Select + Bulk-Approve) | ✅ DONE | 2026-07-16 |
| Model Benchmark Tab | ✅ bereits vorhanden | — |

---

## Empfohlene Reihenfolge

```
C-02 (Disclosure Gap Tracker)   → schnellster CSRD-Mehrwert
C-01 (Materiality Matrix)       → CSRD-Pflicht, visuell beeindruckend
C-04 (Supplier Scorecard)       → leicht, hohe Sichtbarkeit
C-03 (Peer Benchmarking)        → Alleinstellungsmerkmal für Sales
C-05 (Task Manager)             → Plattform-Stickiness
C-06 → C-08                     → Integrations-Phase
```
