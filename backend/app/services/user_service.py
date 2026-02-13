from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.mail_service import MailService


class UserService:
    def __init__(self, user_repository: UserRepository, mail: MailService, current_user: User):
        self.user_repository = user_repository
        self.mail_service = mail
        self.current_user = current_user

