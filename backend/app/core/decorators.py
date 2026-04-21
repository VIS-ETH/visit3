import logging
from app.core.exceptions import EmailNotConfirmed, NotAllowed, UserNotConfirmed

logger = logging.getLogger(__name__)


def require_confirmed_company(func):
    async def wrapper(*args, **kwargs):
        self = args[0]
        if not self.current_user.is_company:
            logger.warning(
                f"Authorization failed - not company: {self.current_user.email}"
            )
            raise NotAllowed(f"require_confirmed_company:{self.current_user.id}")
        if not self.current_user.email_confirmed:
            logger.warning(
                f"Authorization failed - email not confirmed: {self.current_user.email}"
            )
            raise EmailNotConfirmed(f"require_confirmed_company:{self.current_user.id}")
        if not self.current_user.user_confirmed:
            logger.warning(
                f"Authorization failed - user not confirmed by admin: {self.current_user.email}"
            )
            raise UserNotConfirmed(f"require_confirmed_company:{self.current_user.id}")

        logger.debug(
            f"Authorization granted - confirmed company: {self.current_user.email}"
        )
        return await func(*args, **kwargs)

    return wrapper


def require_staff(func):
    async def wrapper(*args, **kwargs):
        self = args[0]
        if not self.current_user.is_staff:
            logger.warning(
                f"Authorization failed - not staff: {self.current_user.email}"
            )
            raise NotAllowed(f"require_staff:{self.current_user.id}")

        logger.debug(f"Authorization granted - staff: {self.current_user.email}")
        return await func(*args, **kwargs)

    return wrapper


def require_admin(func):
    async def wrapper(*args, **kwargs):
        self = args[0]
        if not self.current_user.is_admin:
            logger.warning(
                f"Authorization failed - not admin: {self.current_user.email}"
            )
            raise NotAllowed(f"require_admin:{self.current_user.id}")

        logger.debug(f"Authorization granted - admin: {self.current_user.email}")
        return await func(*args, **kwargs)

    return wrapper


def require_role(role: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            self = args[0]

            user_roles = {
                user_role.name for user_role in (self.current_user.roles or [])
            }
            if role not in user_roles:
                logger.warning(
                    f"Authorization failed - missing role {role}: {self.current_user.email}"
                )
                raise NotAllowed(f"require_role[{role}]:{self.current_user.id}")

            logger.debug(
                f"Authorization granted - role {role}: {self.current_user.email}"
            )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
