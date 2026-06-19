from .agents import router as agents_router
from .disclosure import router as disclosure_router
from .due_diligence import router as due_diligence_router
from .copilot import router as copilot_router
from .regulatory import router as regulatory_router
from .api_platform import router as api_platform_router
from .executive import router as executive_router
from .comments import router as comments_router
from .suppliers import router as suppliers_router
from .supplier_intelligence import router as supplier_intelligence_router
from .notifications import router as notifications_router
from .assessments import router as assessments_router
from .audit import router as audit_router
from .auth import router as auth_router
from .compliance import assessments_compliance_router, frameworks_router
from .dashboard import router as dashboard_router
from .evidences import router as evidences_router
from .findings import router as findings_router
from .health import router as health_router
from .knowledge import router as knowledge_router
from .metrics import router as metrics_router
from .organizations import router as organizations_router
from .recommendations import router as recommendations_router
from .reports import router as reports_router
from .risks import router as risks_router
from .sector_intelligence import assessments_benchmark_router, sector_intelligence_router
from .sectors import router as sectors_router
from .users import router as users_router
from .workflows import router as workflows_router

__all__ = [
    "agents_router",
    "disclosure_router",
    "due_diligence_router",
    "copilot_router",
    "regulatory_router",
    "api_platform_router",
    "executive_router",
    "comments_router",
    "dashboard_router",
    "assessments_compliance_router",
    "assessments_benchmark_router",
    "assessments_router",
    "audit_router",
    "auth_router",
    "evidences_router",
    "findings_router",
    "frameworks_router",
    "health_router",
    "knowledge_router",
    "metrics_router",
    "organizations_router",
    "recommendations_router",
    "reports_router",
    "risks_router",
    "sector_intelligence_router",
    "sectors_router",
    "notifications_router",
    "suppliers_router",
    "supplier_intelligence_router",
    "users_router",
    "workflows_router",
]
