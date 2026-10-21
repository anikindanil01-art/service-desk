def make_ticket(**overrides):
    ticket = {
        "id": 1,
        "subject": "Не работает принтер",
        "description": "Принтер на 3 этаже не печатает",
        "priority": "MEDIUM",
        "status": "NEW",
        "author_id": 10,
        "assignee_id": None,
        "is_deleted": 0,
        "created_at": "2026-01-01T10:00:00+00:00",
        "updated_at": "2026-01-01T10:00:00+00:00",
    }
    ticket.update(overrides)
    return ticket


def make_user(user_id=1, role="USER", username="user"):
    return {
        "id": user_id,
        "username": username,
        "password_hash": "x",
        "role": role,
        "created_at": "2026-01-01T10:00:00+00:00",
    }


ADMIN = make_user(1, "ADMIN", "admin")
EXECUTOR = make_user(2, "EXECUTOR", "executor")
USER = make_user(10, "USER", "author")
STRANGER = make_user(99, "USER", "stranger")
