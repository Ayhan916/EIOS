# CSDDD-008 — Scoping Study Workflow

**CSDDD-Referenz:** Art. 8 Abs. 3 — Risikobasierte Priorisierung / Scoping  
**Phase:** 2 — Fehlende Module  
**Priorität:** MITTEL  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~10 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

Art. 8 Abs. 3 CSDDD erlaubt bei weitreichenden Lieferketten eine **risikobasierte Priorisierung**: Unternehmen können ihre DD-Bemühungen zunächst auf die Bereiche und Lieferanten konzentrieren, bei denen die Wahrscheinlichkeit und Schwere negativer Auswirkungen am größten ist. Diese Priorisierung muss dokumentiert, begründet und regelmäßig überprüft werden.

**Aktueller EIOS-Stand:**
- Risk-Scoring (M43) ✅ vorhanden
- Keine formalisierte "Scoping Study" als eigenes Dokument/Workflow
- Keine Dokumentation warum bestimmte Lieferanten/Bereiche zunächst priorisiert und andere zurückgestellt wurden
- Bei Behördenprüfung: fehlende Scoping-Begründung = Compliance-Risiko

---

## Stories

### CSDDD-008-S1 — Scoping-Parameter konfigurieren
**Beschreibung:** Als Compliance-Manager möchte ich die Scoping-Kriterien für die risikobasierte Priorisierung konfigurieren, damit die Priorisierungsentscheidungen transparent und nachvollziehbar sind.

**Akzeptanzkriterien:**
- [ ] Scoping-Parameter sind konfigurierbar (pro Organisation): Schwellenwert Risk-Score (ab wann = Tier-1-Priorität), Geografische Risikoregionen (Import-Liste aus bestehenden Länder-Daten), Sektoren mit höchstem Risikoprofil, Umsatzanteil-Schwellenwert je Lieferant
- [ ] Parameter können jährlich überprüft und historisch versioniert werden
- [ ] Änderungen an Parametern werden in Audit Log protokolliert (wer hat wann was geändert)
- [ ] Vordefinierte "Best-Practice"-Vorlage basierend auf CSDDD-Leitlinien der EU-Kommission

**Technische Analyse:**
- **Backend:** Neues Modell `ScopingConfig` mit Versionierung
- **Backend:** Audit Log auf Konfigurationsänderungen
- **Frontend:** Einstellungs-Seite "Scoping & Priorisierung" in Compliance-Settings

**Abhängigkeiten:** Keine  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-008-S2 — Automatische Priorisierungs-Analyse
**Beschreibung:** Als Compliance-Manager möchte ich eine automatische Analyse aller Lieferanten basierend auf den Scoping-Parametern, damit ich eine datengestützte Priorisierungsentscheidung treffen kann.

**Akzeptanzkriterien:**
- [ ] System analysiert alle Lieferanten gegen konfigurierte Scoping-Parameter
- [ ] Ergebnis: Drei Kategorien: "Priorität 1 — sofortige DD", "Priorität 2 — planmäßige DD", "Priorität 3 — vereinfachte DD"
- [ ] Jede Kategorisierung mit Begründung: "Score X, Region Y, Sektor Z → Priorität 1"
- [ ] Analyse ist deterministisch und nachvollziehbar (kein LLM-basiertes Scoring)
- [ ] Analyse kann manuell überschrieben werden mit Pflicht-Begründung (Audit Trail)
- [ ] Analyse-Ergebnis "eingefroren" als Snapshot für den Berichtszeitraum

**Technische Analyse:**
- **Backend:** Service `application/scoping/scoping_analyzer.py` — Pure Function analog `csddd_engine.py`
- **Backend:** Inputs: `ScopingConfig` + alle `Supplier`-Datensätze der Organisation
- **Backend:** Outputs: Liste `ScopingResult` je Lieferant mit `priority`, `reasons` (Array[String])
- **Backend:** Keine Datenbankschreibvorgänge während Analyse — Ergebnis separat speicherbar
- **Frontend:** "Analyse starten" Button → Ergebnis in Tabelle mit Drilldown

**Abhängigkeiten:** CSDDD-008-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-008-S3 — Scoping Study Dokument generieren
**Beschreibung:** Als Compliance-Manager möchte ich die Scoping-Analyse als formelles Dokument exportieren, das als Nachweis gegenüber Behörden dient.

**Akzeptanzkriterien:**
- [ ] Dokument enthält: Berichtsjahr, angewandte Scoping-Parameter, Priorisierungsergebnis-Tabelle, Begründungstext für Methodik, Genehmigungsfeld (wer hat die Studie freigegeben, Datum)
- [ ] Genehmigung: Compliance-Manager-Rolle kann Dokument einreichen, Manager/Admin genehmigt
- [ ] KI-Agent darf Scoping Study NICHT genehmigen
- [ ] Nach Genehmigung: Dokument gesperrt (keine Änderungen mehr)
- [ ] Export: PDF mit EIOS-Branding + CSDDD Art. 8 Abs. 3 Referenz-Fußnote

**Technische Analyse:**
- **Backend:** Neues Modell `ScopingStudy` mit Status-Enum und FK zu `ScopingConfig`
- **Backend:** PDF-Generierung via WeasyPrint/ReportLab
- **Backend:** Genehmigungsendpoint nur für Manager/Admin-Rolle
- **Frontend:** "Scoping Study erstellen" Wizard — 3-Schritt: Parameter → Analyse → Genehmigung

**Abhängigkeiten:** CSDDD-008-S2  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-008-S4 — Jährliche Überprüfungs-Erinnerung
**Beschreibung:** Als Compliance-Manager möchte ich automatisch erinnert werden, wenn die Scoping Study ihren jährlichen Review-Termin erreicht.

**Akzeptanzkriterien:**
- [ ] Jährliche E-Mail-Erinnerung 30 Tage vor Jahrestag der letzten genehmigten Scoping Study
- [ ] Dashboard-Indikator: "Scoping Study aktuell / Review fällig"
- [ ] Neue Scoping Study kann mit "letzte genehmigten" als Basis erstellt werden (Clone-Funktion)
- [ ] Historische Scoping Studies archiviert und einsehbar (nicht löschbar)

**Technische Analyse:**
- **Backend:** Background-Job: tägliche Prüfung auf fällige Scoping-Study-Reviews
- **Frontend:** Dashboard-Widget in Compliance-Übersicht

**Abhängigkeiten:** CSDDD-008-S3  
**Story Points:** 2  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] `npx tsc --noEmit` — 0 Fehler
- [ ] Priorisierungs-Algorithmus deterministisch + Unit-tested
- [ ] KI-Agent-Sperre auf Genehmigungsendpoint
- [ ] Genehmigte Dokumente unveränderlich
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "CSDDD Art. 8 — Scoping & Priorisierung"
- [ ] Changelog ergänzt
