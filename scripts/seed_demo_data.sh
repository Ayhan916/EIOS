#!/usr/bin/env bash
# EIOS Demo Seed Script
# Erstellt realistische Testdaten via API (Backend muss laufen auf :8000)
#
# Usage: bash scripts/seed_demo_data.sh

set -euo pipefail

BASE="http://localhost:8000/api/v1"
EMAIL="founder@eios.dev"
PASS="eios2026"
ORG="EIOS Demo GmbH"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC}  $*"; }
info() { echo -e "${BLUE}→${NC}  $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }
fail() { echo -e "${RED}✗${NC}  $*"; exit 1; }

# ── 1. Auth ───────────────────────────────────────────────────────────────────

info "Versuche Login..."
LOGIN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\"}" 2>/dev/null || true)

TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || true)

if [ -z "$TOKEN" ]; then
  info "Login fehlgeschlagen — registriere neuen Account..."
  REG=$(curl -s -X POST "$BASE/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASS\",\"display_name\":\"Founder\",\"organization_name\":\"$ORG\"}")
  TOKEN=$(echo "$REG" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
fi

[ -z "$TOKEN" ] && fail "Kein Token erhalten. Läuft das Backend auf $BASE?"
ok "Authentifiziert als $EMAIL"

AUTH_HEADER="Authorization: Bearer $TOKEN"

post() {
  local path="$1"; local body="$2"
  curl -sL -X POST "$BASE$path" \
    -H "$AUTH_HEADER" \
    -H "Content-Type: application/json" \
    -d "$body"
}

get() {
  local path="$1"
  curl -sL "$BASE$path" -H "$AUTH_HEADER"
}

extract_id() {
  python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null || true
}

# ── 2. Supplier ───────────────────────────────────────────────────────────────

info "Erstelle Lieferanten..."

SUP1=$(post "/suppliers" '{
  "name": "BatteryCell AG",
  "legal_name": "BatteryCell AG",
  "country": "DE",
  "industry": "Battery Manufacturing",
  "supplier_tier": "Tier 1",
  "website": "https://batterycell.example.com",
  "notes": "Tier-1 Zellhersteller für Lithium-Ionen-Batterien"
}')
S1_ID=$(echo "$SUP1" | extract_id)
[ -n "$S1_ID" ] && ok "Lieferant 1: BatteryCell AG ($S1_ID)" || warn "Lieferant 1 fehlgeschlagen: $(echo $SUP1 | head -c 200)"

SUP2=$(post "/suppliers" '{
  "name": "Cobalt Resources Ltd.",
  "legal_name": "Cobalt Resources Limited",
  "country": "CD",
  "industry": "Mining & Raw Materials",
  "supplier_tier": "Tier 2",
  "notes": "Kobalt-Rohstofflieferant aus der DRC"
}')
S2_ID=$(echo "$SUP2" | extract_id)
[ -n "$S2_ID" ] && ok "Lieferant 2: Cobalt Resources Ltd. ($S2_ID)" || warn "Lieferant 2 fehlgeschlagen"

SUP3=$(post "/suppliers" '{
  "name": "GreenPackaging GmbH",
  "legal_name": "GreenPackaging GmbH",
  "country": "AT",
  "industry": "Packaging",
  "supplier_tier": "Tier 1",
  "notes": "Nachhaltige Verpackungslösungen"
}')
S3_ID=$(echo "$SUP3" | extract_id)
[ -n "$S3_ID" ] && ok "Lieferant 3: GreenPackaging GmbH ($S3_ID)" || warn "Lieferant 3 fehlgeschlagen"

SUP4=$(post "/suppliers" '{
  "name": "SteelTech Korea Co.",
  "legal_name": "SteelTech Korea Co. Ltd.",
  "country": "KR",
  "industry": "Steel Manufacturing",
  "supplier_tier": "Tier 2",
  "notes": "Spezialistahl für Batteriegehäuse"
}')
S4_ID=$(echo "$SUP4" | extract_id)
[ -n "$S4_ID" ] && ok "Lieferant 4: SteelTech Korea ($S4_ID)" || warn "Lieferant 4 fehlgeschlagen"

# ── 3. Materialien ────────────────────────────────────────────────────────────

info "Erstelle Materialien..."

MAT1=$(post "/materials" '{
  "name": "Lithium-Karbonat",
  "material_type": "SUBSTANCE",
  "cas_number": "554-13-2",
  "description": "Batterie-Grade Lithiumkarbonat (Li2CO3)",
  "unit_of_measure": "kg",
  "is_critical_raw_material": true
}')
M1_ID=$(echo "$MAT1" | extract_id)
[ -n "$M1_ID" ] && ok "Material 1: Lithium-Karbonat ($M1_ID)" || warn "Material 1 fehlgeschlagen: $(echo $MAT1 | head -c 200)"

MAT2=$(post "/materials" '{
  "name": "Kobalt-Sulfat",
  "material_type": "SUBSTANCE",
  "cas_number": "10124-43-3",
  "description": "Kathoden-Material fuer Li-Ion Batterien (CoSO4)",
  "unit_of_measure": "kg",
  "is_critical_raw_material": true
}')
M2_ID=$(echo "$MAT2" | extract_id)
[ -n "$M2_ID" ] && ok "Material 2: Kobalt-Sulfat ($M2_ID)" || warn "Material 2 fehlgeschlagen"

MAT3=$(post "/materials" '{
  "name": "Graphit synthetisch",
  "material_type": "RAW_MATERIAL",
  "cas_number": "7782-42-5",
  "description": "Synthetisches Graphit als Anodenmaterial",
  "unit_of_measure": "kg",
  "is_critical_raw_material": true
}')
M3_ID=$(echo "$MAT3" | extract_id)
[ -n "$M3_ID" ] && ok "Material 3: Graphit ($M3_ID)" || warn "Material 3 fehlgeschlagen"

MAT4=$(post "/materials" '{
  "name": "Aluminium-Folie",
  "material_type": "PROCESSED_MATERIAL",
  "description": "Stromableiter fuer Kathode",
  "unit_of_measure": "kg",
  "recycled_content_pct": 35.0
}')
M4_ID=$(echo "$MAT4" | extract_id)
[ -n "$M4_ID" ] && ok "Material 4: Aluminium-Folie ($M4_ID)" || warn "Material 4 fehlgeschlagen"

# ── 4. Produkt ────────────────────────────────────────────────────────────────

info "Erstelle Produkte..."

PROD1=$(post "/products" '{
  "name": "EIOS-BAT-100 Lithium-Ionen Zelle",
  "product_type": "COMPONENT",
  "sku": "BAT-100-NMC",
  "description": "NMC 811 Lithium-Ionen Zelle, 100Ah, prismatisch",
  "target_market": "EU",
  "unit_of_measure": "Stueck",
  "is_regulated_product": true,
  "weight_kg": 1.05,
  "country_of_manufacture": "DE"
}')
P1_ID=$(echo "$PROD1" | extract_id)
[ -n "$P1_ID" ] && ok "Produkt 1: EIOS-BAT-100 ($P1_ID)" || warn "Produkt 1 fehlgeschlagen: $(echo $PROD1 | head -c 200)"

PROD2=$(post "/products" '{
  "name": "EIOS-PACK-48V Batteriepack",
  "product_type": "FINISHED_GOOD",
  "sku": "PACK-48V-5KWH",
  "description": "48V 5kWh Batteriepack fuer stationaere Speicher",
  "target_market": "EU",
  "unit_of_measure": "Stueck",
  "is_regulated_product": true,
  "weight_kg": 52.0,
  "country_of_manufacture": "DE"
}')
P2_ID=$(echo "$PROD2" | extract_id)
[ -n "$P2_ID" ] && ok "Produkt 2: EIOS-PACK-48V ($P2_ID)" || warn "Produkt 2 fehlgeschlagen"

# BOM-Einträge für Produkt 1
if [ -n "$P1_ID" ]; then
  [ -n "$M1_ID" ] && post "/products/$P1_ID/bom" "{\"material_id\":\"$M1_ID\",\"weight_pct\":18.5,\"quantity\":0.194,\"unit\":\"kg\"}" > /dev/null && ok "BOM: Lithium-Karbonat → BAT-100 (18.5%)"
  [ -n "$M2_ID" ] && post "/products/$P1_ID/bom" "{\"material_id\":\"$M2_ID\",\"weight_pct\":22.0,\"quantity\":0.231,\"unit\":\"kg\",\"is_substance_of_concern\":true,\"notes\":\"SVHC — CoSO4 auf Kandidatenliste\"}" > /dev/null && ok "BOM: Kobalt-Sulfat → BAT-100 (22.0%)"
  [ -n "$M3_ID" ] && post "/products/$P1_ID/bom" "{\"material_id\":\"$M3_ID\",\"weight_pct\":24.0,\"quantity\":0.252,\"unit\":\"kg\"}" > /dev/null && ok "BOM: Graphit → BAT-100 (24.0%)"
  [ -n "$M4_ID" ] && post "/products/$P1_ID/bom" "{\"material_id\":\"$M4_ID\",\"weight_pct\":8.5,\"quantity\":0.089,\"unit\":\"kg\"}" > /dev/null && ok "BOM: Aluminium-Folie → BAT-100 (8.5%)"
fi

# BOM-Einträge für Produkt 2
if [ -n "$P2_ID" ]; then
  [ -n "$M1_ID" ] && post "/products/$P2_ID/bom" "{\"material_id\":\"$M1_ID\",\"weight_pct\":12.0,\"quantity\":6.24,\"unit\":\"kg\"}" > /dev/null && ok "BOM: Lithium-Karbonat → PACK-48V (12.0%)"
  [ -n "$M3_ID" ] && post "/products/$P2_ID/bom" "{\"material_id\":\"$M3_ID\",\"weight_pct\":15.5,\"quantity\":8.06,\"unit\":\"kg\"}" > /dev/null && ok "BOM: Graphit → PACK-48V (15.5%)"
fi

# ── 5. Compliance-Flags auf Materialien ───────────────────────────────────────

info "Setze Compliance-Flags auf Materialien..."

if [ -n "$M2_ID" ]; then
  post "/materials/$M2_ID/compliance" '{
    "regulation": "REACH_SVHC",
    "compliance_status": "NON_COMPLIANT",
    "notes": "Kobalt-Sulfat auf SVHC-Kandidatenliste — Autorisierungspflichtig gemaess REACH Art. 57"
  }' > /dev/null && ok "Flag: Kobalt-Sulfat → REACH_SVHC NON_COMPLIANT"

  post "/materials/$M2_ID/compliance" '{
    "regulation": "BATTERY_REGULATION",
    "compliance_status": "UNKNOWN",
    "notes": "Due-Diligence fuer EU-Batterieverordnung Art. 48 noch ausstehend"
  }' > /dev/null && ok "Flag: Kobalt-Sulfat → BATTERY_REGULATION UNKNOWN"
