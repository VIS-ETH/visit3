import logging
from app.core.exceptions import EmailNotConfirmed, NotAllowed, UserNotConfirmed

logger = logging.getLogger(__name__)


def require_confirmed_company(func):
    def wrapper(*args, **kwargs):
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
        result = func(*args, **kwargs)

        return result

    return wrapper


def require_staff(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.current_user.is_staff:
            logger.warning(
                f"Authorization failed - not staff: {self.current_user.email}"
            )
            raise NotAllowed(f"require_staff:{self.current_user.id}")

        logger.debug(f"Authorization granted - staff: {self.current_user.email}")
        result = func(*args, **kwargs)

        return result

    return wrapper


def require_admin(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.current_user.is_admin:
            logger.warning(
                f"Authorization failed - not admin: {self.current_user.email}"
            )
            raise NotAllowed(f"require_admin:{self.current_user.id}")

        logger.debug(f"Authorization granted - admin: {self.current_user.email}")
        result = func(*args, **kwargs)

        return result

    return wrapper


def require_role(role: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            self = args[0]
            if role not in self.current_user.roles:
                logger.warning(
                    f"Authorization failed - missing role {role}: {self.current_user.email}"
                )
                raise NotAllowed(f"require_role[{role}]:{self.current_user.id}")

            logger.debug(
                f"Authorization granted - role {role}: {self.current_user.email}"
            )
            result = func(*args, **kwargs)

            return result

        return wrapper

    return decorator
