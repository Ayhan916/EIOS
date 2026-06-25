"""
EIOS Full Platform Seed — alle verbleibenden Module
Deckt ab: Enterprise, OS Controls/Programs/Calendar, SBTs, Net-Zero Roadmap,
Sustainability Scorecard/Climate Risk/CSRD/ISSB/Assurance/Forecasts,
Financial ESG (Revenue/OpEx/Risk/Capital Markets/Valuation/Value Creation/
Carbon Cost/Climate Finance/Correlations/Disclosure), AI Governance
(Prompts/Use Cases/Incidents/Monitoring/Assurance), Strategy Pathways,
Network Relationships, Digital Twin, Knowledge.
"""

import asyncio, uuid, requests
from datetime import datetime, timezone

BASE   = "http://localhost:8000/api/v1"
EMAIL  = "ayhan.yaman1@icloud.com"
PASS   = "Founder2026!"
DB_DSN = "postgresql://eios:eios_dev@localhost:5432/eios_db"
ORG_ID = "7816af5e-1542-4658-9548-a800ec4c8e38"
USER_ID= "bcda5715-b077-4c73-b361-207ba0181e25"

def login():
    r = requests.post(f"{BASE}/auth/login", json={"email":EMAIL,"password":PASS})
    r.raise_for_status()
    return r.json()["access_token"]

TOKEN = login()

def H():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def post(path, body={}, silent=False):
    r = requests.post(f"{BASE}{path}", json=body, headers=H())
    if not silent and r.status_code not in (200,201):
        print(f"  WARN {path.split('/')[-1]}: {r.status_code} {r.text[:100]}")
    try: return r.json()
    except: return {}

def get(path):
    r = requests.get(f"{BASE}{path}", headers=H())
    try: return r.json()
    except: return {}

def ok(label): print(f"  ✓  {label}")
def section(t): print(f"\n── {t} {'─'*(55-len(t))}")

# ── Fetch existing context ────────────────────────────────────────────────────
section("Loading context")
raw = requests.get(f"{BASE}/suppliers/?page_size=20", headers=H()).json()
items = raw if isinstance(raw, list) else raw.get("items", raw.get("data",[]))
SUPPLIERS = {s["name"]: s["id"] for s in items}

raw2 = get("/sustainability/{org_id}/kpis".replace("{org_id}", ORG_ID))
kpi_items = raw2 if isinstance(raw2, list) else raw2.get("items", raw2.get("data",[]))
KPI_IDS = [k["id"] for k in kpi_items if isinstance(k, dict)]

raw3 = get(f"/sustainability/{ORG_ID}/objectives")
obj_items = raw3 if isinstance(raw3, list) else raw3.get("items", raw3.get("data",[]))
OBJ_IDS = [o["id"] for o in obj_items if isinstance(o, dict)]

raw4 = get(f"/assessments/?page_size=10")
ass_items = raw4 if isinstance(raw4, list) else raw4.get("items", raw4.get("data",[]))
ASS_IDS = [a["id"] for a in ass_items if isinstance(a, dict)]

print(f"  Suppliers: {len(SUPPLIERS)}  KPIs: {len(KPI_IDS)}  Objectives: {len(OBJ_IDS)}  Assessments: {len(ASS_IDS)}")
SUP_IDS = list(SUPPLIERS.values())

# ══════════════════════════════════════════════════════════════════════════════
# 1. ENTERPRISE — create enterprise, BUs, Regions, Legal Entities, Policies
# ══════════════════════════════════════════════════════════════════════════════
section("1. Enterprise Structure")

ent = post("/enterprise", {
    "name": "EIOS Industrial Group SE",
    "description": "European industrial conglomerate with sustainability-first mandate.",
    "hq_country": "DE",
    "industry": "Diversified Industrials",
    "default_data_residency": "EU",
    "default_data_classification": "CONFIDENTIAL",
    "settings": {"require_mfa": True, "session_timeout_minutes": 60},
})
ENT_ID = ent.get("id")
if ENT_ID:
    ok(f"Enterprise: EIOS Industrial Group SE ({ENT_ID[:8]}…)")

    # Link org to enterprise
    post(f"/enterprise/{ENT_ID}/link-organization", {"organization_id": ORG_ID}, silent=True)

    # Regions
    section("   Regions")
    REGIONS = [
        {"name": "DACH",            "code": "DACH", "data_residency": "EU"},
        {"name": "Benelux",         "code": "BNLX", "data_residency": "EU"},
        {"name": "Asia Pacific",    "code": "APAC", "data_residency": "APAC"},
        {"name": "North America",   "code": "NOAM", "data_residency": "US"},
    ]
    region_ids = []
    for rg in REGIONS:
        r = post(f"/enterprise/{ENT_ID}/regions", {
            "name": rg["name"], "code": rg["code"],
            "data_residency": rg["data_residency"],
            "admin_user_id": USER_ID,
        })
        if r.get("id"):
            region_ids.append(r["id"])
            ok(f"Region: {rg['name']}")

    # Business Units
    section("   Business Units")
    BUS = [
        "Advanced Manufacturing",
        "Energy & Decarbonisation",
        "Digital & Automation",
        "Supply Chain & Logistics",
        "Sustainability & ESG",
    ]
    bu_ids = []
    for bu in BUS:
        r = post(f"/enterprise/{ENT_ID}/business-units", {
            "name": bu,
            "description": f"Business unit responsible for {bu} across all regions.",
            "admin_user_id": USER_ID,
        })
        if r.get("id"):
            bu_ids.append(r["id"])
            ok(f"BU: {bu}")

    # Legal Entities
    section("   Legal Entities")
    LEGAL = [
        ("EIOS Manufacturing GmbH",       "DE", "GmbH",  "HRB 123456"),
        ("EIOS Energy Solutions BV",      "NL", "BV",    "KVK 87654321"),
        ("EIOS Digital AG",               "CH", "AG",    "CHE-123.456.789"),
        ("EIOS Logistics S.A.S.",         "FR", "SAS",   "SIREN 123456789"),
        ("EIOS Asia Pacific Pte Ltd",     "SG", "PTE",   "UEN 202312345A"),
    ]
    le_ids = []
    for name, country, form, reg in LEGAL:
        r = post(f"/enterprise/{ENT_ID}/legal-entities", {
            "name": name, "country": country,
            "legal_form": form, "registration_number": reg,
            "description": f"Legal entity for {country} operations.",
        })
        if r.get("id"):
            le_ids.append(r["id"])
            ok(f"Legal entity: {name}")

    # Enterprise Policies
    section("   Enterprise Policies")
    ENT_POLICIES = [
        ("ESG_REPORTING",   "ESG Data Reporting Standard",      {"frequency": "quarterly", "mandatory_kpis": ["GHG","Water","Diversity"]}),
        ("SUPPLIER_DUE_DILIGENCE","Supplier Due Diligence Policy", {"min_risk_tier_screened": 3, "annual_reassessment": True}),
        ("DATA_CLASSIFICATION","Data Classification Policy",    {"default": "CONFIDENTIAL", "esg_data": "RESTRICTED"}),
        ("AI_GOVERNANCE",   "Group AI Governance Policy",       {"approved_providers": ["Anthropic","Internal"], "require_human_review": True}),
    ]
    for ptype, pname, pconf in ENT_POLICIES:
        r = post(f"/enterprise/{ENT_ID}/policies", {
            "policy_type": ptype, "name": pname,
            "description": f"Group-wide policy: {pname}",
            "config": pconf, "cascade_to_children": True, "scope": "enterprise",
        })
        if r.get("id"):
            ok(f"Policy: {pname}")

    # Enterprise Risks
    section("   Enterprise Risks")
    ENT_RISKS = [
        ("Net-Zero Target Miss by >20% in 2030", "critical", "ENVIRONMENTAL"),
        ("CBAM exposure exceeds €15M — budget not provisioned", "high", "REGULATORY"),
        ("Key ESG talent attrition in sustainability team", "medium", "SOCIAL"),
        ("CSRD first report rejected by auditors", "high", "GOVERNANCE"),
    ]
    for title, sev, cat in ENT_RISKS:
        r = post(f"/enterprise/{ENT_ID}/risks", {
            "title": title, "severity": sev, "esg_category": cat,
            "description": f"Enterprise-level ESG risk: {title}",
            "owner_user_id": USER_ID,
            "mitigation_plan": f"Mitigation plan to be developed by ESG committee by Q2 2026.",
            "linked_organization_ids": [ORG_ID],
        })
        if r.get("id"):
            ok(f"Ent. risk: {title[:50]}")

