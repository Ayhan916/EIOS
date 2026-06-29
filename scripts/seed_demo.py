"""
EIOS Full Demo Seed Script — corrected field names from OpenAPI schema
Run: python scripts/seed_demo.py
"""

import sys
import requests

BASE = "http://localhost:8000/api/v1"
EMAIL = "ayhan.yaman1@icloud.com"
PASSWORD = "Founder2026!"

def login():
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    data = r.json()
    token = data["access_token"]
    me = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    return token, me["id"], me["organization_id"]

TOKEN, USER_ID, ORG_ID = login()

def h():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def post(path, body, silent=False):
    r = requests.post(f"{BASE}{path}", json=body, headers=h())
    if not silent and r.status_code not in (200, 201):
        print(f"  WARN {path}: {r.status_code} {r.text[:140]}")
    try:
        return r.json()
    except Exception:
        return {}

def put(path, body):
    r = requests.put(f"{BASE}{path}", json=body, headers=h())
    try:
        return r.json()
    except Exception:
        return {}

def patch(path, body):
    r = requests.patch(f"{BASE}{path}", json=body, headers=h())
    try:
        return r.json()
    except Exception:
        return {}

def ok(label):
    print(f"  ✓  {label}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. SUPPLIERS
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 1. Suppliers ──────────────────────────────────────────────────────────")

SUPPLIERS_RAW = [
    {"name": "Infineon Technologies AG",    "country": "DE", "sector": "Semiconductors",       "risk_tier": 2, "esg_score": 74},
    {"name": "Bosch Automotive GmbH",       "country": "DE", "sector": "Automotive Parts",      "risk_tier": 1, "esg_score": 81},
    {"name": "CATL Europe BV",              "country": "NL", "sector": "Battery Manufacturing", "risk_tier": 2, "esg_score": 58},
    {"name": "Foxconn Industrial Internet", "country": "TW", "sector": "Electronics Assembly",  "risk_tier": 3, "esg_score": 44},
    {"name": "Siemens Energy AG",           "country": "DE", "sector": "Energy Equipment",      "risk_tier": 1, "esg_score": 79},
    {"name": "Tata Steel Europe Ltd",       "country": "NL", "sector": "Steel Manufacturing",   "risk_tier": 2, "esg_score": 52},
    {"name": "DHL Supply Chain GmbH",       "country": "DE", "sector": "Logistics",             "risk_tier": 1, "esg_score": 68},
    {"name": "Yanzhou Coal Mining Co",      "country": "CN", "sector": "Coal & Mining",         "risk_tier": 4, "esg_score": 23},
]

REVENUES  = [180_000_000, 2_400_000_000, 950_000_000, 8_200_000_000, 3_100_000_000, 1_700_000_000, 2_800_000_000, 4_500_000_000]
EMPLOYEES = [250, 1200, 4800, 22000, 55000, 8000, 11000, 35000]

supplier_ids = []
for i, s in enumerate(SUPPLIERS_RAW):
    r = post("/suppliers/", {
        "name": s["name"],
        "country_of_incorporation": s["country"],
        "sector": s["sector"],
        "risk_tier": s["risk_tier"],
        "esg_score": s["esg_score"],
        "website": f"https://www.example-{i+1}.com",
        "description": f"Tier-{s['risk_tier']} supplier in {s['sector']} sector.",
        "employee_count": EMPLOYEES[i],
        "annual_revenue_eur": REVENUES[i],
    })
    sid = r.get("id")
    if sid:
        supplier_ids.append({"id": sid, **s})
        ok(s["name"])

# ══════════════════════════════════════════════════════════════════════════════
# 2. ASSESSMENTS
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 2. Assessments ────────────────────────────────────────────────────────")

ASSESSMENT_TEMPLATES = [
    {
        "title": "ESG Risk Assessment Q1 2026",
        "description": "Comprehensive ESG risk review covering environmental, social, and governance dimensions.",
        "scope": "Environmental and Social risk review",
        "findings": [
            {"title": "Carbon emissions above sector benchmark",  "severity": "High",     "category": "Environmental"},
            {"title": "Supplier code of conduct not enforced",    "severity": "Medium",   "category": "Social"},
            {"title": "No Scope 3 emissions disclosure",          "severity": "Medium",   "category": "Environmental"},
        ],
        "risks": [
            {"title": "Climate transition risk — stranded assets","level": "High",    "category": "Climate"},
            {"title": "Reputational risk from labour practices",  "level": "Medium",  "category": "Reputational"},
        ],
    },
    {
        "title": "CSRD Readiness Assessment 2026",
        "description": "CSRD / ESRS gap analysis to identify compliance gaps before the June 2026 reporting deadline.",
        "scope": "CSRD / ESRS gap analysis",
        "findings": [
            {"title": "ESRS E1 climate reporting gaps identified","severity": "Critical","category": "Compliance"},
            {"title": "Double materiality assessment incomplete", "severity": "High",   "category": "Governance"},
        ],
        "risks": [
            {"title": "Regulatory non-compliance under CSRD",    "level": "Critical","category": "Compliance"},
        ],
    },
    {
        "title": "Human Rights Due Diligence",
        "description": "Supply chain labour rights assessment aligned with LkSG and UN Guiding Principles.",
        "scope": "Supply chain labour rights",
        "findings": [
            {"title": "Forced labour risk in Tier-2 supply chain","severity": "Critical","category": "Social"},
            {"title": "Living wage not guaranteed for contractors","severity": "High",   "category": "Social"},
            {"title": "Grievance mechanism not accessible",       "severity": "Medium",  "category": "Governance"},
        ],
        "risks": [
            {"title": "Human rights violation exposure",          "level": "Critical","category": "Human Rights"},
            {"title": "Supply chain disruption from labour unrest","level": "High",   "category": "Operational"},
        ],
    },
]

assessment_ids = []
finding_ids = []
risk_ids = []

for i, sup in enumerate(supplier_ids[:6]):
    tmpl = ASSESSMENT_TEMPLATES[i % len(ASSESSMENT_TEMPLATES)]
    a = post("/assessments/", {
        "title": tmpl["title"],
        "description": tmpl["description"],
        "supplier_id": sup["id"],
        "scope": tmpl["scope"],
        "assessment_type": "esg",
    })
    aid = a.get("id")
    if not aid:
        continue
    assessment_ids.append(aid)
    ok(f"Assessment: {tmpl['title'][:40]} — {sup['name'][:25]}")

    for f in tmpl["findings"]:
        fres = post("/findings/", {
            "title": f["title"],
            "severity": f["severity"],
            "category": f["category"],
            "description": f"Finding identified during {tmpl['title']} for {sup['name']}. Requires remediation within 60 days.",
            "assessment_id": aid,
        })
        if fres.get("id"):
            finding_ids.append(fres["id"])

    for rv in tmpl["risks"]:
        rres = post("/risks/", {
            "title": rv["title"],
            "description": f"Risk identified for {sup['name']} during {tmpl['title']}. Material impact expected.",
            "risk_level": rv["level"],
            "category": rv["category"],
            "assessment_id": aid,
            "probability": 0.65 if rv["level"] == "Critical" else 0.45,
            "impact": 0.90 if rv["level"] == "Critical" else 0.70,
        })
        if rres.get("id"):
            risk_ids.append(rres["id"])

print(f"  → {len(assessment_ids)} assessments, {len(finding_ids)} findings, {len(risk_ids)} risks")

# ══════════════════════════════════════════════════════════════════════════════
# 3. STANDALONE EXECUTIVE RISKS
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 3. Executive Risks ────────────────────────────────────────────────────")

EXEC_RISKS = [
    {"title": "Physical Climate Risk — Flooding at Factory 3",    "level": "Critical","cat": "Climate"},
    {"title": "Carbon Border Adjustment Mechanism cost exposure",  "level": "High",    "cat": "Regulatory"},
    {"title": "Critical mineral supply concentration (China 74%)","level": "Critical","cat": "Supply Chain"},
    {"title": "CSRD non-compliance penalty exposure €2.8M",       "level": "High",    "cat": "Compliance"},
    {"title": "ESG rating downgrade risk — MSCI review Q3",       "level": "Medium",  "cat": "Reputational"},
    {"title": "Transition risk: stranded fossil fuel assets",      "level": "High",    "cat": "Climate"},
    {"title": "Greenwashing litigation risk from NGO campaign",    "level": "Medium",  "cat": "Legal"},
]

for r_item in EXEC_RISKS:
    r = post("/risks/", {
        "title": r_item["title"],
        "description": f"Enterprise-level strategic risk: {r_item['title']}. Requires board-level attention.",
        "risk_level": r_item["level"],
        "category": r_item["cat"],
        "probability": 0.60 if r_item["level"] == "Critical" else 0.40,
        "impact": 0.95 if r_item["level"] == "Critical" else 0.75,
    })
    if r.get("id"):
        risk_ids.append(r["id"])
        ok(r_item["title"][:58])

# ══════════════════════════════════════════════════════════════════════════════
# 4. RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 4. Recommendations ────────────────────────────────────────────────────")

RECS = [
    ("Implement Science-Based Targets for Scope 1+2+3",       "Critical", "Open"),
    ("Commission third-party labour rights audit",            "High",     "InProgress"),
    ("Deploy ISO 14001 environmental management system",      "High",     "Open"),
    ("Establish supplier code of conduct enforcement",        "High",     "InProgress"),
    ("Complete ESRS E1 climate disclosure requirements",      "Critical", "Open"),
    ("Integrate living wage policy into supplier contracts",  "Medium",   "Open"),
    ("Set up Scope 3 data collection pipeline",              "High",     "InProgress"),
    ("Board ESG committee formation",                         "Medium",   "Open"),
    ("Publish CSRD-compliant sustainability report 2025",     "Critical", "Open"),
    ("Deploy real-time emissions monitoring sensors",         "Medium",   "Open"),
]

for i, (title, priority, status) in enumerate(RECS):
    aid = assessment_ids[i % len(assessment_ids)] if assessment_ids else None
    r = post("/recommendations/", {
        "title": title,
        "description": f"Strategic recommendation: {title}. Implementation required within 90 days per ESG roadmap.",
        "priority": priority,
        "assessment_id": aid,
        "action_required": True,
    })
    if r.get("id"):
        ok(title[:55])

# ══════════════════════════════════════════════════════════════════════════════
# 5. EVIDENCE
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 5. Evidence ───────────────────────────────────────────────────────────")

EVIDENCE_ITEMS = [
    {"title": "ISO 14001 Certificate 2025",              "type": "Document",  "source": "TÜV Rheinland"},
    {"title": "GHG Inventory Report Q1 2026",            "type": "Report",    "source": "Internal ESG Team"},
    {"title": "Third-Party Labour Audit — Foxconn 2025", "type": "Report",    "source": "Bureau Veritas"},
    {"title": "CSRD Double Materiality Assessment",      "type": "Report",    "source": "Deloitte Sustainability"},
    {"title": "Supplier ESG Questionnaire — CATL",       "type": "Document",  "source": "Supplier Self-Assessment"},
    {"title": "Carbon Footprint Verification — TÜV",     "type": "Document",  "source": "TÜV SÜD"},
    {"title": "Human Rights Policy Statement 2026",      "type": "Publication","source": "Legal & Compliance"},
    {"title": "Scope 3 Emissions Data Export Q1 2026",   "type": "Data",      "source": "ERP System"},
]

evidence_ids = []
for i, ev in enumerate(EVIDENCE_ITEMS):
    aid = assessment_ids[i % len(assessment_ids)] if assessment_ids else None
    r = post("/evidences/", {
        "title": ev["title"],
        "evidence_type": ev["type"],
        "source": ev["source"],
        "description": f"Evidence document: {ev['title']}. Collected for ESG compliance verification.",
        "assessment_id": aid,
        "language": "en",
        "reliability_score": 0.90,
    })
    if r.get("id"):
        evidence_ids.append(r["id"])
        ok(ev["title"])

# ══════════════════════════════════════════════════════════════════════════════
# 6. SUSTAINABILITY — KPIs
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 6. Sustainability KPIs ────────────────────────────────────────────────")

# ESGKPICreate categories: EMISSIONS|SUPPLIER_COMPLIANCE|AUDIT_COMPLETION|TRAINING_COMPLETION|DIVERSITY|INCIDENT_RATE|CUSTOM
KPIS = [
    {"name": "Total GHG Emissions (Scope 1+2)",    "unit": "tCO2e",     "cat": "EMISSIONS",            "target": 45000,  "current": 62400,  "thresh": 70000},
    {"name": "Scope 3 Supply Chain Emissions",     "unit": "tCO2e",     "cat": "EMISSIONS",            "target": 180000, "current": 234000, "thresh": 260000},
    {"name": "Renewable Energy Share",             "unit": "%",         "cat": "CUSTOM",               "target": 80,     "current": 54,     "thresh": 30},
    {"name": "Supplier ESG Screening Rate",        "unit": "%",         "cat": "SUPPLIER_COMPLIANCE",  "target": 100,    "current": 67,     "thresh": 50},
    {"name": "Female Leadership Ratio",            "unit": "%",         "cat": "DIVERSITY",            "target": 40,     "current": 28,     "thresh": 20},
    {"name": "Lost Time Injury Rate",              "unit": "per 1M h",  "cat": "INCIDENT_RATE",        "target": 0.5,    "current": 1.2,    "thresh": 2.0},
    {"name": "ESG Audit Completion Rate",          "unit": "%",         "cat": "AUDIT_COMPLETION",     "target": 100,    "current": 73,     "thresh": 60},
    {"name": "ESG Training Completion",            "unit": "%",         "cat": "TRAINING_COMPLETION",  "target": 95,     "current": 82,     "thresh": 70},
    {"name": "Water Consumption Intensity",        "unit": "m3/€M",     "cat": "CUSTOM",               "target": 12,     "current": 18.4,   "thresh": 25},
    {"name": "Carbon Price Internal Rate",         "unit": "€/tCO2",    "cat": "CUSTOM",               "target": 80,     "current": 45,     "thresh": 20},
]

kpi_ids = []
for kpi in KPIS:
    r = post(f"/sustainability/{ORG_ID}/kpis", {
        "name": kpi["name"],
        "unit": kpi["unit"],
        "category": kpi["cat"],
        "target_value": kpi["target"],
        "alert_threshold": kpi["thresh"],
        "frequency": "QUARTERLY",
        "description": f"Key sustainability performance indicator: {kpi['name']}",
    })
    if r.get("id"):
        kpi_ids.append(r["id"])
        # Add measurement
        post(f"/sustainability/{ORG_ID}/kpis/{r['id']}/measurements", {
            "value": kpi["current"],
            "period": "2026-Q1",
            "notes": "Q1 2026 measurement — verified by ESG controller",
        }, silent=True)
        ok(kpi["name"])

# ══════════════════════════════════════════════════════════════════════════════
# 7. SUSTAINABILITY — Emission Sources
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 7. Emission Sources ───────────────────────────────────────────────────")

# EmissionSourceCreate: name*, scope*(SCOPE1|2|3), activity_data*, emission_factor*, period_start*, period_end*, reporting_year*
EMISSIONS = [
    {"name": "Natural Gas — HQ Building",       "scope": "SCOPE1", "activity": 6200,    "factor": 0.2,    "cat": "stationary_combustion"},
    {"name": "Fleet Vehicles (Diesel)",         "scope": "SCOPE1", "activity": 15280,   "factor": 0.25,   "cat": "mobile_combustion"},
    {"name": "Purchased Electricity — Germany", "scope": "SCOPE2", "activity": 71500,   "factor": 0.4,    "cat": "purchased_electricity"},
    {"name": "Business Air Travel",             "scope": "SCOPE3", "activity": 12000000,"factor": 0.00035,"cat": "business_travel"},
    {"name": "Purchased Goods & Services",      "scope": "SCOPE3", "activity": 189000,  "factor": 1.0,    "cat": "purchased_goods"},
    {"name": "Employee Commuting",              "scope": "SCOPE3", "activity": 7000000, "factor": 0.0004, "cat": "employee_commuting"},
]

emission_ids = []
for em in EMISSIONS:
    r = post(f"/sustainability/{ORG_ID}/emissions", {
        "name": em["name"],
        "scope": em["scope"],
        "activity_data": em["activity"],
        "emission_factor": em["factor"],
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "reporting_year": 2026,
        "category": em["cat"],
        "activity_unit": "kWh" if "Electricity" in em["name"] else "km" if "Travel" in em["name"] or "Commut" in em["name"] else "m3" if "Gas" in em["name"] else "km",
        "emission_factor_unit": "tCO2e/unit",
        "source_reference": "DEFRA 2023 / EPA 2023",
    })
    if r.get("id"):
        emission_ids.append(r["id"])
        ok(em["name"])

# ══════════════════════════════════════════════════════════════════════════════
# 8. SUSTAINABILITY — Objectives & Initiatives
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 8. Objectives & Initiatives ───────────────────────────────────────────")

# ESGObjectiveCreate: title*, category*(ENVIRONMENTAL|SOCIAL|GOVERNANCE)
OBJECTIVES = [
    {"title": "Net-Zero Scope 1+2 by 2040",        "cat": "ENVIRONMENTAL"},
    {"title": "100% Renewable Energy by 2030",     "cat": "ENVIRONMENTAL"},
    {"title": "Zero Waste to Landfill by 2028",    "cat": "ENVIRONMENTAL"},
    {"title": "50% Women in Leadership by 2030",   "cat": "SOCIAL"},
    {"title": "100% Supplier ESG Screening 2026",  "cat": "GOVERNANCE"},
]

obj_ids = []
for obj in OBJECTIVES:
    r = post(f"/sustainability/{ORG_ID}/objectives", {
        "title": obj["title"],
        "category": obj["cat"],
        "description": f"Strategic sustainability objective: {obj['title']}",
        "owner_user_id": USER_ID,
        "start_date": "2026-01-01T00:00:00Z",
        "target_date": "2030-12-31T00:00:00Z",
    })
    if r.get("id"):
        obj_ids.append(r["id"])
        ok(obj["title"])

# DecarbonizationInitiativeCreate: name*, initiative_type*(RENEWABLE_ENERGY|LOGISTICS_OPTIMIZATION|SUPPLIER_TRANSITION|FACILITY_UPGRADE|OTHER), expected_reduction*
INITIATIVES = [
    {"name": "Solar PV — Munich Campus",        "type": "RENEWABLE_ENERGY",      "reduction": 4800},
    {"name": "EV Fleet Transition",             "type": "LOGISTICS_OPTIMIZATION","reduction": 3200},
    {"name": "Green Steel Procurement",         "type": "SUPPLIER_TRANSITION",   "reduction": 18000},
    {"name": "Factory 3 Energy Upgrade",        "type": "FACILITY_UPGRADE",      "reduction": 6500},
    {"name": "Supplier ESG Capacity Building",  "type": "SUPPLIER_TRANSITION",   "reduction": 2200},
    {"name": "Water Recycling System",          "type": "FACILITY_UPGRADE",      "reduction": 800},
]

for init in INITIATIVES:
    r = post(f"/sustainability/{ORG_ID}/initiatives", {
        "name": init["name"],
        "initiative_type": init["type"],
        "expected_reduction": init["reduction"],
        "description": f"Decarbonization initiative: {init['name']}",
        "cost_estimate": init["reduction"] * 200.0,
        "start_date": "2026-01-01",
        "end_date": "2028-12-31",
    })
    if r.get("id"):
        ok(init["name"])

# Sustainability Report
r = post(f"/sustainability/{ORG_ID}/reports", {
    "title": "CSRD Annual Sustainability Report 2025",
    "report_type": "FULL",
    "period_start": "2025-01-01",
    "period_end": "2025-12-31",
})
if r.get("id"):
    ok("CSRD Annual Sustainability Report 2025")

# ══════════════════════════════════════════════════════════════════════════════
# 9. FINANCIAL ESG
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 9. Financial ESG ──────────────────────────────────────────────────────")

# EU Taxonomy — TaxonomyAssessmentCreate: assessment_year*, taxonomy_framework
r = post(f"/financial-esg/{ORG_ID}/taxonomy", {
    "assessment_year": 2025,
    "taxonomy_framework": "EU_TAXONOMY",
    "total_revenue": 485_000_000.0,
    "total_capex": 84_000_000.0,
    "total_opex": 32_000_000.0,
    "eligible_activities": {
        "manufacture_low_carbon": {"revenue_pct": 62, "capex_pct": 71},
        "renewable_energy": {"revenue_pct": 14, "capex_pct": 18},
    },
    "aligned_activities": {
        "manufacture_low_carbon": {"revenue_pct": 48, "capex_pct": 58},
        "renewable_energy": {"revenue_pct": 11, "capex_pct": 14},
    },
    "justification": "Assessment aligned with EU Taxonomy Delegated Acts for climate mitigation.",
})
if r.get("id"):
    ok("EU Taxonomy Assessment 2025")

# Green CapEx — GreenCapexCreate: project_name*, amount*, alignment_percent*, period*
CAPEX_ITEMS = [
    {"project": "Solar PV Manufacturing Upgrade",     "amount": 24_500_000, "aligned": 88},
    {"project": "EV Charging Infrastructure Rollout", "amount": 8_200_000,  "aligned": 100},
    {"project": "Heat Pump HVAC Replacement",         "amount": 4_100_000,  "aligned": 95},
]
for cx in CAPEX_ITEMS:
    r = post(f"/financial-esg/{ORG_ID}/capex", {
        "project_name": cx["project"],
        "amount": cx["amount"],
        "alignment_percent": cx["aligned"],
        "period": "2025",
        "currency": "EUR",
        "taxonomy_category": "climate_mitigation",
    })
    if r.get("id"):
        ok(cx["project"])

# Transition Plan — TransitionPlanCreate: name*, financing_needs*, currency*
r = post(f"/financial-esg/{ORG_ID}/transition-plans", {
    "name": "Climate Transition Plan 2026–2040",
    "description": "Comprehensive decarbonisation roadmap aligned with 1.5°C pathway",
    "financing_needs": 180_000_000.0,
    "currency": "EUR",
    "start_date": "2026-01-01T00:00:00Z",
    "target_date": "2040-12-31T00:00:00Z",
    "baseline_state": {"emissions_tco2e": 310000, "year": 2023},
    "target_state": {"emissions_tco2e": 0, "year": 2040},
    "funding_sources": {"green_bonds": 80_000_000, "internal_capex": 60_000_000, "eu_grants": 40_000_000},
})
if r.get("id"):
    ok("Climate Transition Plan 2026–2040")

# Financial Scenarios — scenario_name*, scenario_type*, inputs*, assumptions*
SCENARIOS = [
    {
        "scenario_name": "1.5°C Aligned Transition",
        "scenario_type": "climate_transition",
        "inputs": {"carbon_price_eur": 150, "renewable_share": 95, "year": 2035},
        "assumptions": {"policy_trajectory": "rapid", "tech_breakthrough": True},
        "notes": "IPCC 1.5°C pathway — most ambitious scenario",
    },
    {
        "scenario_name": "Delayed Transition (3°C)",
        "scenario_type": "climate_physical",
        "inputs": {"carbon_price_eur": 40, "temperature_rise_c": 3.0, "year": 2050},
        "assumptions": {"policy_trajectory": "weak", "physical_risks": "severe"},
        "notes": "Weak policy action, severe physical climate risks materialise post-2030",
    },
    {
        "scenario_name": "CSRD Full Enforcement",
        "scenario_type": "regulatory",
        "inputs": {"carbon_price_eur": 90, "mandatory_assurance_year": 2027},
        "assumptions": {"enforcement": "strict", "penalty_exposure_eur": 2_800_000},
        "notes": "Full CSRD enforcement with mandatory third-party assurance from 2027",
    },
]

for sc in SCENARIOS:
    r = post(f"/financial-esg/{ORG_ID}/scenarios", sc)
    if r.get("id"):
        ok(sc["scenario_name"])

# ══════════════════════════════════════════════════════════════════════════════
# 10. SECURITY — SOC2, Checklist, Pentest
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 10. Security ──────────────────────────────────────────────────────────")

post("/security/soc2/seed", {}, silent=True)
ok("SOC2 controls seeded")

post("/security/production-checklist/seed", {}, silent=True)
ok("Production security checklist seeded")

# PentestFindingCreate: owasp_category*(A01-A10), title*, severity*(CRITICAL|HIGH|MEDIUM|LOW|INFO)
PENTEST = [
    {"owasp": "A01", "title": "Insecure Direct Object Reference in Supplier API",  "sev": "HIGH"},
    {"owasp": "A07", "title": "Missing rate limiting on authentication endpoints",  "sev": "MEDIUM"},
    {"owasp": "A03", "title": "XSS vulnerability in report export filename param", "sev": "MEDIUM"},
    {"owasp": "A09", "title": "Sensitive data in server logs (partial tokens)",    "sev": "HIGH"},
    {"owasp": "A02", "title": "Weak password policy — no complexity requirement",  "sev": "MEDIUM"},
]
for pt in PENTEST:
    r = post("/security/pentest/findings", {
        "owasp_category": pt["owasp"],
        "title": pt["title"],
        "severity": pt["sev"],
        "cvss_score": 7.8 if pt["sev"] == "HIGH" else 5.4,
        "description": f"Penetration test finding: {pt['title']}",
        "remediation_notes": "Apply OWASP remediation guidance. Fix within 30 days for HIGH, 90 days for MEDIUM.",
    })
    if r.get("id"):
        ok(pt["title"][:58])

# ══════════════════════════════════════════════════════════════════════════════
# 11. EXECUTIVE REPORTS (Board Reports)
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 11. Executive Reports ─────────────────────────────────────────────────")

BOARD_REPORTS = [
    {
        "title": "Q1 2026 ESG Board Report",
        "executive_summary": (
            "Q1 2026 shows material progress on climate targets: Scope 1+2 emissions down 8% YoY to 62,400 tCO2e. "
            "Critical risks remain in supply chain concentration (74% critical minerals from China) and CSRD "
            "compliance gaps (48% readiness). Three Critical findings require board attention. "
            "ESG portfolio score: 71/100 (+4 vs Q4 2025). Full remediation roadmap enclosed."
        ),
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "report_type": "quarterly",
    },
    {
        "title": "Annual ESG Performance Review 2025",
        "executive_summary": (
            "FY2025: GHG emissions reduced 12% vs 2023 baseline (310,000 → 272,000 tCO2e). "
            "EU Taxonomy alignment 72% (target: 80% by 2027). "
            "Supplier ESG screening: 67% coverage — 33 high-risk suppliers remain unscreened. "
            "CSRD first-year reporting on track for June 2026. "
            "Three new Critical risks added: CBAM exposure, mineral supply concentration, physical flood risk."
        ),
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
        "report_type": "annual",
    },
]

for br in BOARD_REPORTS:
    r = post("/executive/reports", {
        "title": br["title"],
        "executive_summary": br["executive_summary"],
        "period_start": br["period_start"],
        "period_end": br["period_end"],
        "report_type": br["report_type"],
    })
    if r.get("id"):
        ok(br["title"])

# ══════════════════════════════════════════════════════════════════════════════
# 12. SUPPLIER CERTIFICATES
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 12. Supplier Certificates ─────────────────────────────────────────────")

# SupplierCertificateCreate: name*, cert_type*, expires_at*
CERTS = [
    {"name": "ISO 14001:2015 Environmental Management",  "type": "ISO_14001", "issuer": "TÜV Rheinland",  "expires": "2027-06-30T00:00:00Z"},
    {"name": "ISO 9001:2015 Quality Management",         "type": "ISO_9001",  "issuer": "DNV GL",         "expires": "2026-12-31T00:00:00Z"},
    {"name": "SA8000 Social Accountability",             "type": "SA8000",    "issuer": "Bureau Veritas", "expires": "2026-09-30T00:00:00Z"},
    {"name": "ISO 50001 Energy Management",              "type": "ISO_50001", "issuer": "TÜV SÜD",        "expires": "2027-03-31T00:00:00Z"},
]

for i, sup in enumerate(supplier_ids[:4]):
    cert = CERTS[i % len(CERTS)]
    r = post(f"/suppliers/{sup['id']}/certificates", {
        "name": cert["name"],
        "cert_type": cert["type"],
        "expires_at": cert["expires"],
        "issued_at": "2024-06-01T00:00:00Z",
        "issuer": cert["issuer"],
        "certificate_number": f"CERT-{2024+i}-{10000+i}",
        "alert_days_before": 90,
        "notes": f"Verified by {cert['issuer']}. Auto-renewal in progress.",
    })
    if r.get("id"):
        ok(f"{cert['type']} — {sup['name'][:30]}")

# ══════════════════════════════════════════════════════════════════════════════
# 13. AI GOVERNANCE
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 13. AI Governance ─────────────────────────────────────────────────────")

# AIModelCreate: name*, provider*, model_type*(LLM|CLASSIFICATION|RISK_SCORING|EMBEDDING|RANKING|FORECASTING|OTHER)
AI_MODELS = [
    {"name": "ESG Copilot",          "provider": "Anthropic", "type": "LLM",          "purpose": "Q&A, analysis, drafting"},
    {"name": "Supplier Risk Scorer", "provider": "Internal",  "type": "RISK_SCORING", "purpose": "Automated ESG risk scoring"},
    {"name": "Document Classifier",  "provider": "Internal",  "type": "CLASSIFICATION","purpose": "Evidence document classification"},
    {"name": "Forecast Engine",      "provider": "Internal",  "type": "FORECASTING",  "purpose": "KPI and emissions forecasting"},
]

for m in AI_MODELS:
    r = post(f"/ai-governance/{ORG_ID}/models", {
        "name": m["name"],
        "provider": m["provider"],
        "model_type": m["type"],
        "purpose": m["purpose"],
        "owner_user_id": USER_ID,
        "metadata": {"version": "1.0", "deployed": "2026-01-15"},
    })
    if r.get("id"):
        ok(m["name"])

# AIPolicyCreate: name*, policy_type*(APPROVED_PROVIDERS|PROHIBITED_USE_CASES|RETENTION|REVIEW_REQUIREMENTS|OTHER)
AI_POLICIES = [
    {"name": "Approved AI Providers Policy",        "type": "APPROVED_PROVIDERS",   "body": {"providers": ["Anthropic", "Internal"], "prohibited": ["OpenAI GPT-3", "unvetted"]}},
    {"name": "Prohibited AI Use Cases Policy",      "type": "PROHIBITED_USE_CASES", "body": {"prohibited": ["autonomous approval", "automated rejection of suppliers without review"]}},
    {"name": "AI Model Review Requirements",        "type": "REVIEW_REQUIREMENTS",  "body": {"review_frequency_months": 6, "required_approvers": ["CTO", "ESG Lead"]}},
]

for p in AI_POLICIES:
    r = post(f"/ai-governance/{ORG_ID}/policies", {
        "name": p["name"],
        "policy_type": p["type"],
        "policy_body": p["body"],
        "description": f"AI governance policy: {p['name']}",
    })
    if r.get("id"):
        ok(p["name"])

# ══════════════════════════════════════════════════════════════════════════════
# 14. COMMENTS
# ══════════════════════════════════════════════════════════════════════════════
print("\n── 14. Comments ──────────────────────────────────────────────────────────")

COMMENTS = [
    "Initial review completed — escalated to ESG lead for remediation planning.",
    "Root cause analysis in progress. Supplier has been notified. Target completion: 2026-05-15.",
    "Supplier acknowledged finding and submitted corrective action plan (CAP-2026-04-12).",
    "Third-party verification scheduled for Q2 2026. TÜV appointment confirmed.",
]

for i, fid in enumerate(finding_ids[:4]):
    r = post("/comments/", {
        "entity_type": "finding",
        "entity_id": fid,
        "content": COMMENTS[i % len(COMMENTS)],
    })
    if r.get("id"):
        ok(f"Comment on finding #{i+1}")

for i, rid in enumerate(risk_ids[:3]):
    r = post("/comments/", {
        "entity_type": "risk",
        "entity_id": rid,
        "content": f"Risk reviewed by ESG committee on 2026-04-08. Mitigation plan approved. Owner: Ayhan Yaman.",
    })
    if r.get("id"):
        ok(f"Comment on risk #{i+1}")

# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 62)
print("  EIOS Demo Data — COMPLETE")
print("=" * 62)
print(f"  Suppliers              : {len(supplier_ids)}")
print(f"  Assessments            : {len(assessment_ids)}")
print(f"  Findings               : {len(finding_ids)}")
print(f"  Risks (total)          : {len(risk_ids)}")
print(f"  Evidence records       : {len(evidence_ids)}")
print(f"  Sustainability KPIs    : {len(kpi_ids)}")
print(f"  Emission sources       : {len(emission_ids)}")
print(f"  Objectives             : {len(obj_ids)}")
print()
print("  → Open http://localhost:3000 and explore the platform.")
print()
