from sqlalchemy.orm import Session
from app.infrastructure.models import User
from app.infrastructure.security import get_password_hash


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, email: str, password_plain: str) -> User:
        user = User(email=email, password_hash=get_password_hash(password_plain))
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
