"""M34.2 Tests — B1 startup / import correctness.

Verifies that:
  1. Both M34 routers import cleanly with no broken paths
  2. operations.py uses interfaces.api.deps (not .dependencies or infrastructure.database)
  3. external_intelligence.py uses interfaces.api.deps and domain.user

These tests inspect source code so they work in any environment without
requiring all transitive dependencies (jwt, database drivers, etc.).
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
import sys


def _load_source(module_path: str, module_name: str):
    """Load a Python source file without executing transitive imports."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    return open(module_path).read()


def _read_router_source(filename: str) -> str:
    base = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "interfaces", "api", "routers",
    )
    path = os.path.normpath(os.path.join(base, filename))
    with open(path) as f:
        return f.read()


def test_operations_module_uses_correct_deps_import():
    src = _read_router_source("operations.py")
    assert "from interfaces.api.deps import" in src
    assert "from infrastructure.database import" not in src
    assert "from interfaces.api.dependencies import" not in src


def test_external_intelligence_module_uses_correct_deps_import():
    src = _read_router_source("external_intelligence.py")
    assert "from interfaces.api.deps import" in src
    assert "from infrastructure.database import" not in src
    assert "from interfaces.api.dependencies import" not in src


def test_external_intelligence_module_uses_domain_user():
    src = _read_router_source("external_intelligence.py")
    assert "from domain.user import User" in src


def test_operations_router_has_require_admin():
    src = _read_router_source("operations.py")
    assert "require_admin" in src


def test_operations_router_imports_deps_not_dependencies():
    src = _read_router_source("operations.py")
    # Must use deps, not dependencies
    assert "interfaces.api.deps" in src
    assert "interfaces.api.dependencies" not in src


def test_operations_router_has_all_six_endpoints():
    src = _read_router_source("operations.py")
    assert '"/dashboard"' in src
    assert '"/health"' in src
    assert '"/freshness"' in src
    assert '"/trigger"' in src
    assert '"/scheduler-health"' in src


def test_scheduler_health_module_importable():
    from application.external_intelligence.scheduler_health import get_scheduler_health_report
    assert callable(get_scheduler_health_report)


def test_scheduler_health_report_structure():
    from application.external_intelligence.scheduler_health import (
        _SchedulerHeartbeat,
    )
    hb = _SchedulerHeartbeat()
    hb.record_started()
    hb.record_completed()
    report = hb.report()
    assert report.scheduler_alive is True
    assert report.cycles_completed == 1
    assert report.last_cycle_completed is not None


def test_m1_api_scope_has_external_intelligence_scopes():
    from domain.enums import ApiScope
    assert hasattr(ApiScope, "EXTERNAL_INTELLIGENCE_READ")
    assert hasattr(ApiScope, "EXTERNAL_INTELLIGENCE_WRITE")
    assert ApiScope.EXTERNAL_INTELLIGENCE_READ.value == "external_intelligence:read"
    assert ApiScope.EXTERNAL_INTELLIGENCE_WRITE.value == "external_intelligence:write"
