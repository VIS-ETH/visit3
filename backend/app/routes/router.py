from fastapi import APIRouter
from app.routes.user import router as user_router
from app.routes.auth import router as auth_router
from app.routes.csrf import router as csrf_router

router = APIRouter()
router.include_router(user_router)
router.include_router(auth_router)
router.include_router(csrf_router)
