import structlog
from sqlalchemy.orm import Session

from app.infrastructure.security import create_access_token, verify_password
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger()


class UserService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def register(self, email: str, password_plain: str):
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("User with this email already exists")
        user = self.user_repo.create(email, password_plain)
        logger.info("Registered new user", user_id=str(user.id), email=email)
        return user

    def authenticate(self, email: str, password_plain: str) -> str | None:
        user = self.user_repo.get_by_email(email)
        if not user:
            return None
        if not verify_password(password_plain, user.password_hash):
            return None

        # Create JWT access token
        token = create_access_token(subject=str(user.id))
        logger.info("User authenticated successfully", user_id=str(user.id))
        return token

    def get_user_by_id(self, user_id):
        return self.user_repo.get_by_id(user_id)
