import logging
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi_csrf_protect import CsrfProtect

from app.core.config import get_settings
from app.core.deps.database import DbSessionDep
from app.core.exceptions import CsrfInvalid, NotAllowed, Unauthenticated
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login", refreshUrl="/api/auth/refresh"
)


async def get_current_user(
    request: Request,
    session: DbSessionDep,
    token: Annotated[str, Depends(oauth2_scheme)],
):
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
        subject = payload.get("sub")
        if subject is None:
            logger.warning("JWT decode failed - no sub claim")
            raise Unauthenticated("jwt_decode:no_sub")
    except jwt.InvalidTokenError:
        logger.warning("JWT decode failed - invalid token")
        raise Unauthenticated("jwt_decode:invalid_token")

    user_repo = UserRepository(session)
    try:
        user = await user_repo.get_by_id(UUID(subject))
    except ValueError:
        logger.warning("JWT decode failed - invalid subject: %r", subject)
        raise Unauthenticated(f"jwt_decode:invalid_sub:{subject}")

    if user is None:
        logger.warning("JWT user lookup failed - user not found: %r", subject)
        raise Unauthenticated(f"jwt_decode:user_not_found:{subject}")

    await user_repo.load_user_roles(user)
    logger.debug("User authenticated: %s", user.id)

    impersonate_id = request.headers.get("X-Impersonate-User-Id")
    if impersonate_id and user.is_admin:
        try:
            target_uuid = UUID(impersonate_id)
        except ValueError:
            raise NotAllowed(f"impersonate:invalid_uuid:{impersonate_id}")
        target = await user_repo.get_by_id(target_uuid)
        if target is None:
            raise NotAllowed(f"impersonate:user_not_found:{impersonate_id}")
        if target.is_admin and target.id != user.id:
            raise NotAllowed(f"impersonate:target_is_admin:{target.id}")
        await user_repo.load_user_roles(target)
        logger.info("Admin %s impersonating: %s", user.id, target.id)
        return target
    elif impersonate_id:
        raise NotAllowed(f"impersonate:not_admin:{user.email}")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def _csrf_dep(request: Request, csrf_protect: Annotated[CsrfProtect, Depends()]):
    if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
        try:
            await csrf_protect.validate_csrf(request)
        except Exception:
            raise CsrfInvalid(f"csrf:{request.method}:{request.url.path}")


CsrfDep = Depends(_csrf_dep)