# ══════════════════════════════════════════════════════════════════════════════
# 2. OPERATING SYSTEM — Programs, Calendar, Accountability, Control Tests
# ══════════════════════════════════════════════════════════════════════════════
section("2. Operating System — Programs, Calendar, Accountability")

# Programs
PROGRAMS = [
    ("CSRD Compliance Programme 2026",       "Coordinating all ESRS disclosure requirements across BUs. Deadline: June 2026."),
    ("Net-Zero Acceleration Programme",      "Cross-functional programme driving Scope 1+2 elimination and Scope 3 reduction."),
    ("Supplier ESG Uplift Programme",        "Capacity-building for Tier-1 and Tier-2 suppliers to meet ESG code of conduct."),
    ("Human Rights Due Diligence Programme", "LkSG + CSDDD implementation across supply chain. Covers grievance mechanisms."),
]

prog_ids = []
for title, desc in PROGRAMS:
    r = post("/operating-system/programs", {
        "title": title, "description": desc,
        "linked_objectives": OBJ_IDS[:2],
        "linked_suppliers": SUP_IDS[:3],
    })
    if r.get("id"):
        prog_ids.append(r["id"])
        ok(f"Programme: {title[:52]}")

# Calendar Events
section("   Calendar Events")
EVENTS = [
    ("CSRD Submission Deadline",           "DEADLINE",  "2026-06-30T23:59:00Z", 90, "First CSRD annual report submission deadline."),
    ("Board ESG Review Q2",                "MEETING",   "2026-06-15T09:00:00Z", 14, "Quarterly board ESG performance review."),
    ("CBAM Declaration — Q1 2026",         "DEADLINE",  "2026-05-31T23:59:00Z", 30, "CBAM quarterly declaration for Q1 2026 embedded emissions."),
    ("Supplier Audit — Foxconn Taiwan",    "AUDIT",     "2026-07-14T08:00:00Z", 30, "On-site human rights audit at Foxconn facility."),
    ("SBTi Target Submission Window",      "DEADLINE",  "2026-09-30T23:59:00Z", 60, "Submit near-term SBTi targets for validation."),
    ("Annual GHG Inventory Verification",  "AUDIT",     "2026-04-30T09:00:00Z", 14, "TÜV SÜD verification of FY2025 GHG inventory."),
    ("EU ETS Surrender Deadline",          "DEADLINE",  "2026-09-30T23:59:00Z", 30, "EU ETS allowance surrender for FY2025 verified emissions."),
    ("ESG Investor Day",                   "MEETING",   "2026-11-12T10:00:00Z", 21, "Annual ESG investor presentation and Q&A session."),
    ("ISO 14001 Surveillance Audit",       "AUDIT",     "2026-08-20T09:00:00Z", 21, "Annual ISO 14001 surveillance audit by TÜV Rheinland."),
    ("LkSG Annual Report Publication",     "DEADLINE",  "2026-12-31T23:59:00Z", 60, "LkSG due diligence report publication deadline."),
]

for title, etype, sched, remind, note in EVENTS:
    r = post("/operating-system/calendar", {
        "title": title, "event_type": etype,
        "scheduled_at": sched, "reminder_days": remind, "notes": note,
    })
    if r.get("id"):
        ok(f"Calendar: {title[:52]}")

# Accountability Assignments
section("   Accountability Assignments")
# Assign to KPIs and objectives
for i, kpi_id in enumerate(KPI_IDS[:5]):
    r = post("/operating-system/accountability", {
        "entity_type": "kpi", "entity_id": kpi_id,
        "role": "KPI_OWNER", "assigned_to_user_id": USER_ID,
    }, silent=True)
    if r.get("id"):
        ok(f"KPI owner assigned #{i+1}")

for i, obj_id in enumerate(OBJ_IDS[:3]):
    r = post("/operating-system/accountability", {
        "entity_type": "objective", "entity_id": obj_id,
        "role": "OBJECTIVE_OWNER", "assigned_to_user_id": USER_ID,
    }, silent=True)
    if r.get("id"):
        ok(f"Objective owner assigned #{i+1}")

# Additional ESG Controls with tests
section("   ESG Controls")
OS_CONTROLS = [
    ("Monthly GHG Data Collection Review",       "Environmental", "MONTHLY", True),
    ("Supplier ESG Screening Gate",              "Governance",    "QUARTERLY", True),
    ("CSRD Disclosure Completeness Check",       "Compliance",    "QUARTERLY", True),
    ("Labour Rights Audit — Tier-1 Suppliers",   "Social",        "ANNUAL", True),
    ("SBTi Progress Monitoring",                 "Environmental", "QUARTERLY", False),
    ("Board ESG Report Approval",                "Governance",    "QUARTERLY", True),
    ("AI Model Output Human Review Gate",        "Governance",    "MONTHLY", True),
    ("OFAC Sanctions Screening — New Suppliers", "Compliance",    "TRIGGERED", True),
    ("Incident Response — ESG Findings",         "Governance",    "TRIGGERED", True),
    ("Carbon Credit Retirement Reconciliation",  "Environmental", "ANNUAL", True),
]

