from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.company import router as company_router
from app.routes.csrf import router as csrf_router
from app.routes.kp import router as kp_router
from app.routes.user import public_router as public_user_router
from app.routes.user import router as user_router

router = APIRouter()
router.include_router(public_user_router)
router.include_router(user_router)
router.include_router(auth_router)
router.include_router(csrf_router)
router.include_router(company_router)
router.include_router(kp_router)
