from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.jwt import create_access_token
from app.utils.password import (
    hash_password,
    verify_password,
)


class AuthService:

    @staticmethod
    def signup(
        db: Session,
        name: str,
        email: str,
        password: str,
    ) -> User:

        existing_user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing_user:
            raise ValueError(
                "User with this email already exists"
            )

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def login(
        db: Session,
        email: str,
        password: str,
    ):

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )
        print(f"user details:: {user}")

        if not user:
            raise ValueError(
                "User not found"
            )

        if not verify_password(
            password,
            user.password_hash,
        ):
            raise ValueError(
                "Invalid email or password"
            )

        token = create_access_token(
            user_id=user.id,
            email=user.email,
        )

        return user, token