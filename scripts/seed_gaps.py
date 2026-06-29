"""
EIOS Demo Gap-Fill Script
Fills: assessments/findings/risks (supplier-linked), certificates,
       financial scenarios, comments, pentest findings (direct DB),
       AI models/policies (direct DB).
"""

import asyncio
import uuid
import requests
from datetime import datetime, timezone

BASE = "http://localhost:8000/api/v1"
EMAIL = "ayhan.yaman1@icloud.com"
PASSWORD = "Founder2026!"
DB_DSN = "postgresql://eios:eios_dev@localhost:5432/eios_db"
ORG_ID = "7816af5e-1542-4658-9548-a800ec4c8e38"
USER_ID = "bcda5715-b077-4c73-b361-207ba0181e25"

def login():
    r = requests.post(f"{BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    r.raise_for_status()
    return r.json()["access_token"]

TOKEN = login()

def h():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def post(path, body, silent=False):
    r = requests.post(f"{BASE}{path}", json=body, headers=h())
    if not silent and r.status_code not in (200, 201):
        print(f"  WARN {path}: {r.status_code} {r.text[:120]}")
    try:
        return r.json()
    except Exception:
        return {}

def ok(label):
    print(f"  ✓  {label}")

# ── Fetch existing suppliers ──────────────────────────────────────────────────
r = requests.get(f"{BASE}/suppliers/?page_size=20", headers=h())
raw = r.json()
items = raw if isinstance(raw, list) else raw.get("items", raw.get("data", []))
SUPPLIERS = {s["name"]: s["id"] for s in items}
print(f"\n── Fetched {len(SUPPLIERS)} existing suppliers")

# ══════════════════════════════════════════════════════════════════════════════
# A. ASSESSMENTS + FINDINGS + RISKS per supplier
# ══════════════════════════════════════════════════════════════════════════════
print("\n── A. Assessments / Findings / Risks ─────────────────────────────────────")

PLANS = [
    {
        "supplier": "Infineon Technologies AG",
        "assessment": {"title": "ESG Risk Assessment Q1 2026",
                       "description": "Full ESG risk review — environmental, social, governance dimensions. Q1 2026.",
                       "scope": "E+S+G risk review", "assessment_type": "esg"},
        "findings": [
            {"title": "Carbon emissions 18% above semiconductor sector benchmark", "severity": "High",     "category": "Environmental"},
            {"title": "Supplier code of conduct not enforced at Tier-2",           "severity": "Medium",   "category": "Social"},
            {"title": "No Scope 3 Category 1 emissions disclosure",                "severity": "Medium",   "category": "Environmental"},
        ],
        "risks": [
            {"title": "Climate transition risk — fab energy intensity",  "level": "High",    "cat": "Climate",       "prob": 0.55, "impact": 0.75},
            {"title": "Reputational risk from Tier-2 labour practices",  "level": "Medium",  "cat": "Reputational",  "prob": 0.35, "impact": 0.60},
        ],
    },
    {
        "supplier": "Bosch Automotive GmbH",
        "assessment": {"title": "CSRD Readiness Assessment 2026",
                       "description": "CSRD / ESRS gap analysis before June 2026 reporting deadline. Scope: all ESRS standards.",
                       "scope": "CSRD / ESRS gap analysis", "assessment_type": "compliance"},
        "findings": [
            {"title": "ESRS E1 climate reporting gaps — no physical risk analysis", "severity": "Critical", "category": "Compliance"},
            {"title": "Double materiality assessment only 40% complete",            "severity": "High",     "category": "Governance"},
        ],
        "risks": [
            {"title": "Regulatory non-compliance penalty under CSRD", "level": "Critical", "cat": "Compliance", "prob": 0.70, "impact": 0.90},
        ],
    },
    {
        "supplier": "CATL Europe BV",
        "assessment": {"title": "Battery Supply Chain Due Diligence",
                       "description": "Cobalt & lithium sourcing risk — human rights and environmental review per LkSG.",
                       "scope": "Critical mineral supply chain", "assessment_type": "esg"},
        "findings": [
            {"title": "Cobalt sourcing from DRC without third-party audit",  "severity": "Critical", "category": "Social"},
            {"title": "Water discharge standards exceed EU limits at site 3", "severity": "High",     "category": "Environmental"},
            {"title": "No living wage commitment for contract workers",        "severity": "Medium",   "category": "Social"},
        ],
        "risks": [
            {"title": "Forced labour risk in cobalt supply chain",       "level": "Critical", "cat": "Human Rights",  "prob": 0.60, "impact": 0.95},
            {"title": "Environmental violation — EU Water Framework Dir.", "level": "High",    "cat": "Environmental", "prob": 0.50, "impact": 0.80},
        ],
    },
    {
        "supplier": "Foxconn Industrial Internet",
        "assessment": {"title": "Human Rights Due Diligence 2026",
                       "description": "LkSG-aligned human rights assessment — labour conditions, grievance mechanisms, living wage.",
                       "scope": "Labour rights & social standards", "assessment_type": "esg"},
        "findings": [
            {"title": "Excessive working hours documented (>60h/week)",      "severity": "Critical", "category": "Social"},
            {"title": "Grievance mechanism not accessible to migrant workers","severity": "High",     "category": "Governance"},
            {"title": "Living wage gap: 23% below living wage benchmark",     "severity": "High",     "category": "Social"},
        ],
        "risks": [
            {"title": "Supply chain disruption from labour unrest",       "level": "High",    "cat": "Operational",  "prob": 0.45, "impact": 0.85},
            {"title": "Regulatory sanctions under LkSG",                  "level": "Critical","cat": "Compliance",   "prob": 0.55, "impact": 0.90},
        ],
    },
    {
        "supplier": "Siemens Energy AG",
        "assessment": {"title": "Climate Transition Risk Assessment",
                       "description": "Physical and transition climate risk assessment under TCFD framework.",
                       "scope": "TCFD climate risk — physical & transition", "assessment_type": "esg"},
        "findings": [
            {"title": "Flood risk at Hamburg turbine plant — no mitigation plan", "severity": "High",   "category": "Environmental"},
            {"title": "Gas turbine backlog creates stranded asset risk by 2035",  "severity": "Medium", "category": "Governance"},
        ],
        "risks": [
            {"title": "Physical climate risk — asset damage from flooding",  "level": "High",    "cat": "Climate",       "prob": 0.40, "impact": 0.80},
            {"title": "Stranded asset risk — gas turbine portfolio 2035",    "level": "Medium",  "cat": "Climate",       "prob": 0.50, "impact": 0.65},
        ],
    },
    {
        "supplier": "Tata Steel Europe Ltd",
        "assessment": {"title": "Steel Decarbonisation Readiness",
                       "description": "Green steel transition readiness — hydrogen DRI, CBAM exposure, SBTi alignment.",
                       "scope": "Decarbonisation & CBAM exposure", "assessment_type": "esg"},
        "findings": [
            {"title": "No SBTi target submitted — 2 years overdue",          "severity": "Critical", "category": "Environmental"},
            {"title": "CBAM exposure estimated €12M/year from 2026",         "severity": "High",     "category": "Compliance"},
            {"title": "Hydrogen DRI pilot delayed 18 months",                "severity": "Medium",   "category": "Environmental"},
        ],
        "risks": [
            {"title": "CBAM cost exposure — steel imports to EU",            "level": "High",    "cat": "Regulatory",   "prob": 0.95, "impact": 0.75},
            {"title": "Competitive disadvantage vs green steel producers",   "level": "High",    "cat": "Strategic",    "prob": 0.65, "impact": 0.70},
        ],
    },
]

assessment_ids = []
finding_ids = []
risk_ids = []

for plan in PLANS:
    sid = SUPPLIERS.get(plan["supplier"])
    if not sid:
        print(f"  SKIP (supplier not found): {plan['supplier']}")
        continue

    a = post("/assessments/", {**plan["assessment"], "supplier_id": sid})
    aid = a.get("id")
    if not aid:
        continue

    assessment_ids.append(aid)
    ok(f"Assessment: {plan['assessment']['title'][:38]} — {plan['supplier'][:22]}")

    for f in plan["findings"]:
        fr = post("/findings/", {
            "title": f["title"],
            "severity": f["severity"],
            "category": f["category"],
            "description": f"Finding from {plan['assessment']['title']}. Impact on {plan['supplier']}. Remediation required.",
            "assessment_id": aid,
        })
        if fr.get("id"):
            finding_ids.append(fr["id"])

    for rv in plan["risks"]:
        rr = post("/risks/", {
            "title": rv["title"],
            "description": f"Risk identified during {plan['assessment']['title']} for {plan['supplier']}.",
            "risk_level": rv["level"],
            "category": rv["cat"],
            "assessment_id": aid,
            "probability": rv["prob"],
            "impact": rv["impact"],
        })
        if rr.get("id"):
            risk_ids.append(rr["id"])

print(f"  → {len(assessment_ids)} assessments, {len(finding_ids)} findings, {len(risk_ids)} risks")

# ══════════════════════════════════════════════════════════════════════════════
# B. SUPPLIER CERTIFICATES
# ══════════════════════════════════════════════════════════════════════════════
print("\n── B. Supplier Certificates ──────────────────────────────────────────────")

CERTS = [
    ("Infineon Technologies AG",    "ISO 14001:2015 Environmental Mgmt", "ISO_14001", "TÜV Rheinland",  "2027-06-30T00:00:00Z"),
    ("Bosch Automotive GmbH",       "ISO 9001:2015 Quality Management",  "ISO_9001",  "DNV GL",          "2026-12-31T00:00:00Z"),
    ("CATL Europe BV",              "SA8000 Social Accountability",      "SA8000",    "Bureau Veritas",  "2026-09-30T00:00:00Z"),
    ("Foxconn Industrial Internet", "RBA Code of Conduct Certification", "RBA_COC",   "RBA",             "2026-06-30T00:00:00Z"),
    ("Siemens Energy AG",           "ISO 50001:2018 Energy Management",  "ISO_50001", "TÜV SÜD",         "2027-03-31T00:00:00Z"),
    ("Tata Steel Europe Ltd",       "ISO 14001:2015 Environmental Mgmt", "ISO_14001", "Lloyd's Register","2027-01-31T00:00:00Z"),
    ("DHL Supply Chain GmbH",       "ISO 45001:2018 OHS Management",     "ISO_45001", "SGS",             "2026-11-30T00:00:00Z"),
]

for sup_name, cert_name, cert_type, issuer, expires in CERTS:
    sid = SUPPLIERS.get(sup_name)
    if not sid:
        continue
    r = post(f"/suppliers/{sid}/certificates", {
        "name": cert_name,
        "cert_type": cert_type,
        "expires_at": expires,
        "issued_at": "2024-07-01T00:00:00Z",
        "issuer": issuer,
        "certificate_number": f"{cert_type}-2024-{abs(hash(sup_name)) % 90000 + 10000}",
        "alert_days_before": 90,
        "notes": f"Verified by {issuer}. Valid and active.",
    })
    if r.get("id"):
        ok(f"{cert_type} — {sup_name[:30]}")

# ══════════════════════════════════════════════════════════════════════════════
# C. FINANCIAL SCENARIOS (valid types)
# ══════════════════════════════════════════════════════════════════════════════
print("\n── C. Financial ESG Scenarios ────────────────────────────────────────────")

# Valid types: CARBON_PRICE_INCREASE | SUPPLIER_DISRUPTION | CLIMATE_REGULATION | ACCELERATED_TRANSITION
SCENARIOS = [
    {
        "scenario_name": "Carbon Price Surge to €150/tCO2e by 2030",
        "scenario_type": "CARBON_PRICE_INCREASE",
        "inputs": {"carbon_price_start_eur": 50, "carbon_price_end_eur": 150, "timeline_years": 5},
        "assumptions": {"policy": "EU ETS reform Phase 5", "scope": "Scope 1+2 + CBAM"},
        "notes": "Models P&L impact if EU carbon price reaches €150 by 2030 under ETS reform.",
    },
    {
        "scenario_name": "Critical Mineral Supply Disruption — China Export Ban",
        "scenario_type": "SUPPLIER_DISRUPTION",
        "inputs": {"affected_materials": ["lithium", "cobalt", "rare_earths"], "disruption_months": 18, "revenue_at_risk_pct": 23},
        "assumptions": {"trigger": "China export controls", "geographic_concentration": 0.74},
        "notes": "Models impact of 18-month supply disruption from Chinese export controls on critical minerals.",
    },
    {
        "scenario_name": "CSRD + CBAM Full Enforcement 2026",
        "scenario_type": "CLIMATE_REGULATION",
        "inputs": {"cbam_cost_eur": 12_000_000, "csrd_compliance_cost_eur": 800_000, "enforcement_year": 2026},
        "assumptions": {"full_enforcement": True, "mandatory_assurance": True, "penalty_risk_eur": 2_800_000},
        "notes": "Models combined regulatory cost impact of CSRD + CBAM coming into full force in 2026.",
    },
    {
        "scenario_name": "Accelerated Green Transition — Net-Zero by 2035",
        "scenario_type": "ACCELERATED_TRANSITION",
        "inputs": {"renewable_share_target": 100, "ev_fleet_pct": 100, "green_capex_eur": 180_000_000},
        "assumptions": {"timeline": "2035", "financing": "green_bonds_and_eu_grants", "capex_recovery_years": 8},
        "notes": "Best-case accelerated transition scenario — full decarbonisation achieved 5 years ahead of base plan.",
    },
]

for sc in SCENARIOS:
    r = post(f"/financial-esg/{ORG_ID}/scenarios", sc)
    if r.get("id"):
        ok(sc["scenario_name"][:60])

# ══════════════════════════════════════════════════════════════════════════════
# D. COMMENTS (correct entity_type capitalisation)
# ══════════════════════════════════════════════════════════════════════════════
print("\n── D. Comments ───────────────────────────────────────────────────────────")

FINDING_COMMENTS = [
    "Initial triage completed — escalated to ESG Lead. Supplier notified on 2026-04-10.",
    "Root cause confirmed: no enforced monitoring at Tier-2 level. CAP submitted by supplier.",
    "Third-party verification scheduled with TÜV for 2026-06-15. Interim controls applied.",
    "Closed pending final TÜV sign-off. Risk downgraded from Critical to High in interim.",
    "Remediation plan approved by ESG committee. €180k budget allocated. Target: 2026-09-30.",
]

RISK_COMMENTS = [
    "Risk accepted by board with condition: quarterly review and mitigation budget €500k.",
    "Mitigation strategy approved: green procurement + SBTi submission by Q3 2026.",
    "Escalated to CEO due to CBAM cost materialisation sooner than modelled. Board informed.",
]

for i, fid in enumerate(finding_ids[:5]):
    r = post("/comments/", {
        "entity_type": "Finding",
        "entity_id": fid,
        "content": FINDING_COMMENTS[i % len(FINDING_COMMENTS)],
    })
    if r.get("id"):
        ok(f"Comment on finding #{i+1}")

for i, rid in enumerate(risk_ids[:3]):
    r = post("/comments/", {
        "entity_type": "Risk",
        "entity_id": rid,
        "content": RISK_COMMENTS[i % len(RISK_COMMENTS)],
    })
    if r.get("id"):
        ok(f"Comment on risk #{i+1}")

# ══════════════════════════════════════════════════════════════════════════════
# E. DIRECT DB — Pentest Findings + AI Models/Policies
# ══════════════════════════════════════════════════════════════════════════════
print("\n── E. Pentest Findings + AI Models (direct DB) ───────────────────────────")

import asyncpg

async def seed_db():
    conn = await asyncpg.connect(DB_DSN)
    now = datetime.now(timezone.utc)

    PENTEST = [
        ("A01", "Insecure Direct Object Reference — Supplier Document API",  "HIGH",     "OPEN",       7.8, "Attacker can access any supplier document by changing ID parameter in URL. No authorization check.", "Implement object-level authorization. Validate resource ownership on every request."),
        ("A07", "Missing rate limiting on /auth/login endpoint",              "MEDIUM",   "REMEDIATED", 5.4, "No brute-force protection on authentication endpoint. 1000+ login attempts per minute possible.", "Implement rate limiting (10 req/min per IP). Add progressive delay and account lockout."),
        ("A03", "Stored XSS in report export filename parameter",             "MEDIUM",   "OPEN",       5.4, "Report filename field renders unsanitized in download dialog. Stored XSS via crafted filename.", "Apply output encoding. Use allowlist for filename characters. Add CSP header."),
        ("A09", "Partial auth tokens logged in application server logs",      "HIGH",     "IN_PROGRESS",7.2, "First 32 chars of JWT access tokens logged in INFO level. Logs accessible to operations team.", "Redact all tokens from logs. Implement structured logging with field-level filtering."),
        ("A02", "Password policy: no complexity requirement enforced",        "MEDIUM",   "OPEN",       4.3, "Users can set passwords as short as 6 chars with no complexity requirement. Weak credential risk.", "Enforce minimum 12 chars, mixed case, digit and special character. Add HaveIBeenPwned check."),
        ("A05", "Security misconfiguration — debug mode on staging endpoint", "HIGH",     "OPEN",       6.8, "Staging /debug endpoint accessible without auth. Returns stack traces and internal config.", "Disable debug endpoints in all environments. Enforce env-specific config management."),
        ("A06", "Outdated dependency: PyJWT 2.6.0 — CVE-2022-29217",        "HIGH",     "REMEDIATED", 7.5, "Outdated PyJWT version with known algorithm confusion vulnerability. Upgrade required.", "Upgrade PyJWT to ≥2.8.0. Run automated dependency scanning in CI pipeline."),
        ("A10", "SSRF risk in external URL fetch for evidence ingestion",     "HIGH",     "OPEN",       7.1, "Evidence URL field allows fetching from internal network addresses. SSRF possible via 169.254.x.x.", "Validate and allowlist URL schemes and hosts. Block RFC1918 and link-local ranges."),
    ]

    for owasp, title, sev, status, cvss, desc, remed in PENTEST:
        fid = str(uuid.uuid4())
        try:
            await conn.execute("""
                INSERT INTO pentest_findings
                    (id, organization_id, owasp_category, title, severity, status,
                     cvss_score, description, remediation_notes, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT DO NOTHING
            """, fid, ORG_ID, owasp, title, sev, status, cvss, desc, remed, now, now)
            ok(f"{owasp} {title[:50]}")
        except Exception as e:
            print(f"  ERR pentest {owasp}: {e}")

    print()

    AI_MODELS = [
        ("ESG Copilot",               "Anthropic",  "LLM",           "Q&A, analysis and drafting for ESG workflows",    "Production"),
        ("Supplier Risk Scorer",      "Internal",   "RISK_SCORING",  "Deterministic ESG risk scoring (M43)",            "Production"),
        ("Document Classifier",       "Internal",   "CLASSIFICATION","Evidence document type and relevance classifier", "Production"),
        ("KPI Forecast Engine",       "Internal",   "FORECASTING",   "KPI and emissions trend forecasting (M44)",       "Production"),
        ("Embedding Index",           "Anthropic",  "EMBEDDING",     "Semantic search for knowledge base queries",      "Production"),
    ]

    model_ids = []
    for name, provider, mtype, purpose, status in AI_MODELS:
        mid = str(uuid.uuid4())
        try:
            await conn.execute("""
                INSERT INTO ai_models
                    (id, organization_id, name, provider, model_type, purpose,
                     ai_status, version, owner_user_id, created_by, updated_by, created_at, updated_at, metadata)
                VALUES ($1,$2,$3,$4,$5,$6,$7,1,$8,$9,$10,$11,$12,$13)
                ON CONFLICT DO NOTHING
            """, mid, ORG_ID, name, provider, mtype, purpose, status,
                USER_ID, USER_ID, USER_ID, now, now, '{"version":"1.0"}')
            model_ids.append(mid)
            ok(f"AI Model: {name}")
        except Exception as e:
            print(f"  ERR ai_model {name}: {e}")

    print()

    AI_POLICIES = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='ai_policies' ORDER BY ordinal_position")
    policy_cols = [c['column_name'] for c in AI_POLICIES]

    POLICIES = [
        ("Approved AI Providers Policy",   "APPROVED_PROVIDERS",   "Lists vetted AI providers. Only Anthropic and internal models approved."),
        ("Prohibited AI Use Cases",        "PROHIBITED_USE_CASES", "No autonomous approvals, no rejection of suppliers without human review."),
        ("AI Model Review Requirements",   "REVIEW_REQUIREMENTS",  "All production models reviewed every 6 months by CTO + ESG Lead."),
        ("Data Retention for AI Logs",     "RETENTION",            "AI inference logs retained 24 months. PII must be excluded from prompts."),
    ]

    for pname, ptype, pdesc in POLICIES:
        pid = str(uuid.uuid4())
        try:
            if 'policy_type' in policy_cols and 'description' in policy_cols:
                await conn.execute("""
                    INSERT INTO ai_policies
                        (id, organization_id, name, policy_type, description,
                         version, created_by, updated_by, created_at, updated_at)
                    VALUES ($1,$2,$3,$4,$5,1,$6,$7,$8,$9)
                    ON CONFLICT DO NOTHING
                """, pid, ORG_ID, pname, ptype, pdesc, USER_ID, USER_ID, now, now)
            else:
                await conn.execute("""
                    INSERT INTO ai_policies (id, organization_id, name, version, created_by, updated_by, created_at, updated_at)
                    VALUES ($1,$2,$3,1,$4,$5,$6,$7)
                    ON CONFLICT DO NOTHING
                """, pid, ORG_ID, pname, USER_ID, USER_ID, now, now)
            ok(f"AI Policy: {pname}")
        except Exception as e:
            print(f"  ERR ai_policy {pname}: {e}")

    await conn.close()

asyncio.run(seed_db())

# ══════════════════════════════════════════════════════════════════════════════
# DONE
# ══════════════════════════════════════════════════════════════════════════════
print()
print("=" * 62)
print("  EIOS Gap-Fill — COMPLETE")
print("=" * 62)
print(f"  Assessments created   : {len(assessment_ids)}")
print(f"  Findings created      : {len(finding_ids)}")
print(f"  Risks created         : {len(risk_ids)}")
print()
print("  → Reload http://localhost:3000")
print()
