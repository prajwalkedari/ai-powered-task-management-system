from fastapi import APIRouter

from app.api import auth, tasks

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(tasks.router)
