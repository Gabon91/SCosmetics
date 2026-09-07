from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.auth import UserRegistrationRequest


class EmailAlreadyRegisteredError(Exception):
    pass


class UserService:
    def __init__(self, session: Session):
        self.session = session

    def register_customer(self, data: UserRegistrationRequest) -> User:
        normalized_email = str(data.email).strip().lower()
        existing_user_id = self.session.scalar(
            select(User.id).where(User.email == normalized_email)
        )
        if existing_user_id is not None:
            raise EmailAlreadyRegisteredError

        user = User(
            first_name=data.first_name,
            last_name=data.last_name,
            email=normalized_email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=UserRole.CUSTOMER,
        )
        self.session.add(user)

        try:
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise EmailAlreadyRegisteredError from error

        self.session.refresh(user)
        return user