fi

if [ -n "$M1_ID" ]; then
  post "/materials/$M1_ID/compliance" '{
    "regulation": "REACH_SVHC",
    "compliance_status": "COMPLIANT",
    "notes": "Lithiumkarbonat nicht auf SVHC-Kandidatenliste — kein Autorisierungsbedarf"
  }' > /dev/null && ok "Flag: Lithium-Karbonat → REACH_SVHC COMPLIANT"
fi

if [ -n "$M3_ID" ]; then
  post "/materials/$M3_ID/compliance" '{
    "regulation": "REACH_SVHC",
    "compliance_status": "COMPLIANT",
    "notes": "Synthetisches Graphit — kein SVHC-Status"
  }' > /dev/null && ok "Flag: Graphit → REACH_SVHC COMPLIANT"
fi

# ── 6. Digital Product Passport ───────────────────────────────────────────────

if [ -n "$P1_ID" ]; then
  info "Erstelle Digital Product Passport..."
  DPP=$(post "/dpp" "{
    \"product_id\":\"$P1_ID\",
    \"format\":\"BATTERY_REGULATION\",
    \"product_category\":\"Battery Cell\",
    \"battery_chemistry\":\"NMC 811\",
    \"capacity_wh\":370.0,
    \"nominal_voltage_v\":3.7,
    \"declared_capacity_cycles\":3000,
    \"carbon_footprint_kg_co2e\":12.4,
    \"carbon_footprint_source\":\"computed\",
    \"recycled_content_pct\":8.5,
    \"manufacturer_name\":\"EIOS Demo GmbH\",
    \"manufacturer_country\":\"DE\",
    \"notes\":\"DPP für EU-Batterieverordnung (EU) 2023/1542\"
  }")
  DPP_ID=$(echo "$DPP" | extract_id)
  [ -n "$DPP_ID" ] && ok "DPP: EIOS-BAT-100 ($DPP_ID)" || warn "DPP fehlgeschlagen: $(echo $DPP | head -c 200)"
