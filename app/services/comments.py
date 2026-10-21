from app.errors import NotFoundError
from app.models import utcnow_iso
from app.services.common import require_text


class CommentService:
    def __init__(self, comments, tickets):
        self.comments = comments
        self.tickets = tickets

    def _check_ticket(self, ticket_id):
        if self.tickets.get(ticket_id) is None:
            raise NotFoundError("Заявка не найдена")

    def add(self, current_user, ticket_id, data):
        self._check_ticket(ticket_id)
        text = require_text(data, "text", 2000)
        return self.comments.create(ticket_id, current_user["id"], text, utcnow_iso())

    def list(self, ticket_id):
        self._check_ticket(ticket_id)
        return self.comments.list_by_ticket(ticket_id)
