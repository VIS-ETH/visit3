from app.core.exceptions import EmailNotConfirmed, NotAllowed, UserNotConfirmed


def require_confirmed_company(func):
    def wrapper(*args, **kwargs):
        self = args[0]
        if not self.current_user.is_company:
            raise NotAllowed(self.current_user.email)
        if not self.current_user.email_confirmed:
            raise EmailNotConfirmed(self.current_user.email)
        if not self.current_user.user_confirmed:
            raise UserNotConfirmed(self.current_user.email)

        result = func(*args, **kwargs)

        return result

    return wrapper
