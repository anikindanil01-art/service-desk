from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models import (
    ALLOWED_TRANSITIONS,
    PRIORITIES,
    ROLE_ADMIN,
    ROLE_EXECUTOR,
    STATUSES,
    utcnow_iso,
)
from app.services.common import require_text

MAX_PAGE_SIZE = 100


def public_ticket(ticket):
    return {
        "id": ticket["id"],
        "subject": ticket["subject"],
        "description": ticket["description"],
        "priority": ticket["priority"],
        "status": ticket["status"],
        "author_id": ticket["author_id"],
        "assignee_id": ticket["assignee_id"],
        "created_at": ticket["created_at"],
        "updated_at": ticket["updated_at"],
    }


def _check_priority(value):
    if value not in PRIORITIES:
        raise ValidationError("Недопустимый приоритет, допустимы: " + ", ".join(PRIORITIES))
    return value


def _check_status(value):
    if value not in STATUSES:
        raise ValidationError("Недопустимый статус, допустимы: " + ", ".join(STATUSES))
    return value


class TicketService:
    def __init__(self, tickets, users):
        self.tickets = tickets
        self.users = users

    def _get_active(self, ticket_id):
        ticket = self.tickets.get(ticket_id)
        if ticket is None or ticket["is_deleted"]:
            raise NotFoundError("Заявка не найдена")
        return ticket

    def create(self, current_user, data):
        subject = require_text(data, "subject", 200)
        description = require_text(data, "description", 5000)
        priority = _check_priority(data.get("priority", "MEDIUM"))
        assignee_id = data.get("assignee_id")
        if assignee_id is not None and not isinstance(assignee_id, int):
            raise ValidationError("assignee_id должен быть числом")
        ticket_id = self.tickets.create(
            subject, description, priority, current_user["id"], assignee_id, utcnow_iso()
        )
        return public_ticket(self.tickets.get(ticket_id))

    def list(self, status=None, priority=None, assignee_id=None, page=1, page_size=10):
        if status is not None:
            _check_status(status)
        if priority is not None:
            _check_priority(priority)
        if page < 1 or page_size < 1:
            raise ValidationError("page и page_size должны быть не меньше 1")
        page_size = min(page_size, MAX_PAGE_SIZE)
        offset = (page - 1) * page_size
        items = self.tickets.list(status, priority, assignee_id, page_size, offset)
        total = self.tickets.count(status, priority, assignee_id)
        return {
            "items": [public_ticket(t) for t in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    def get(self, ticket_id):
        return public_ticket(self._get_active(ticket_id))

    def update(self, current_user, ticket_id, data):
        ticket = self._get_active(ticket_id)
        is_admin = current_user["role"] == ROLE_ADMIN
        is_author = ticket["author_id"] == current_user["id"]
        is_assignee = ticket["assignee_id"] == current_user["id"]
        if not (is_admin or is_author or is_assignee):
            raise ForbiddenError("Редактировать заявку может автор, исполнитель или ADMIN")
        fields = {}
        if "subject" in data:
            fields["subject"] = require_text(data, "subject", 200)
        if "description" in data:
            fields["description"] = require_text(data, "description", 5000)
        if "priority" in data:
            fields["priority"] = _check_priority(data["priority"])
        if "status" in data:
            fields["status"] = _check_status(data["status"])
        if not fields:
            raise ValidationError("Не переданы поля для изменения")
        self.tickets.update(ticket_id, fields, utcnow_iso())
        return public_ticket(self.tickets.get(ticket_id))

    def delete(self, current_user, ticket_id):
        if current_user["role"] != ROLE_ADMIN:
            raise ForbiddenError("Удалять заявки может только ADMIN")
        self._get_active(ticket_id)
        self.tickets.soft_delete(ticket_id, utcnow_iso())

    def change_status(self, current_user, ticket_id, data):
        ticket = self._get_active(ticket_id)
        is_admin = current_user["role"] == ROLE_ADMIN
        if not (is_admin or ticket["assignee_id"] == current_user["id"]):
            raise ForbiddenError("Менять статус может исполнитель заявки или ADMIN")
        new_status = _check_status(data.get("status"))
        current = ticket["status"]
        if new_status not in ALLOWED_TRANSITIONS[current]:
            raise ConflictError(f"Переход {current} -> {new_status} запрещён")
        self.tickets.set_status(ticket_id, new_status)
        return public_ticket(self.tickets.get(ticket_id))

    def assign(self, current_user, ticket_id, data):
        if current_user["role"] != ROLE_ADMIN:
            raise ForbiddenError("Назначать исполнителя может только ADMIN")
        self._get_active(ticket_id)
        assignee_id = data.get("assignee_id")
        if not isinstance(assignee_id, int):
            raise ValidationError("assignee_id должен быть числом")
        executor = self.users.get_by_id(assignee_id)
        if executor is None:
            raise NotFoundError("Пользователь не найден")
        if executor["role"] != ROLE_EXECUTOR:
            raise ValidationError("Исполнителем может быть только пользователь с ролью EXECUTOR")
        self.tickets.set_assignee(ticket_id, assignee_id, utcnow_iso())
        return public_ticket(self.tickets.get(ticket_id))