fi

# ── 7. Assessment + Befunde + Risiko ─────────────────────────────────────────

A1_ID=""
if [ -n "$S1_ID" ]; then
  info "Erstelle Assessment für BatteryCell AG..."
  ASS=$(post "/assessments" "{
    \"supplier_id\":\"$S1_ID\",
    \"title\":\"BatteryCell AG — ESG & CSRD Assessment Q2/2026\",
    \"description\":\"Erstbewertung nach CSRD-Anforderungen: Scope 1-3 Emissionen, Due-Diligence gemäß CSDDD, EU-Batterieverordnung Konformität\",
    \"assessment_type\":\"ESG\"
  }")
  A1_ID=$(echo "$ASS" | extract_id)
  [ -n "$A1_ID" ] && ok "Assessment: Q2/2026 ESG ($A1_ID)" || warn "Assessment fehlgeschlagen: $(echo $ASS | head -c 200)"
fi

A2_ID=""
if [ -n "$S2_ID" ]; then
  info "Erstelle Assessment für Cobalt Resources Ltd...."
  ASS2=$(post "/assessments" "{
    \"supplier_id\":\"$S2_ID\",
    \"title\":\"Cobalt Resources — HRDD Menschenrechts-Due-Diligence 2026\",
    \"description\":\"Human Rights Due Diligence gemäß CSDDD Art. 5 für Kobalt-Sourcing in der DRC\",
    \"assessment_type\":\"Human Rights\"
  }")
  A2_ID=$(echo "$ASS2" | extract_id)
  [ -n "$A2_ID" ] && ok "Assessment: HRDD Cobalt Resources ($A2_ID)" || warn "Assessment 2 fehlgeschlagen"
