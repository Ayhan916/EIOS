# CSDDD-014 — Regulatory Change Radar

**CSDDD-Referenz:** Art. 7 Abs. 4 (Aktualisierungspflicht), Art. 15 Abs. 2 (Wesentliche Änderung) — Eigene Innovation  
**Phase:** 4 — Zukunftssicherung  
**Priorität:** NIEDRIG  
**Aktueller Stand:** 0% → Ziel: 100%  
**Gesamtaufwand:** ~11 Story Points  
**Status:** 🔴 TODO  

---

## Kontext & Anforderung

CSDDD Art. 7 Abs. 4 und Art. 15 Abs. 2 verpflichten Unternehmen, ihre DD-Prozesse bei wesentlichen regulatorischen Änderungen zu aktualisieren. Der **Regulatory Change Radar** ist eine eigene Innovation: ein kuratorisches Feed-System das regulatorische Änderungen (CSDDD-Delegierte Rechtsakte, nationale Umsetzungsgesetze, EU-Guidance-Dokumente) trackt und Compliance-Teams automatisch benachrichtigt.

**Differenzierungspotential:**
- Compliance-Teams verbringen heute viel Zeit mit manueller Regulatory-Watch
- EIOS könnte dies automatisieren → signifikanter Mehrwert
- Kann ggf. in Premium-Tier vermarktet werden

---

## Stories

### CSDDD-014-S1 — Regulatory-Quellen-Konfiguration
**Beschreibung:** Als Compliance-Manager möchte ich konfigurieren welche regulatorischen Quellen ich verfolgen möchte, damit der Radar nur für mich relevante Änderungen anzeigt.

**Akzeptanzkriterien:**
- [ ] Vordefinierte Quellen-Bibliothek: EUR-Lex (CSDDD-Delegierte Rechtsakte), BAFA (LkSG-Guidance), EU-Kommission Guidance, EFRAG Reporting Standards, ILO Konventionen, OECD Due Diligence Guidance
- [ ] Eigene Quellen hinzufügbar (URL + Name + Beschreibung)
- [ ] Pro Quelle: Relevanzbewertung (1–5) → beeinflusst Priorisierung in Feed
- [ ] Länder-Filter: Nur Quellen aus bestimmten Jurisdiktionen anzeigen
- [ ] Branchen-Filter: Nur Quellen die für meinen Sektor relevant sind

**Technische Analyse:**
- **Backend:** Neues Modell `RegulatorySource` — globale Bibliothek + org-spezifische Konfiguration
- **Backend:** Seed-Daten: 10 Standard-Quellen bei Erstinstallation
- **Frontend:** Einstellungs-Seite "Regulatory Radar Quellen"

**Abhängigkeiten:** Keine  
**Story Points:** 2  
**Status:** 🔴 TODO

---

### CSDDD-014-S2 — Manueller Change-Eingang & Kuratierung
**Beschreibung:** Als Compliance-Manager möchte ich regulatorische Änderungen manuell erfassen (oder aus E-Mail-Newslettern eintragen), damit der Radar auch nicht-automatisch erfasste Quellen abdeckt.

**Akzeptanzkriterien:**
- [ ] Neuer "Regulatory Change" kann manuell angelegt werden
- [ ] Felder: Titel, Quelle, URL, Datum des Inkrafttretens, Zusammenfassung, Betroffene CSDDD-Artikel (Multi-Select), Relevanz für Organisation (Pflichtfeld: Begründung), Handlungsbedarf (Ja/Nein + Beschreibung)
- [ ] Change kann einem Governance-Termin / DD-Politik-Review verknüpft werden
- [ ] Statusverfolgung: Neu / Analysiert / Umgesetzt / Nicht relevant
- [ ] Kuratierungs-Queue: Neue Changes landen zunächst in "Zu prüfen" bis jemand sie bewertet hat

**Technische Analyse:**
- **Backend:** Neues Modell `RegulatoryChange` — mit Versionierung
- **Backend:** Router `interfaces/api/routers/regulatory_changes.py`
- **Frontend:** Neues Modul "Regulatory Radar" mit Inbox-Ansicht (ähnlich E-Mail-Inbox)

**Abhängigkeiten:** CSDDD-014-S1  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-014-S3 — Automatische RSS/Web-Monitor-Integration
**Beschreibung:** Als Compliance-Manager möchte ich dass EUR-Lex und BAFA-Quellen automatisch auf neue Veröffentlichungen geprüft werden, damit ich keine regulatorischen Änderungen versäume.

**Akzeptanzkriterien:**
- [ ] Automatischer RSS/Atom-Feed-Abruf für konfigurierte Quellen die RSS unterstützen
- [ ] EUR-Lex RSS Feed für CSDDD-Verfahren (bekannte EUR-Lex Feed-URL)
- [ ] Täglich gecheckt (Background-Job), neue Einträge landen in Kuratierungs-Queue
- [ ] Duplikat-Erkennung: bereits vorhandene Einträge nicht doppelt importieren (URL-Hash)
- [ ] Rate-Limiting: max. 1 Request pro Quelle pro Stunde
- [ ] Fehler-Benachrichtigung wenn Feed > 7 Tage nicht erreichbar

**Technische Analyse:**
- **Backend:** Background-Job (Celery Beat): `tasks/regulatory_radar_fetcher.py`
- **Backend:** feedparser Library für RSS-Parsing
- **Backend:** Modell `RegulatoryFeedEntry` mit `url_hash` für Duplikat-Erkennung
- **Sicherheit:** Keine Ausführung von Skripten aus Feeds — nur Textinhalt verarbeiten

**Abhängigkeiten:** CSDDD-014-S2  
**Story Points:** 3  
**Status:** 🔴 TODO

---

### CSDDD-014-S4 — Change-Impact-Analyse & Benachrichtigung
**Beschreibung:** Als Compliance-Manager möchte ich für jeden bestätigten relevanten Regulatory Change eine strukturierte Impact-Analyse erstellen, damit ich die notwendigen EIOS-Konfigurationsänderungen planen kann.

**Akzeptanzkriterien:**
- [ ] Impact-Analyse-Formular: Betroffene EIOS-Module (Multi-Select), Handlungsempfehlung, Geschätzter Aufwand, Fälligkeit
- [ ] Benachrichtigung an Compliance-Manager wenn Change-Status von "Neu" auf "Analysiert" gesetzt wird
- [ ] Benachrichtigung an Management wenn Change-Status = "Handlungsbedarf JA" + Fälligkeit < 60 Tage
- [ ] Dashboard-Widget: "X neue regulatorische Änderungen zu prüfen"
- [ ] Automatische Verknüpfung: Wenn Change Art. 7 betrifft → Erinnerung DD-Politik zu aktualisieren

**Technische Analyse:**
- **Backend:** Erweiterung `RegulatoryChange` Modell um Impact-Felder
- **Backend:** Notification-Service bei Status-Änderungen
- **Frontend:** Dashboard-Widget + Impact-Analyse-Formular im Change-Detail

**Abhängigkeiten:** CSDDD-014-S2, CSDDD-014-S3  
**Story Points:** 3  
**Status:** 🔴 TODO

---

## Definition of Done
- [ ] Alle 4 Stories implementiert und tested
- [ ] RSS-Fetcher: keine Skript-Ausführung aus Feeds (Security)
- [ ] Duplikat-Erkennung getestet
- [ ] Rate-Limiting auf Feed-Abrufe
- [ ] `organization_id` auf allen Queries
- [ ] Confluence-Seite erstellt: "Regulatory Change Radar — Quellen & Prozess"
- [ ] Changelog ergänzt
