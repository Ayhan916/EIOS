# CSDDD-003 — Effectiveness Monitoring Workflow

**CSDDD-Referenz:** Art. 15 — Überwachung der Wirksamkeit  
**Phase:** 1 — Kritische Compliance-Lücken  
**Priorität:** HOCH  
**Aktueller Stand:** 50% → Ziel: 100%  
**Gesamtaufwand:** ~10 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 15 CSDDD verpflichtet Unternehmen, die Wirksamkeit ihrer Due-Diligence-Maßnahmen regelmäßig zu überwachen — mindestens alle 12 Monate und immer wenn sich die Risikosituation wesentlich ändert. Die Überwachung muss auf qualitativen **und** quantitativen Indikatoren basieren.

**Aktueller EIOS-Stand:**
- M43 Scoring (deterministischer Score) ✅ vorhanden
- M44 Forecasts ✅ vorhanden
- CAP-Tracking (Maßnahmen-Status) ✅ vorhanden
- Kein expliziter "Effectiveness Review" Workflow mit fester Periodizität
- Keine Indikatoren-Bibliothek (KPI-Set für DD-Wirksamkeit)
- Kein strukturierter Vergleich: Zustand-vorher vs. Zustand-nachher für eine Maßnahme

---

## Stories

### CSDDD-003-S1 — Indikatoren-Bibliothek (KPI-Framework)
**Beschreibung:** Als Compliance-Manager möchte ich aus einer vordefinierten Bibliothek von Wirksamkeitsindikatoren auswählen, damit die Messung meiner DD-Maßnahmen auf anerkannten Metriken basiert.

**Akzeptanzkriterien:**
- [ ] Bibliothek enthält mind. 20 vordefinierte Indikatoren (quantitativ + qualitativ) aus CSDDD-Leitlinien und gängiger Praxis:
  - Quantitativ: Anzahl geschlossener CAPs, Lieferanten-Audit-Quote, Grievance-Response-Zeit, Remediation-Rate
  - Qualitativ: Stakeholder-Zufriedenheit, Policy-Bekanntheitsgrad, Audit-Befund-Trend
- [ ] Organisation kann eigene Indikatoren definieren und zur Bibliothek hinzufügen
- [ ] Indikator hat: Name, Beschreibung, Typ (Quantitativ/Qualitativ), Einheit, Datenquelle (Automatisch/Manuell), CSDDD-Artikelbezug
- [ ] Indikatoren sind nach Risikokategorie filterbar

**Technische Analyse:**
- **Backend:** Neues Modell `EffectivenessIndicator` — Bibliothek als globale (organization_id=NULL) + organisationsspezifische Einträge
- **Backend:** Seed-Daten: 20 Standard-Indikatoren bei Erstinstallation
- **Frontend:** Neue Seite in Compliance-Bereich: "KPI-Bibliothek" mit Tabelle, Filter, "Eigenen KPI hinzufügen"

**Abhängigkeiten:** Keine  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-003-S2 — Effectiveness Review Workflow
**Beschreibung:** Als Compliance-Manager möchte ich periodische Wirksamkeits-Reviews durchführen und dokumentieren, damit ich Art. 15 CSDDD fristgerecht erfülle.

**Akzeptanzkriterien:**
- [ ] Review kann manuell gestartet oder automatisch nach 12 Monaten vorgeschlagen werden
- [ ] Review verknüpft ausgewählte Indikatoren aus der Bibliothek mit aktuellen Messwerten
- [ ] Für automatisch befüllbare Indikatoren (z.B. Anzahl geschlossener CAPs): automatisches Vorausfüllen aus Datenbank
- [ ] Für manuelle Indikatoren: Eingabefelder mit Freitext und Zahlenwert
- [ ] Review enthält: Bewertungszeitraum, Gesamtbewertung (Skala 1–5), Kernbefunde, Geplante Verbesserungsmaßnahmen
- [ ] Review kann als "abgeschlossen" markiert werden — erfordert dann Genehmigung durch Manager-Rolle
- [ ] KI-Agent darf Review NICHT abschließen — nur `create_draft_recommendation()` aufrufen

