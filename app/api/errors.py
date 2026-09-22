import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import ApplicationError
from app.core.logging import request_id_context

logger = logging.getLogger(__name__)


def _response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": request_id_context.get()}},
    )


async def application_error_handler(_: Request, exc: ApplicationError) -> JSONResponse:
    logger.warning("application_error", extra={"event": exc.code, "status": exc.status_code})
    return _response(exc.status_code, exc.code, exc.public_message)


async def validation_error_handler(_: Request, __: RequestValidationError) -> JSONResponse:
    return _response(422, "validation_error", "The request contains invalid data")


async def database_error_handler(_: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("database_error", exc_info=exc, extra={"event": "postgresql_failure", "status": 503})
    return _response(503, "database_unavailable", "The database is temporarily unavailable")


async def timeout_error_handler(_: Request, exc: TimeoutError) -> JSONResponse:
    logger.warning("operation_timeout", extra={"event": "timeout", "status": 504})
    return _response(504, "operation_timeout", "The operation timed out")


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", exc_info=exc, extra={"event": "unhandled_error", "status": 500})
    return _response(500, "internal_server_error", "An unexpected error occurred")
