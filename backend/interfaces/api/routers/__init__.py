from .agents import router as agents_router
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
    "users_router",
    "workflows_router",
]
