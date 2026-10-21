from app.errors import AuthError, ConflictError, ValidationError
from app.models import ROLE_USER, ROLES, utcnow_iso
from app.security import create_token, hash_password, verify_password


def public_user(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


class AuthService:
    def __init__(self, users, secret, expires_minutes, iterations):
        self.users = users
        self.secret = secret
        self.expires_minutes = expires_minutes
        self.iterations = iterations

    def register(self, data):
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", ROLE_USER)
        if not isinstance(username, str) or not 3 <= len(username.strip()) <= 50:
            raise ValidationError("username должен содержать от 3 до 50 символов")
        if not isinstance(password, str) or len(password) < 6:
            raise ValidationError("password должен содержать не менее 6 символов")
        if role not in ROLES:
            raise ValidationError("Недопустимая роль, допустимы: " + ", ".join(ROLES))
        username = username.strip()
        if self.users.get_by_username(username) is not None:
            raise ConflictError("Пользователь с таким именем уже существует")
        password_hash = hash_password(password, self.iterations)
        user = self.users.create(username, password_hash, role, utcnow_iso())
        return public_user(user)

    def login(self, data):
        username = data.get("username")
        password = data.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            raise ValidationError("Нужно передать username и password")
        user = self.users.get_by_username(username.strip())
        if user is None or not verify_password(password, user["password_hash"]):
            raise AuthError("Неверное имя пользователя или пароль")
        token = create_token(user["id"], user["role"], self.secret, self.expires_minutes)
        return {"access_token": token, "token_type": "Bearer"}
