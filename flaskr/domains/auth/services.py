from flask import abort
from flask_jwt_extended import create_access_token, get_jwt
from werkzeug.security import check_password_hash

from flaskr.core.extensions import db
from flaskr.core.utils import utc_now
from flaskr.domains.auth.models import TokenBlocklist
from flaskr.domains.user.models import User
from flaskr.domains.user.repositories import UserRepository


class AuthService:
    repository: UserRepository = UserRepository()

    def verify_user(self, username: str, password: str) -> dict:
        user: User = self.repository.get_by_name(column_name="username", value=username)

        if not user or not check_password_hash(user.password, password):
            abort(401, description="Invalid credentials")

        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"role": user.role.name},
        )

        return {"access_token": access_token, "refresh_token": "refresh_token"}

    def logout(self) -> None:
        jti = get_jwt()["jti"]
        db.session.add(TokenBlocklist(jti=jti, created_at=utc_now()))
        db.session.commit()