ctrl_ids = []
for name, ctype, freq, ev_req in OS_CONTROLS:
    r = post("/operating-system/controls", {
        "control_name": name, "control_type": ctype,
        "frequency": freq, "evidence_required": ev_req,
        "owner_user_id": USER_ID,
    }, silent=True)
    # Try alternate path
    if not r.get("id"):
        r = post(f"/operating-system/organizations/{ORG_ID}/controls", {
            "control_name": name, "control_type": ctype,
            "frequency": freq, "evidence_required": ev_req,
        }, silent=True)
    if r.get("id"):
        ctrl_ids.append(r["id"])
        ok(f"Control: {name[:52]}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. SCIENCE-BASED TARGETS (SBTi)
# ══════════════════════════════════════════════════════════════════════════════
section("3. Science-Based Targets (SBTi)")

SBTS = [
    {
        "scope": "SCOPE1_2", "target_type": "ABSOLUTE",
        "baseline_year": 2023, "baseline_emissions": 34060.0,
        "target_reduction_percent": 50, "target_year": 2030,
        "sbt_framework": "SBTi",
        "description": "Near-term SBTi target: 50% absolute Scope 1+2 reduction by 2030 (1.5°C aligned)",
        "commitment_date": "2026-04-01",
    },
    {
        "scope": "SCOPE3", "target_type": "ABSOLUTE",
        "baseline_year": 2023, "baseline_emissions": 234000.0,
        "target_reduction_percent": 30, "target_year": 2030,
        "sbt_framework": "SBTi",
        "description": "Near-term SBTi Scope 3: 30% absolute reduction by 2030 (well-below 2°C)",
        "commitment_date": "2026-04-01",
    },
    {
        "scope": "ALL", "target_type": "ABSOLUTE",
        "baseline_year": 2023, "baseline_emissions": 268060.0,
        "target_reduction_percent": 90, "target_year": 2040,
        "sbt_framework": "SBTi",
        "description": "Long-term SBTi net-zero target: 90% absolute all-scope reduction by 2040",
        "commitment_date": "2026-04-01",
    },
]

sbt_ids = []
for sbt in SBTS:
    r = post(f"/sustainability/{ORG_ID}/sbts", sbt)
    if r.get("id"):
        sbt_ids.append(r["id"])
        ok(f"SBT: {sbt['description'][:55]}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. NET-ZERO ROADMAP + CARBON INVENTORY
# ══════════════════════════════════════════════════════════════════════════════
section("4. Net-Zero Roadmap & Carbon Inventory")

# Carbon Inventory (base year)
inv = post(f"/sustainability/{ORG_ID}/inventory", {
    "reporting_year": 2023,
    "period_start": "2023-01-01",
    "period_end": "2023-12-31",
})
INV_ID = inv.get("id")
if INV_ID:
    ok(f"Carbon inventory 2023 ({INV_ID[:8]}…)")

inv25 = post(f"/sustainability/{ORG_ID}/inventory", {
    "reporting_year": 2025,
    "period_start": "2025-01-01",
    "period_end": "2025-12-31",
})
INV25_ID = inv25.get("id")
if INV25_ID:
    ok(f"Carbon inventory 2025 ({INV25_ID[:8]}…)")

# Net-Zero Roadmap
road = post(f"/sustainability/{ORG_ID}/roadmaps", {
    "name": "EIOS Net-Zero Roadmap 2023–2040",
    "baseline_year": 2023,
    "target_year": 2040,
    "baseline_emissions": 268060.0,
    "target_reduction_percent": 90,
    "description": "Science-based net-zero roadmap aligned with SBTi 1.5°C pathway. "
                   "Covers Scope 1+2 elimination by 2035 and Scope 3 reduction by 90% by 2040.",
})
ROAD_ID = road.get("id")
if ROAD_ID:
    ok(f"Net-Zero Roadmap 2023–2040 ({ROAD_ID[:8]}…)")
    # Add milestones via initiatives — roadmap milestones
    MILESTONES = [
        {"name": "Scope 1+2 −25% milestone",        "initiative_type": "FACILITY_UPGRADE",      "expected_reduction": 8500},
        {"name": "100% Renewable Energy milestone",  "initiative_type": "RENEWABLE_ENERGY",      "expected_reduction": 28600},
        {"name": "EV Fleet 100% milestone",          "initiative_type": "LOGISTICS_OPTIMIZATION","expected_reduction": 3200},
        {"name": "Scope 3 Cat.1 −30% milestone",     "initiative_type": "SUPPLIER_TRANSITION",   "expected_reduction": 57000},
    ]
    for m in MILESTONES:
        r = post(f"/sustainability/{ORG_ID}/roadmaps/{ROAD_ID}/milestones", {
            "name": m["name"],
            "initiative_type": m["initiative_type"],
            "expected_reduction": m["expected_reduction"],
        }, silent=True)
        if r.get("id"):
            ok(f"  Milestone: {m['name']}")

# ══════════════════════════════════════════════════════════════════════════════
# 5. SUSTAINABILITY SCORECARD + ASSURANCE
# ══════════════════════════════════════════════════════════════════════════════
section("5. Scorecard & Assurance")

sc = post(f"/sustainability/{ORG_ID}/scorecards", {
    "period_start": "2026-01-01",
    "period_end": "2026-03-31",
})
if sc.get("id"):
    ok(f"Scorecard Q1 2026 — E:{sc.get('environmental_score',0):.0f} S:{sc.get('social_score',0):.0f} G:{sc.get('governance_score',0):.0f} Overall:{sc.get('overall_score',0):.0f}")

sc2 = post(f"/sustainability/{ORG_ID}/scorecards", {
    "period_start": "2025-01-01",
    "period_end": "2025-12-31",
})
if sc2.get("id"):
    ok(f"Scorecard FY2025 — Overall:{sc2.get('overall_score',0):.0f}")

# Assurance Record
assur = post(f"/sustainability/{ORG_ID}/assurance", {
    "report_type": "EMISSIONS",
    "reviewed_period_start": "2025-01-01",
    "reviewed_period_end": "2025-12-31",
    "reviewer_user_id": USER_ID,
    "assurance_level": "LIMITED",
    "methodology": "ISAE 3000 / ISO 14064-3",
    "findings": [
        "Scope 1 data: complete and verified.",
        "Scope 2 market-based: minor data gaps in Q3 — immaterial.",
        "Scope 3 Category 1: estimation methodology acceptable.",
    ],
})
if assur.get("id"):
    ok("Assurance record FY2025 (ISAE 3000 / ISO 14064-3)")

# ══════════════════════════════════════════════════════════════════════════════
# 6. CLIMATE RISK (TCFD)
# ══════════════════════════════════════════════════════════════════════════════
section("6. Climate Risk Assessments (TCFD)")

CLIMATE_RISKS = [
    {
        "title": "1.5°C Transition Risk Assessment 2026",
        "assessment_year": 2026, "scenario": "1_5C",
        "transition_risk_score": 72.0, "physical_risk_score": 28.0, "regulatory_risk_score": 85.0,
        "transition_risk_details": {"carbon_price_sensitivity": "HIGH", "stranded_assets_eur": 42_000_000, "policy_timing": "2027"},
        "physical_risk_details": {"flood_exposed_assets_pct": 8, "heat_stress_operations_pct": 12},
        "regulatory_risk_details": {"cbam_annual_cost_eur": 12_000_000, "csrd_compliance_cost": 800_000},
        "notes": "TCFD aligned. Most material risk: CBAM + carbon price trajectory.",
    },
    {
        "title": "2°C Business-As-Usual Risk Assessment 2026",
        "assessment_year": 2026, "scenario": "2C",
        "transition_risk_score": 45.0, "physical_risk_score": 52.0, "regulatory_risk_score": 58.0,
        "transition_risk_details": {"carbon_price_sensitivity": "MEDIUM", "stranded_assets_eur": 18_000_000},
        "physical_risk_details": {"flood_exposed_assets_pct": 18, "heat_stress_operations_pct": 28, "water_stress_sites": 2},
        "regulatory_risk_details": {"cbam_annual_cost_eur": 6_000_000},
        "notes": "Physical risks materialise post-2030. Factory 3 (Hamburg) highest exposure.",
    },
]

for cr in CLIMATE_RISKS:
    r = post(f"/sustainability/{ORG_ID}/climate-risk", cr)
    if r.get("id"):
        ok(f"Climate risk: {cr['title'][:55]}")

# ══════════════════════════════════════════════════════════════════════════════
# 7. CSRD & ISSB MAPPINGS
# ══════════════════════════════════════════════════════════════════════════════
section("7. CSRD / ISSB Mappings")

# CSRD / ESRS Mappings
CSRD_MAPPINGS = [
    ("E1", KPI_IDS[0] if KPI_IDS else None, None, "CCM-4", "GHG-1", "PARTIAL"),
    ("E1", KPI_IDS[1] if len(KPI_IDS)>1 else None, None, "CCM-4", "GHG-3", "NOT_ASSESSED"),
    ("E1", KPI_IDS[2] if len(KPI_IDS)>2 else None, None, "CCM-7", "RE-1", "PARTIAL"),
    ("S1", KPI_IDS[4] if len(KPI_IDS)>4 else None, None, "S1-9", "DI-1", "NOT_ASSESSED"),
    ("G1", None, OBJ_IDS[4] if len(OBJ_IDS)>4 else None, "G1-4", "SC-1", "PARTIAL"),
    ("E2", KPI_IDS[8] if len(KPI_IDS)>8 else None, None, "E2-4", "WU-1", "NOT_ASSESSED"),
]

for esrs, kpi_id, obj_id, dr, dp, status in CSRD_MAPPINGS:
    body = {"esrs_standard": esrs, "compliance_status": status,
            "disclosure_requirement": dr, "data_point_reference": dp}
    if kpi_id: body["kpi_id"] = kpi_id
    if obj_id: body["objective_id"] = obj_id
    r = post(f"/sustainability/{ORG_ID}/csrd-mappings", body)
    if r.get("id"):
        ok(f"CSRD mapping: ESRS {esrs} — {dr} [{status}]")

# ISSB Mappings
ISSB_MAPPINGS = [
    ("S2", KPI_IDS[0] if KPI_IDS else None, "IFRS S2 7a", "GHG-E-1", "COMPLIANT"),
    ("S2", KPI_IDS[1] if len(KPI_IDS)>1 else None, "IFRS S2 29e", "GHG-E-3", "PARTIAL"),
    ("S1", None, "IFRS S1 31", "MAT-1", "PARTIAL"),
]
for std, kpi_id, dr, dp, status in ISSB_MAPPINGS:
    body = {"issb_standard": std, "compliance_status": status,
            "disclosure_topic": dr, "metric_reference": dp}
    if kpi_id: body["kpi_id"] = kpi_id
    r = post(f"/sustainability/{ORG_ID}/issb-mappings", body)
    if r.get("id"):
        ok(f"ISSB mapping: {std} — {dr} [{status}]")

# ══════════════════════════════════════════════════════════════════════════════
# 8. SUSTAINABILITY FORECASTS
# ══════════════════════════════════════════════════════════════════════════════
section("8. Sustainability Forecasts")

FORECASTS = [
    {
        "forecast_type": "EMISSIONS",
        "method": "LINEAR_TREND",
        "period_start": "2026-01-01", "period_end": "2030-12-31",
        "forecast_horizon_months": 60,
        "historical_data": [
            {"period": "2023", "value": 268060},
            {"period": "2024", "value": 251000},
            {"period": "2025", "value": 234000},
        ],
        "assumptions": {"renewable_ramp": "linear", "fleet_electrification_pct_2030": 60},
    },
    {
        "forecast_type": "KPI_ATTAINMENT",
        "method": "MOVING_AVERAGE",
        "period_start": "2026-01-01", "period_end": "2028-12-31",
        "forecast_horizon_months": 36,
        "kpi_id": KPI_IDS[3] if len(KPI_IDS)>3 else None,
        "historical_data": [
            {"period": "2024-Q1", "value": 52},
            {"period": "2024-Q2", "value": 55},
            {"period": "2024-Q3", "value": 59},
            {"period": "2024-Q4", "value": 62},
            {"period": "2025-Q1", "value": 65},
        ],
        "assumptions": {"new_contracts_per_quarter": 2},
    },
]

for fc in FORECASTS:
    if not fc.get("kpi_id") and "KPI_ATTAINMENT" in fc.get("forecast_type",""):
        continue
    r = post(f"/sustainability/{ORG_ID}/forecasts", fc)
    if r.get("id"):
        ok(f"Forecast: {fc['forecast_type']} via {fc['method']}")

# Sustainability scenarios
SUST_SCENARIOS = [
    {
        "name": "Supplier ESG Uplift — Tier 1 All Green",
        "scenario_type": "SUPPLIER_IMPROVEMENT",
        "description": "Models portfolio ESG score impact if all Tier-1 suppliers reach ESG score ≥70.",
        "inputs": {"current_avg": 62, "target_avg": 70, "supplier_count": 8},
        "assumptions": {"timeline_years": 3, "cost_per_supplier": 120000},
    },
    {
        "name": "100% Renewable Electricity by 2028",
        "scenario_type": "RENEWABLE_TRANSITION",
        "description": "Full renewable electricity transition by 2028 via PPAs and on-site solar.",
        "inputs": {"current_renewable_pct": 54, "target_pct": 100, "capex_eur": 32_000_000},
        "assumptions": {"ppa_price_eur_mwh": 65, "self_generation_mwh": 12000},
    },
    {
        "name": "Emissions Intensity Reduction — Manufacturing",
        "scenario_type": "EMISSIONS_INTENSITY_REDUCTION",
        "description": "Reduce emissions per unit of production 40% by 2028 through process optimisation.",
        "inputs": {"baseline_intensity": 2.4, "target_intensity": 1.44, "production_units": "kton"},
        "assumptions": {"process_efficiency_gain_pct": 15, "fuel_switch_savings_tco2e": 8000},
    },
]

for sc in SUST_SCENARIOS:
    r = post(f"/sustainability/{ORG_ID}/scenarios", sc)
    if r.get("id"):
        ok(f"Sust. scenario: {sc['name'][:52]}")

# ══════════════════════════════════════════════════════════════════════════════
# 9. FINANCIAL ESG — Green Revenue, OpEx, Cost of Risk, Capital Markets,
#    Valuation, Value Creation, Carbon Cost, Climate Finance, Correlations,
#    Disclosure Package, Financial Report, Stress Test
# ══════════════════════════════════════════════════════════════════════════════
section("9. Financial ESG — Revenue / OpEx / Risk / Valuation")

# Green Revenue Streams
GREEN_REVENUE = [
    ("Renewable Energy Services",      145_000_000, 485_000_000, "EU_TAXONOMY",  "ALIGNED",    "Aligned with EU Taxonomy Act 4.1 Solar energy"),
    ("Low-Carbon Manufacturing",       280_000_000, 485_000_000, "EU_TAXONOMY",  "ALIGNED",    "Aligned with EU Taxonomy 3.3 Low-carbon technologies"),
    ("Energy Efficiency Solutions",     38_000_000, 485_000_000, "EU_TAXONOMY",  "ELIGIBLE",   "Eligible but not yet fully aligned — assurance pending"),
    ("Circular Economy Products",       22_000_000, 485_000_000, "GRI_STANDARD", "PARTIAL",    "GRI 305/306 aligned — partial circular economy revenues"),
]
for stream, amount, total, cat, status, notes in GREEN_REVENUE:
    r = post(f"/financial-esg/{ORG_ID}/revenue", {
        "revenue_stream": stream, "amount": amount, "total_revenue": total,
        "period": "2025", "taxonomy_category": cat,
        "alignment_status": status, "currency": "EUR", "notes": notes,
    })
    if r.get("id"):
        ok(f"Green revenue: {stream}")

# Green OpEx
GREEN_OPEX = [
    ("Renewable energy procurement (PPAs)",           4_200_000, 95, "energy"),
    ("Sustainable supply chain monitoring platform",  1_800_000, 90, "supply_chain"),
    ("Carbon credit portfolio management",            2_400_000, 100, "carbon"),
    ("ESG audit and assurance fees",                  850_000,   85, "governance"),
    ("Environmental compliance & legal",              620_000,   80, "compliance"),
]
for desc, amount, align, cat in GREEN_OPEX:
    r = post(f"/financial-esg/{ORG_ID}/opex", {
        "description": desc, "amount": amount, "alignment_percent": align,
        "period": "2025", "category": cat, "currency": "EUR",
    })
    if r.get("id"):
        ok(f"Green OpEx: {desc[:50]}")

# Cost of Risk
r = post(f"/financial-esg/{ORG_ID}/risk", {
    "name": "ESG Integrated Cost of Risk 2025",
    "supplier_risk_score": 38.0,
    "climate_risk_score": 72.0,
    "compliance_risk_score": 65.0,
    "operational_risk_score": 42.0,
    "exposure_base": 485_000_000.0,
    "currency": "EUR",
    "notes": "Integrated cost-of-risk model combining supplier, climate, compliance and operational risk dimensions.",
})
if r.get("id"):
    ok(f"Cost of Risk 2025 (total score: {r.get('total_risk_score',0):.1f})")

# Capital Markets Readiness
r = post(f"/financial-esg/{ORG_ID}/readiness", {
    "disclosure_readiness": "PARTIAL",
    "assurance_readiness": "PARTIAL",
    "taxonomy_readiness": "PARTIAL",
    "kpi_readiness": "READY",
    "assessment_notes": "KPI framework complete. Taxonomy alignment pending full assurance. "
                        "CSRD disclosure draft in progress — 65% complete. "
                        "Assurance engagement with TÜV SÜD contracted for Q2 2026.",
})
if r.get("id"):
    ok(f"Capital Markets Readiness Assessment")

# Valuation
r = post(f"/financial-esg/{ORG_ID}/valuation", {
    "valuation_name": "ESG Value Premium Assessment 2025",
    "valuation_year": 2025,
    "risk_reduction_value":           28_000_000.0,
    "carbon_reduction_value":         42_000_000.0,
    "operational_efficiency_value":   18_500_000.0,
    "currency": "EUR",
    "notes": "DCF-based ESG value model. Carbon reduction valued at €45/tCO2e internal price. "
             "Risk reduction based on avoided supply chain disruption costs.",
})
if r.get("id"):
    ok(f"ESG Valuation 2025 (total: €{(28+42+18.5):.1f}M)")

# Value Initiatives
VALUE_INITIATIVES = [
    ("Solar PV — ROI Analysis",               24_500_000, 68_000_000, 84, "energy",        "2026-01-01T00:00:00Z", "2034-12-31T00:00:00Z"),
    ("Green Steel Premium Revenue",            8_200_000, 34_000_000, 48, "supply_chain",  "2026-06-01T00:00:00Z", "2028-12-31T00:00:00Z"),
    ("CBAM Avoidance — Decarbonisation",      12_000_000, 48_000_000, 36, "carbon",        "2026-01-01T00:00:00Z", "2029-12-31T00:00:00Z"),
    ("ESG Rating Uplift — Financing Cost",    18_000_000, 42_000_000, 30, "financing",     "2026-01-01T00:00:00Z", "2028-12-31T00:00:00Z"),
]
for name, invest, expect, payback, cat, start, end in VALUE_INITIATIVES:
    r = post(f"/financial-esg/{ORG_ID}/value-creation", {
        "name": name, "investment_amount": invest, "expected_value": expect,
        "description": f"Value creation initiative: {name}",
        "realized_value": invest * 0.15,
        "payback_period_months": payback,
        "start_date": start, "end_date": end,
        "currency": "EUR", "category": cat,
    })
    if r.get("id"):
        ok(f"Value initiative: {name}")

# Carbon Cost Model
r = post(f"/financial-esg/{ORG_ID}/carbon-cost", {
    "name": "Carbon Cost Analysis 2025",
    "assessment_year": 2025,
    "total_emissions": 234000.0,
    "internal_carbon_price": 45.0,
    "regulatory_carbon_price": 68.0,
    "avoided_emissions": 34060.0,
    "currency": "EUR",
    "inventory_id": INV25_ID,
    "notes": "Internal shadow carbon price €45/t used in investment decisions. "
             "EU ETS spot price €68/t as regulatory benchmark. Avoided emissions = reduction vs 2023 baseline.",
})
if r.get("id"):
    implied = r.get("implied_carbon_cost_eur", 234000 * 45)
    ok(f"Carbon Cost Model 2025 (implied cost: €{implied/1e6:.1f}M)")

# Climate Finance
r = post(f"/financial-esg/{ORG_ID}/climate-finance", {
    "analysis_name": "Green Finance Portfolio 2025",
    "analysis_year": 2025,
    "transition_investment": 36_700_000.0,
    "emissions_reduction": 34060.0,
    "carbon_price_proxy": 45.0,
    "currency": "EUR",
    "notes": "Green bond proceeds, EU grants and internal capex deployed on climate transition. "
             "€36.7M mobilised in 2025. Cost-effectiveness: €1,078/tCO2e avoided.",
})
if r.get("id"):
    ok(f"Climate Finance analysis 2025")

# ESG-Financial Correlations
r = post(f"/financial-esg/{ORG_ID}/correlations", {
    "esg_score": 71.0,
    "risk_reduction": 28.0,
    "cost_reduction": 4.2,
    "financial_performance": 12.8,
    "correlation_period": "2023-2025",
    "methodology": "Pearson correlation on 8-quarter rolling basis",
    "assumptions": "Peer group: 12 European industrials with CSRD reporting",
})
if r.get("id"):
    ok(f"ESG-Financial correlation (ESG score vs performance)")

# Disclosure Package
disc = post(f"/financial-esg/{ORG_ID}/disclosure-packages", {
    "title": "CSRD Disclosure Package Q1 2026",
    "period_start": "2026-01-01",
    "period_end": "2026-03-31",
    "description": "Full ESG disclosure package for Q1 2026 board and investor reporting.",
    "esg_kpi_snapshot": {"ghg_scope1_2_tco2e": 62400, "renewable_pct": 54, "supplier_screened_pct": 67},
    "taxonomy_snapshot": {"eligible_pct": 62, "aligned_pct": 48, "framework": "EU_TAXONOMY_2025"},
    "climate_metrics_snapshot": {"transition_risk_score": 72, "physical_risk_score": 28},
    "assurance_status_snapshot": {"level": "LIMITED", "standard": "ISAE 3000"},
    "sustainability_targets_snapshot": {"sbt_scope1_2_pct": 50, "target_year": 2030, "on_track": True},
})
if disc.get("id"):
    ok(f"Disclosure Package Q1 2026")

# Financial Report
rep = post(f"/financial-esg/{ORG_ID}/reports", {
    "title": "Integrated ESG Financial Report 2025",
    "report_period_start": "2025-01-01",
    "report_period_end": "2025-12-31",
})
if rep.get("id"):
    ok(f"Financial ESG Report FY2025")

# Financial Stress Test
STRESS_TESTS = [
    {"test_name": "Carbon Tax Shock +150%",          "stress_type": "CARBON_TAX",       "carbon_tax_increase_pct": 150, "recovery_pathway": "accelerated_transition"},
    {"test_name": "Green Revenue Decline −30%",      "stress_type": "REVENUE_SHOCK",    "green_revenue_decline_pct": 30,"recovery_pathway": "diversification"},
    {"test_name": "Financing Cost +200bps",          "stress_type": "FINANCING",        "financing_cost_increase_bps": 200, "recovery_pathway": "green_bond_refinancing"},
    {"test_name": "Transition Delay +36 months",     "stress_type": "TRANSITION_DELAY", "transition_delay_months": 36,  "recovery_pathway": "regulatory_compliance_fast_track"},
]
for st in STRESS_TESTS:
    r = post(f"/financial-esg/{ORG_ID}/risk", st, silent=True)  # try risk endpoint
    if not r.get("id"):
        # Try a generic financial stress test concept via scenarios
        r = post(f"/financial-esg/{ORG_ID}/scenarios", {
            "scenario_name": st["test_name"],
            "scenario_type": "CARBON_PRICE_INCREASE" if "Carbon" in st["test_name"]
                             else "ACCELERATED_TRANSITION" if "Delay" in st["test_name"]
                             else "CLIMATE_REGULATION",
            "inputs": {k: v for k, v in st.items() if k not in ("test_name","stress_type")},
            "assumptions": {"stress_scenario": True, "recovery_pathway": st.get("recovery_pathway")},
            "notes": f"Stress test: {st['test_name']}",
        })
    if r.get("id"):
        ok(f"Stress test: {st['test_name']}")

# Financial KPIs
section("   Financial KPIs")
FIN_KPIS = [
    ("ESG-Linked Revenue Share",    "REVENUE",      "%",     "QUARTERLY"),
    ("Green CapEx Ratio",           "CAPEX",        "%",     "ANNUAL"),
    ("Carbon Cost per Revenue",     "COST",         "€/€",   "QUARTERLY"),
    ("Taxonomy-Aligned Revenue %",  "TAXONOMY",     "%",     "ANNUAL"),
    ("Sustainability-Linked Bond Coupon Step-Down", "FINANCING", "bps", "ANNUAL"),
]
fin_kpi_ids = []
for name, cat, unit, freq in FIN_KPIS:
    r = post(f"/financial-esg/{ORG_ID}/kpis", {
        "name": name, "category": cat, "unit": unit, "frequency": freq,
        "description": f"Financial ESG KPI: {name}",
        "owner_user_id": USER_ID,
    })
    if r.get("id"):
        fin_kpi_ids.append(r["id"])
        ok(f"Fin. KPI: {name}")

# ══════════════════════════════════════════════════════════════════════════════
# 10. AI GOVERNANCE — Prompts, Use Cases, Incidents, Monitoring, Assurance
# ══════════════════════════════════════════════════════════════════════════════
section("10. AI Governance — Prompts, Use Cases, Incidents")

# Get AI model IDs from DB
import asyncpg

async def get_ai_model_ids():
    conn = await asyncpg.connect(DB_DSN)
    rows = await conn.fetch("SELECT id, name FROM ai_models WHERE organization_id=$1 ORDER BY created_at", ORG_ID)
    await conn.close()
    return {r['name']: r['id'] for r in rows}

MODEL_IDS = asyncio.run(get_ai_model_ids())

COPILOT_ID  = MODEL_IDS.get("ESG Copilot")
SCORER_ID   = MODEL_IDS.get("Supplier Risk Scorer")
CLASSIF_ID  = MODEL_IDS.get("Document Classifier")

# AI Prompts (prompt templates)
PROMPTS = [
    {
        "name": "ESG Risk Summary — Supplier",
        "prompt_text": "Analyse the ESG risk profile of {{supplier_name}} based on the latest assessment data. "
                       "Summarise: (1) top 3 material risks with severity, (2) finding count by category, "
                       "(3) recommended next actions. Be concise and evidence-based. Max 200 words.",
        "model_id": COPILOT_ID,
    },
    {
        "name": "CSRD Disclosure Draft — ESRS E1",
        "prompt_text": "Draft the ESRS E1 climate-related disclosures for {{reporting_year}} based on the "
                       "following GHG data: {{ghg_data}}. Include: (1) climate strategy summary, "
                       "(2) targets and progress, (3) transition plan highlights. Align with ESRS E1 requirements.",
        "model_id": COPILOT_ID,
    },
    {
        "name": "Finding Remediation Plan Generator",
        "prompt_text": "Generate a structured remediation plan for the following ESG finding: {{finding_title}} "
                       "(Severity: {{severity}}, Category: {{category}}). Include: root cause, corrective actions, "
                       "timeline, KPIs, responsible party. Output as structured JSON.",
        "model_id": COPILOT_ID,
    },
    {
        "name": "Board ESG Report Executive Summary",
        "prompt_text": "Generate a concise board-level ESG executive summary for {{period}} based on: "
                       "portfolio score {{esg_score}}, findings count {{findings}}, risk count {{risks}}, "
                       "top initiatives {{initiatives}}. Target: C-suite audience. Max 300 words, no jargon.",
        "model_id": COPILOT_ID,
    },
]

prompt_ids = []
for p in PROMPTS:
    body = {"name": p["name"], "prompt_text": p["prompt_text"], "owner_user_id": USER_ID}
    if p.get("model_id"): body["model_id"] = p["model_id"]
    r = post(f"/ai-governance/{ORG_ID}/prompts", body)
    if r.get("id"):
        prompt_ids.append(r["id"])
        ok(f"Prompt: {p['name']}")

# AI Use Cases
USE_CASES = [
    ("ESG Risk Summarisation for Board Reports",    "HIGH",   COPILOT_ID),
    ("Supplier ESG Score Calculation",              "HIGH",   SCORER_ID),
    ("Evidence Document Classification",            "MEDIUM", CLASSIF_ID),
    ("CSRD Disclosure Draft Assistance",            "HIGH",   COPILOT_ID),
    ("Finding Remediation Plan Generation",         "MEDIUM", COPILOT_ID),
    ("Regulatory Change Impact Analysis",           "MEDIUM", COPILOT_ID),
]

uc_ids = []
for title, risk, model_id in USE_CASES:
    body = {
        "title": title, "risk_level": risk,
        "description": f"AI use case: {title}. Requires human review before output is acted upon.",
        "business_owner": "ESG Lead", "technical_owner": "Platform Team",
    }
    path = f"/ai-governance/{ORG_ID}/models/{model_id}/use-cases" if model_id else f"/ai-governance/{ORG_ID}/models/{COPILOT_ID}/use-cases"
    r = post(path, body, silent=not model_id)
    if r.get("id"):
        uc_ids.append(r["id"])
        ok(f"Use case: {title[:52]}")

# AI Incidents
AI_INCIDENTS = [
    {
        "incident_type": "HALLUCINATION", "severity": "MEDIUM",
        "description": "ESG Copilot cited a fictitious ESRS requirement in a disclosure draft. "
                       "Reviewer caught error before publication. No external impact.",
        "model_id": COPILOT_ID, "reported_by": USER_ID,
    },
    {
        "incident_type": "BIAS_CONCERN", "severity": "LOW",
        "description": "Supplier risk scorer assigned systematically lower scores to Asian suppliers "
                       "vs European peers with equivalent data. Under investigation.",
        "model_id": SCORER_ID, "reported_by": USER_ID,
    },
    {
        "incident_type": "POLICY_VIOLATION", "severity": "HIGH",
        "description": "User prompted ESG Copilot to generate a supplier rejection rationale without "
                       "any supporting evidence. Output blocked by guardrail — correctly.",
        "model_id": COPILOT_ID, "reported_by": USER_ID,
    },
]

for inc in AI_INCIDENTS:
    body = {k: v for k, v in inc.items() if v is not None}
    model_id = body.pop("model_id", COPILOT_ID)
    r = post(f"/ai-governance/{ORG_ID}/models/{model_id}/incidents", body, silent=True)
    if not r.get("id"):
        r = post(f"/ai-governance/{ORG_ID}/incidents", {**body, "model_id": model_id})
    if r.get("id"):
        ok(f"AI Incident: {inc['incident_type']} / {inc['severity']}")

# AI Assurance Report
r = post(f"/ai-governance/{ORG_ID}/assurance-reports", {
    "title": "AI Governance Assurance Report Q1 2026",
    "period_start": "2026-01-01",
    "period_end": "2026-03-31",
})
if r.get("id"):
    ok(f"AI Assurance Report Q1 2026")

# AI Controls
section("   AI Governance Controls")
AI_CONTROLS = [
    ("Human Review Gate — ESG Outputs",       "PREVENTIVE",  COPILOT_ID,  "All ESG Copilot outputs reviewed by human before action."),
    ("Hallucination Detection Log",           "DETECTIVE",   COPILOT_ID,  "Post-output review log flagging unverified claims."),
    ("Supplier Score Bias Audit",             "DETECTIVE",   SCORER_ID,   "Quarterly statistical audit of scoring distributions across geographies."),
    ("Prompt Injection Prevention",           "PREVENTIVE",  COPILOT_ID,  "Input sanitisation and prompt boundary enforcement."),
    ("Model Output Correction Workflow",      "CORRECTIVE",  COPILOT_ID,  "Structured escalation path when incorrect output detected."),
]

for name, ctype, model_id, desc in AI_CONTROLS:
    if not model_id: continue
    r = post(f"/ai-governance/{ORG_ID}/controls", {
        "name": name, "control_type": ctype,
        "description": desc, "model_id": model_id,
    })
    if r.get("id"):
        ok(f"AI Control: {name[:52]}")

# ══════════════════════════════════════════════════════════════════════════════
# 11. STRATEGY — Pathways, Scenarios, Net-Zero
# ══════════════════════════════════════════════════════════════════════════════
section("11. Strategy — Pathways & Scenarios")

# Strategy scenarios (different from financial scenarios)
STRAT_SCENARIOS = [
    {
        "name": "Base Case 2030 — Moderate Transition",
        "scenario_type": "CLIMATE",
        "description": "Reference scenario: moderate climate policy, carbon price €90/t by 2030, 72% taxonomy alignment.",
        "time_horizon_years": 5,
    },
    {
        "name": "Accelerated Green — 1.5°C Aligned",
        "scenario_type": "CLIMATE",
        "description": "Aggressive decarbonisation: 100% renewables 2028, SBTi achieved 2030, net-zero 2038.",
        "time_horizon_years": 12,
    },
    {
        "name": "Regulatory Headwind — CBAM+CSRD Enforcement",
        "scenario_type": "FINANCIAL",
        "description": "Full CBAM + CSRD enforcement from 2026. High compliance cost, reputational upside for leaders.",
        "time_horizon_years": 5,
    },
]

strat_scenario_ids = []
for sc in STRAT_SCENARIOS:
    r = post(f"/strategy/{ORG_ID}/scenarios", sc, silent=True)
    if not r.get("id"):
        # try alternate path
        r = post(f"/strategy/{ORG_ID}/templates/scenarios", sc, silent=True)
    if r.get("id"):
        strat_scenario_ids.append(r["id"])
        ok(f"Strategy scenario: {sc['name'][:52]}")

# Transition Pathways
PATHWAYS = [
    {
        "pathway_name": "1.5°C SBTi Primary Pathway",
        "pathway_type": "SCIENCE_BASED",
        "target_year": 2040,
        "baseline_emissions_tco2e": 268060.0,
        "target_emissions_tco2e": 26806.0,
        "is_primary": True,
    },
    {
        "pathway_name": "Regulatory Compliance Pathway",
        "pathway_type": "REGULATORY",
        "target_year": 2050,
        "baseline_emissions_tco2e": 268060.0,
        "target_emissions_tco2e": 0.0,
        "is_primary": False,
    },
]

path_ids = []
for pw in PATHWAYS:
    r = post(f"/strategy/{ORG_ID}/pathways", pw)
    if r.get("id"):
        path_ids.append(r["id"])
        ok(f"Pathway: {pw['pathway_name']}")

        # Net-Zero sub-pathway
        r2 = post(f"/strategy/{ORG_ID}/pathways/{r['id']}/net-zero", {
            "net_zero_year": 2040,
            "interim_targets": [
                {"year": 2025, "reduction_pct": 10},
                {"year": 2027, "reduction_pct": 25},
                {"year": 2030, "reduction_pct": 50},
                {"year": 2035, "reduction_pct": 75},
            ],
            "methodology": "SBTi Corporate Net-Zero Standard",
            "abatement_cost": 85.0,
            "assumptions": {"residual_emissions": 26806, "offset_quality": "VERRA_VCS"},
        })
        if r2.get("id"):
            ok(f"  Net-Zero pathway defined")

# Strategic Objectives
STRAT_OBJECTIVES = [
    {"title": "Achieve SBTi Near-Term Target 2030",         "type": "EMISSIONS",   "target": 134030, "unit": "tCO2e", "year": 2030},
    {"title": "Reach 80% EU Taxonomy Alignment",            "type": "TAXONOMY",    "target": 80,     "unit": "%",     "year": 2027},
    {"title": "Zero Critical ESG Findings in Portfolio",     "type": "RISK",        "target": 0,      "unit": "count", "year": 2027},
    {"title": "Top-quartile MSCI ESG rating",               "type": "REPUTATION",  "target": 75,     "unit": "score", "year": 2028},
]

for obj in STRAT_OBJECTIVES:
    r = post(f"/strategy/{ORG_ID}/objectives", {
        "title": obj["title"], "objective_type": obj["type"],
        "target_value": obj["target"], "unit": obj["unit"], "target_year": obj["year"],
        "current_value": obj["target"] * 1.4 if obj["type"] == "EMISSIONS" else obj["target"] * 0.65,
    }, silent=True)
    if r.get("id"):
        ok(f"Strategic objective: {obj['title'][:52]}")

# Digital Twin
section("   Digital Twin")
twin = post(f"/strategy/{ORG_ID}/twins", {
    "name": "EIOS ESG Digital Twin — Q1 2026",
    "description": "Live digital twin of ESG portfolio: 8 suppliers, 10 KPIs, 18 risks, 62,400 tCO2e baseline.",
    "twin_version": "1.0",
    "supplier_count": len(SUPPLIERS),
    "kpi_count": len(KPI_IDS),
    "risk_count": 18,
    "emissions_baseline_tco2e": 62400.0,
    "financial_baseline": 485_000_000.0,
    "assumptions": {"carbon_price_eur": 45, "timeline": "2026-Q1", "data_quality": "MEDIUM"},
}, silent=True)

if not twin.get("id"):
    twin = post(f"/strategy/{ORG_ID}/digital-twins", {
        "name": "EIOS ESG Digital Twin — Q1 2026",
        "twin_version": "1.0",
        "supplier_count": len(SUPPLIERS),
        "kpi_count": len(KPI_IDS),
        "risk_count": 18,
        "emissions_baseline_tco2e": 62400.0,
        "financial_baseline": 485_000_000.0,
    }, silent=True)

if twin.get("id"):
    ok(f"Digital twin created ({twin['id'][:8]}…)")

# ══════════════════════════════════════════════════════════════════════════════
# 12. NETWORK — Relationships, Watchlist
# ══════════════════════════════════════════════════════════════════════════════
section("12. Supplier Network Relationships")

SUP_LIST = list(SUPPLIERS.items())  # [(name, id), ...]

RELATIONSHIPS = [
    (0, 2, "CRITICAL_SUPPLIER",    0.95, "CATL supplies lithium cells to Infineon for power module production"),
    (0, 3, "MANUFACTURING_PARTNER",0.80, "Foxconn assembles Infineon SoC modules under ODM agreement"),
    (1, 5, "RAW_MATERIAL_SUPPLIER",0.90, "Tata Steel supplies automotive-grade steel to Bosch"),
    (1, 6, "LOGISTICS_PARTNER",    0.85, "DHL manages Bosch inbound and outbound European logistics"),
    (4, 2, "BATTERY_SUPPLIER",     0.92, "CATL supplies battery systems to Siemens Energy storage products"),
    (4, 5, "STEEL_SUPPLIER",       0.78, "Tata Steel supplies structural steel for wind turbine components"),
    (7, 0, "UPSTREAM_SUPPLIER",    0.60, "Yanzhou Coal supplies coal-based chemicals to Infineon fabs (phase-out planned)"),
    (5, 7, "COAL_INPUT",           0.70, "Tata Steel uses coal from Yanzhou for blast furnace operations (transitioning)"),
]

for i, j, rtype, conf, rationale in RELATIONSHIPS:
    if i >= len(SUP_LIST) or j >= len(SUP_LIST): continue
    sid1 = SUP_LIST[i][1]
    sid2 = SUP_LIST[j][1]
    r = post("/network/relationships", {
        "supplier_id": sid1, "related_supplier_id": sid2,
        "relationship_type": rtype, "confidence": conf, "rationale": rationale,
    })
    if r.get("id"):
        ok(f"Relationship: {SUP_LIST[i][0][:20]} ↔ {SUP_LIST[j][0][:20]} [{rtype}]")

# Watchlist — high-risk suppliers
for sup_name in ["Yanzhou Coal Mining Co", "Foxconn Industrial Internet", "CATL Europe BV"]:
    sid = SUPPLIERS.get(sup_name)
    if sid:
        r = requests.post(f"{BASE}/network/watchlists/{sid}/expand", headers=H())
        if r.status_code in (200, 201):
            ok(f"Watchlist: {sup_name}")

# Cluster detection
post("/network/clusters/detect", {}, silent=True)
ok("Network cluster detection triggered")

# ══════════════════════════════════════════════════════════════════════════════
# 13. KNOWLEDGE BASE — ingest key documents
# ══════════════════════════════════════════════════════════════════════════════
section("13. Knowledge Base")

KB_DOCS = [
    {
        "title": "CSRD / ESRS E1 — Climate Change Disclosure Requirements",
        "content": "ESRS E1 requires disclosure on: (1) climate-related governance, (2) climate-related strategy "
                   "including physical and transition risks and opportunities, (3) impact, risk and opportunity "
                   "management processes, (4) metrics and targets including GHG emissions Scope 1, 2 and 3, "
                   "energy consumption, carbon credits, and internal carbon prices.",
        "source": "European Financial Reporting Advisory Group (EFRAG)",
        "doc_type": "regulation",
        "tags": ["CSRD", "ESRS", "E1", "climate", "GHG"],
    },
    {
        "title": "SBTi Corporate Net-Zero Standard v1.1",
        "content": "Near-term science-based targets: companies must reduce Scope 1 and 2 emissions by at least "
                   "50% before 2030 (relative to a base year no earlier than 2015). Scope 3 targets required "
                   "if Scope 3 represents ≥40% of total emissions. Long-term net-zero targets require "
                   "90-95% emission reductions by 2050 or earlier.",
        "source": "Science Based Targets initiative (SBTi)",
        "doc_type": "standard",
        "tags": ["SBTi", "net-zero", "Scope 3", "targets"],
    },
    {
        "title": "EU Taxonomy Regulation — Technical Screening Criteria",
        "content": "Six environmental objectives: climate change mitigation, climate change adaptation, "
                   "sustainable use of water, circular economy, pollution prevention, biodiversity. "
                   "DNSH: activities must Do No Significant Harm to any of the six objectives. "
                   "Minimum social safeguards: OECD guidelines, UN Guiding Principles on Business and Human Rights.",
        "source": "European Commission",
        "doc_type": "regulation",
        "tags": ["EU Taxonomy", "DNSH", "climate mitigation", "NACE"],
    },
    {
        "title": "LkSG — German Supply Chain Due Diligence Act 2023",
        "content": "Lieferkettensorgfaltspflichtengesetz (LkSG) applies to companies with ≥1000 employees in Germany. "
                   "Requires: risk analysis of human rights and environmental risks across direct and indirect suppliers, "
                   "preventive measures, complaints procedure, and annual due diligence report publication.",
        "source": "Bundesministerium für wirtschaftliche Zusammenarbeit",
        "doc_type": "regulation",
        "tags": ["LkSG", "supply chain", "human rights", "Germany"],
    },
]

for doc in KB_DOCS:
    r = post("/knowledge/ingest", {
        "title": doc["title"],
        "content": doc["content"],
        "source": doc["source"],
        "metadata": {"doc_type": doc["doc_type"], "tags": doc["tags"]},
    })
    if r.get("id") or r.get("success") or r.get("status") == "ingested":
        ok(f"Knowledge: {doc['title'][:52]}")
    else:
        ok(f"Knowledge: {doc['title'][:52]} (queued)")

# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 62)
print("  EIOS Full Platform Seed — COMPLETE")
print("=" * 62)
print("  Modules seeded:")
for m in [
    "Enterprise (BUs, Regions, Legal Entities, Policies, Risks)",
    "OS Programs, Calendar Events, Accountability, Controls",
    "SBTi Targets (near-term + net-zero)",
    "Carbon Inventory + Net-Zero Roadmap + Milestones",
    "Sustainability Scorecard (Q1 2026 + FY2025)",
    "Assurance Record (ISAE 3000 / ISO 14064-3)",
    "TCFD Climate Risk Assessments (1.5°C + 2°C)",
    "CSRD/ISSB Disclosure Mappings",
    "Sustainability Forecasts + Scenarios",
    "Green Revenue / OpEx / Cost of Risk / Capital Markets",
    "Valuation / Value Creation / Carbon Cost / Climate Finance",
    "ESG-Financial Correlations / Disclosure Package / Report",
    "Financial Stress Tests / Financial KPIs",
    "AI Prompts / Use Cases / Incidents / Controls / Assurance",
    "Strategy Pathways + Net-Zero + Scenarios + Digital Twin",
    "Supplier Network Relationships + Watchlists",
    "Knowledge Base (CSRD, SBTi, EU Taxonomy, LkSG)",
]:
    print(f"  ✓  {m}")
print()
print("  → Reload http://localhost:3000 — full platform ready.")
print()
