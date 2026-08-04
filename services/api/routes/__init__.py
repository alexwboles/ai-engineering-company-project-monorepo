from .suppliers import router as suppliers_router
from .users import router as users_router
from .profiles import router as profiles_router
from .auth import router as auth_router
from .incidents import router as incidents_router
from .telemetry import router as telemetry_router
from .telemetry_report import router as telemetry_report_router
from .inventory import router as inventory_router
from .tasks import router as tasks_router

__all__ = [
    "suppliers_router",
    "users_router",
    "profiles_router",
    "auth_router",
    "incidents_router",
    "telemetry_router",
    "telemetry_report_router",
    "inventory_router",
    "tasks_router",
]
