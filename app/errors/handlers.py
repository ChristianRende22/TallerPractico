from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors.exceptions import AppError


def _payload(error, code, status, details=None):
    body = {"error": error, "code": code, "status": status}
    if details is not None:
        body["details"] = details
    return body


async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content=_payload(exc.message, exc.code, exc.status, exc.details),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(
                str(p) for p in error["loc"] if p not in ("body", "query")
            ),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=400,
        content=_payload("Validation failed", "VALIDATION_ERROR", 400, details),
    )


async def unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=_payload("Internal server error", "INTERNAL_ERROR", 500),
    )


def register_error_handlers(app):
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
