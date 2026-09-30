from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from app.api.dependencies import AdministratorUser

router = APIRouter(tags=["observability"])


@router.get(
    "/metrics",
    summary="Export Prometheus application metrics",
    response_class=Response,
)
def metrics(_: AdministratorUser) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