fi

# Befunde
if [ -n "$A1_ID" ]; then
  post "/findings" "{
    \"assessment_id\":\"$A1_ID\",
    \"title\":\"Kobalt-Sourcing ohne Due-Diligence-Nachweis\",
    \"description\":\"Lieferant bezieht Kobalt aus der DRC ohne dokumentierten Sorgfaltspflichtprozess gemäß CSDDD Art. 5. Keine Risikoanalyse für den Tier-2-Lieferanten vorhanden.\",
    \"severity\":\"High\",
    \"category\":\"Supply Chain\"
  }" > /dev/null && ok "Befund 1: Kobalt Due-Diligence"

  post "/findings" "{
    \"assessment_id\":\"$A1_ID\",
    \"title\":\"CO2-Fussabdruck nicht offengelegt\",
    \"description\":\"Scope 1 und Scope 2 Emissionen für das Berichtsjahr 2025 nicht berichtet. ESRS E1 Pflichtberichterstattung gilt ab 2026.\",
    \"severity\":\"Medium\",
    \"category\":\"Climate\"
  }" > /dev/null && ok "Befund 2: CO2-Offenlegung"

  post "/findings" "{
    \"assessment_id\":\"$A1_ID\",
    \"title\":\"EU-Batterieverordnung: Recyclatanteil nicht nachgewiesen\",
    \"description\":\"Mindestanteil an Recyclingmaterial (Kobalt: 16%, Lithium: 6% ab 2031) nicht dokumentiert. Vorbereitung unzureichend.\",
    \"severity\":\"Medium\",
    \"category\":\"Regulatory\"
  }" > /dev/null && ok "Befund 3: Recyclatanteil"
fi

if [ -n "$A2_ID" ]; then
  post "/findings" "{
    \"assessment_id\":\"$A2_ID\",
    \"title\":\"Keine OECD-konforme Sorgfaltspflichtkette für Kobalt\",
    \"description\":\"Kobalt-Abbau ohne OECD Due Diligence Guidance for Responsible Mineral Supply Chains Konformität. Risiko Kinderarbeit und Umweltschäden.\",
    \"severity\":\"Critical\",
    \"category\":\"Human Rights\"
  }" > /dev/null && ok "Befund 4: OECD-Konformität Kobalt"
fi

# Risiko
if [ -n "$A1_ID" ]; then
  info "Erstelle Risiken..."
  post "/risks" "{
    \"assessment_id\":\"$A1_ID\",
    \"title\":\"Lieferketten-Abhaengigkeit bei kritischen Rohstoffen\",
    \"description\":\"100% Kobalt-Bezug aus einem einzigen Tier-2-Lieferanten in Hochrisikoregion (DRC). Single-Source-Risiko bei kritischem Rohstoff ohne Alternativlieferanten.\",
    \"risk_level\":\"Critical\",
    \"category\":\"Supply Chain\"
  }" > /dev/null && ok "Risiko 1: Rohstoff-Abhängigkeit"

  post "/risks" "{
    \"assessment_id\":\"$A1_ID\",
    \"title\":\"Regulatorisches Risiko: EU-Batterieverordnung Non-Compliance\",
    \"description\":\"Bei fehlender REACH-Autorisierung für Kobalt-Sulfat droht Marktausschluss in der EU ab 2027. Bussgelder bis 4% des Jahresumsatzes.\",
    \"risk_level\":\"High\",
    \"category\":\"Regulatory\"
  }" > /dev/null && ok "Risiko 2: Regulatorisches Risiko"
fi

# ── Fertig ────────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Demo-Daten erfolgreich erstellt!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Login-Daten:"
echo -e "  Email:    ${BLUE}$EMAIL${NC}"
echo -e "  Passwort: ${BLUE}$PASS${NC}"
echo ""
echo "  Erstellt:"
echo "  • 4 Lieferanten (BatteryCell, Cobalt Resources, GreenPackaging, SteelTech)"
echo "  • 4 Materialien (Lithium-Karbonat, Kobalt-Sulfat, Graphit, Aluminium-Folie)"
echo "  • 2 Produkte mit BOM (BAT-100, PACK-48V)"
echo "  • Compliance-Flags (REACH, EU-Batterieverordnung)"
echo "  • 1 Digital Product Passport"
echo "  • 2 Assessments (ESG, HRDD)"
echo "  • 4 Befunde + 2 Risiken"
echo ""
echo "  Frontend öffnen: http://localhost:3000"
echo ""
