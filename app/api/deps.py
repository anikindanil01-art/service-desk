from functools import wraps

import jwt
from flask import current_app, g, request

from app.db import get_db
from app.errors import AuthError, ValidationError
from app.repositories.comments import CommentRepository
from app.repositories.tickets import TicketRepository
from app.repositories.users import UserRepository
from app.security import decode_token
from app.services.auth import AuthService
from app.services.comments import CommentService
from app.services.tickets import TicketService


def auth_service():
    cfg = current_app.config
    return AuthService(
        UserRepository(get_db()),
        cfg["SECRET_KEY"],
        cfg["JWT_EXPIRES_MINUTES"],
        cfg["PASSWORD_ITERATIONS"],
    )


def ticket_service():
    conn = get_db()
    return TicketService(TicketRepository(conn), UserRepository(conn))


def comment_service():
    conn = get_db()
    return CommentService(CommentRepository(conn), TicketRepository(conn))


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Тело запроса должно быть JSON-объектом")
    return data


def int_arg(name, default=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValidationError(f"Параметр {name} должен быть числом")


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise AuthError("Требуется токен авторизации")
        try:
            payload = decode_token(header[len("Bearer "):], current_app.config["SECRET_KEY"])
        except jwt.PyJWTError:
            raise AuthError("Недействительный или просроченный токен")
        user = UserRepository(get_db()).get_by_id(int(payload["sub"]))
        if user is None:
            raise AuthError("Пользователь не найден")
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper
