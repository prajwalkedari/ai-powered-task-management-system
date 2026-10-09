"""Application factory and ASGI entry point.

Run locally with:  uvicorn app.main:app --reload
"""
from fastapi.middleware.cors import CORSMiddleware




import logging

from fastapi import FastAPI

from app.api import api_router
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API for authenticated task management, with AI-generated task descriptions "
            "and summaries. To call protected endpoints, log in via POST /api/auth/login and "
            "paste the access_token into the Authorize dialog."
        ),
    )
    register_exception_handlers(app)
    app.include_router(api_router)

    @app.get("/health", tags=["System"], summary="Liveness check")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # "https://ai-task-management-dashboard.v0.build",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)