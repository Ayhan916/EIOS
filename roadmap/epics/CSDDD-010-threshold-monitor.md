# CSDDD-010 — Threshold Monitor

**CSDDD-Referenz:** Art. 2 — Geltungsbereich: Schwellenwerte & Übergangsfristen  
**Phase:** 4 — Zukunftssicherung  
**Priorität:** NIEDRIG (bei größeren Unternehmen relevant)  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~6 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 2 CSDDD definiert gestaffelte Anwendungsschwellen:
- **Stufe 1 (ab 26. Juli 2027):** Unternehmen ≥ 5.000 MA UND ≥ 1,5 Mrd. € Nettoumsatz weltweit
- **Stufe 2 (ab 26. Juli 2028):** Unternehmen ≥ 1.000 MA UND ≥ 450 Mio. € Nettoumsatz weltweit
- Sonderregel: Nicht-EU-Unternehmen, Hochrisikobereich-Ausnahmen

EIOS-Nutzer können nahe an diesen Schwellen operieren. Ein Monitor der die Schwellenwerte trackt und rechtzeitig warnt ist für Compliance-Teams wertvoll.

---

## Stories

### CSDDD-010-S1 — Unternehmenskennzahlen pflegen
**Beschreibung:** Als Compliance-Manager möchte ich die relevanten Unternehmenskennzahlen (Mitarbeiterzahl, Umsatz) im System pflegen, damit der Schwellenwert-Monitor korrekte Aussagen treffen kann.

**Akzeptanzkriterien:**
- [ ] Neue Entität `CompanyProfile` mit Feldern: `fiscal_year`, `employee_count_worldwide`, `net_revenue_eur_worldwide`, `headquarters_country`, `sector`, `non_eu_company` (Boolean)
- [ ] Pro Geschäftsjahr ein Eintrag (historisch)
- [ ] Felder editierbar durch Admin-Rolle
- [ ] Änderungen in Audit Log
- [ ] Hinweis: Daten sind selbst eingetragen — kein automatischer Abgleich mit Handelsregistern

**Technische Analyse:**
- **Backend:** Neues Modell `CompanyProfile` (nicht `organization_id` FK, sondern direkt die Organisation selbst)
- **Frontend:** Neuer Bereich in Company-Settings: "Unternehmenskennzahlen"

**Abhängigkeiten:** Keine  
**Story Points:** 1  
**Status:** 🔴 TODO

---

### CSDDD-010-S2 — Schwellenwert-Berechnung & Status
**Beschreibung:** Als Compliance-Manager möchte ich auf einen Blick sehen ob mein Unternehmen aktuell unter CSDDD Stufe 1, Stufe 2 oder noch keiner Stufe fällt.

**Akzeptanzkriterien:**
- [ ] Automatische Berechnung basierend auf aktuellen `CompanyProfile`-Daten:
  - Stufe 1: MA ≥ 5.000 UND Umsatz ≥ 1,5 Mrd. €
  - Stufe 2: MA ≥ 1.000 UND Umsatz ≥ 450 Mio. €
  - Noch nicht betroffen: Unterhalb beider Schwellen
- [ ] Status-Badge: "CSDDD Stufe 1", "CSDDD Stufe 2", "Noch nicht CSDDD-pflichtig", "Grenzbereich (< 20% unter Schwelle)"
- [ ] Berechnung deterministisch (kein KI-basiertes Scoring)
- [ ] Wenn Grenzbereich: Warnhinweis mit nächsten Pflichten und Übergangsfrist-Datum

**Technische Analyse:**
- **Backend:** Service `application/compliance/threshold_calculator.py` — Pure Function
- **Backend:** Endpoint `GET /compliance/csddd-threshold-status`
- **Frontend:** Anzeige im Compliance-Dashboard oder Settings

**Abhängigkeiten:** CSDDD-010-S1  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-010-S3 — Schwellenwert-Alert & Timeline
**Beschreibung:** Als Compliance-Manager möchte ich gewarnt werden wenn sich meine Kennzahlen einem Schwellenwert annähern, damit ich frühzeitig die notwendigen Vorbereitungen einleiten kann.

**Akzeptanzkriterien:**
- [ ] E-Mail-Benachrichtigung wenn neue Kennzahlen eingetragen werden und Grenzbereich erreicht wird
- [ ] Timeline-Visualisierung: Historische Entwicklung MA und Umsatz vs. Schwellenwerte (Liniendiagramm)
- [ ] Prognose-Feature (optional, einfach): Wenn lineares Wachstum fortgesetzt → in wie vielen Jahren Schwelle erreicht?
- [ ] Regulatorische Timeline: Übersicht der Übergangsfristen (2027, 2028) mit Countdown-Anzeige
- [ ] Informationstext: Was bedeutet Stufe 1/2 konkret — welche Pflichten entstehen?

**Technische Analyse:**
- **Backend:** Notification bei `CompanyProfile` Update wenn Grenzbereich neu eintritt
- **Frontend:** Neue Komponente "CSDDD-Threshold-Monitor" in Compliance-Settings
- **Frontend:** Recharts Liniendiagramm mit Schwellenwert-Referenzlinien

**Abhängigkeiten:** CSDDD-010-S1, CSDDD-010-S2  
**Story Points:** 3  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 3 Stories implementiert und tested
- [ ] Schwellenwert-Berechnung deterministisch + Unit-tested
- [ ] `organization_id` auf allen Queries (CompanyProfile gehört zur Organization)
- [ ] Confluence-Seite erstellt: "CSDDD Art. 2 — Schwellenwerte & Anwendungsbereich"
- [ ] Changelog ergänzt
