import json
import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.exceptions import HTTPException

from app.api import auth, catalog, health, shopping, wishlist
from app.config import Settings, get_settings
from app.core.errors import AppError

logger = logging.getLogger("decor.requests")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)
logger.propagate = False


def create_app(settings: Settings | None = None, database_engine=None) -> FastAPI:
    settings = settings or get_settings()
    engine = database_engine or create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={"connect_timeout": 3},
    )

    @asynccontextmanager
    async def lifespan(app):
        yield
        if database_engine is None:
            engine.dispose()

    app = FastAPI(
        title="Home Decor API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env != "production" else None,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
        expose_headers=["X-Request-ID"],
    )

    def error_response(request, status, code, message):
        return JSONResponse(
            status_code=status,
            content={
                "error": {"code": code, "message": message},
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
        )

    @app.exception_handler(AppError)
    async def app_error(request, error):
        response = error_response(request, error.status, error.code, error.message)
        if error.status == 429:
            response.headers["Retry-After"] = "900"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Raw Pydantic input/context may contain passwords. Never serialize it.
        return error_response(
            request, 422, "invalid_input", "Check the submitted fields and password requirements."
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return error_response(
            request, error.status_code, "http_error", "Request could not be completed."
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = str(uuid4())
        start = time.monotonic()
        try:
            if request.method in {"POST", "PUT", "PATCH"}:
                size = 0
                chunks = []
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > 16384:
                        raise AppError(413, "request_too_large", "Request is too large.")
                    chunks.append(chunk)
                request._body = b"".join(chunks)
            response = await call_next(request)
        except AppError as error:
            response = error_response(request, error.status, error.code, error.message)
        except Exception:
            logger.error(
                json.dumps({"event": "request_failed", "request_id": request.state.request_id})
            )
            response = error_response(
                request, 500, "internal_error", "An unexpected error occurred."
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith(("/api/v1/auth", "/api/v1/cart", "/api/v1/wishlist")):
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "request_id": request.state.request_id,
                    "method": request.method,
                    "status": response.status_code,
                    "duration_ms": round((time.monotonic() - start) * 1000),
                }
            )
        )
        return response

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(shopping.router, prefix="/api/v1")
    app.include_router(wishlist.router, prefix="/api/v1")
    return app


app = create_app()
