from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.company import companies_router
from app.routes.company import public_router as public_company_router
from app.routes.company import router as company_router
from app.routes.csrf import router as csrf_router
from app.routes.industry import router as industry_router
from app.routes.kp import router as kp_router
from app.routes.mail_template import router as mail_template_router
from app.routes.user import public_router as public_user_router
from app.routes.user import router as user_router
from app.routes.user import users_router
from app.routes.venue import router as venue_router

router = APIRouter()
router.include_router(public_user_router)
router.include_router(user_router)
router.include_router(users_router)
router.include_router(auth_router)
router.include_router(csrf_router)
router.include_router(public_company_router)
router.include_router(company_router)
router.include_router(companies_router)
router.include_router(industry_router)
router.include_router(kp_router)
router.include_router(mail_template_router)
router.include_router(venue_router)