**Technische Analyse:**
- **Backend:** Neues Modell `EffectivenessReview` mit `ReviewLine`-Einträgen (Indikator + Messwert + Kommentar)
- **Backend:** Endpoint `POST /effectiveness-reviews` — erstellt Review, `PATCH /effectiveness-reviews/{id}/submit` — sendet zur Genehmigung
- **Backend:** `close()` Endpoint nur für Manager/Admin-Rolle erreichbar
- **Frontend:** Review-Formular mit dynamischen Feldern je nach Indikator-Typ

**Abhängigkeiten:** CSDDD-003-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-003-S3 — Vorher/Nachher Maßnahmen-Vergleich
**Beschreibung:** Als Compliance-Manager möchte ich sehen wie sich Risikoscores und Indikatoren nach Durchführung einer CAP verändert haben, damit ich die Wirkung einer Maßnahme objektiv belegen kann.

**Akzeptanzkriterien:**
- [ ] Für jeden abgeschlossenen CAP: Snapshot des Risk-Scores vor und nach Implementierung
- [ ] Vergleichsansicht: "Risk Score Δ", "Indikator Δ" je Maßnahme
- [ ] Zeitliche Darstellung: Liniendiagramm Risk Score über Zeit mit CAP-Markierungen
- [ ] Export: "Wirksamkeitsnachweis" PDF für einzelnen CAP
- [ ] Aggregierter Score: Durchschnittliche Risikoreduktion aller abgeschlossenen CAPs des Berichtsjahres

**Technische Analyse:**
- **Backend:** Bei CAP-Abschluss: Snapshot des aktuellen Risk-Scores in `CorrectiveActionPlan.baseline_score` (Pre) und `closed_score` (Post) speichern
- **Backend:** Neuer Query-Endpoint `GET /cap/{id}/effectiveness-snapshot`
- **Frontend:** Neues Panel in CAP-Detailansicht: "Wirksamkeit"
- **Frontend:** Recharts Liniendiagramm mit Annotationen

**Abhängigkeiten:** CSDDD-003-S2  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-003-S4 — Kontinuierliches Monitoring-Dashboard
**Beschreibung:** Als Management möchte ich ein Live-Dashboard, das mir jederzeit den aktuellen Stand der DD-Wirksamkeit zeigt, ohne auf den nächsten Jahres-Review warten zu müssen.

**Akzeptanzkriterien:**
- [ ] 6 Kernmetriken stets sichtbar: Offene CAPs, Überfällige CAPs, Geschlossene CAPs (12M), Grievance-Response-Ø-Zeit, Audit-Quote, Stakeholder-Konsultationen (12M)
- [ ] Trend-Indikatoren: Pfeil-Icons für Verbesserung / Verschlechterung vs. Vorjahresperiode
- [ ] Eskalations-Trigger: Bei signifikanter Risikoverschlechterung → automatisch neuen Review vorschlagen (Art. 15 Abs. 2: "wesentliche Änderung")
- [ ] Drilldown auf jede Metrik führt zur Detailansicht

**Technische Analyse:**
- **Backend:** Aggregations-Endpoint `GET /effectiveness/dashboard` — berechnet alle 6 Metriken aus existierenden Tabellen
- **Frontend:** Neues Dashboard-Modul in Compliance-Übersicht (analog bestehendem DD-Dashboard)
- **Performance:** Caching 15 Minuten, Hintergrundberechnung via Job bei großen Datensätzen

**Abhängigkeiten:** CSDDD-003-S1, CSDDD-003-S2  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] KI-Agent-Sperre auf Review-Abschluss-Endpoint verifiziert
- [ ] Risk-Score-Snapshots unveränderlich nach CAP-Abschluss
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 15 — Wirksamkeitsüberwachung"
- [ ] Changelog ergänzt
