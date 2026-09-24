from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.agents import router as workflows_router
from app.api.routes.knowledge import router as audit_router
from app.api.routes.reviews import router as reviews_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(tickets_router)
api_router.include_router(workflows_router)
api_router.include_router(reviews_router)
api_router.include_router(audit_router)
