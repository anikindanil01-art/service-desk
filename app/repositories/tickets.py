UPDATABLE_FIELDS = ("subject", "description", "priority", "status")


def _build_where(status, priority, assignee_id):
    clauses = []
    params = []
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority)
    if assignee_id is not None:
        clauses.append("assignee_id = ?")
        params.append(assignee_id)
    return clauses, params


class TicketRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, subject, description, priority, author_id, assignee_id, now):
        cur = self.conn.execute(
            "INSERT INTO tickets (subject, description, priority, status, author_id, "
            "assignee_id, is_deleted, created_at, updated_at) "
            "VALUES (?, ?, ?, 'NEW', ?, ?, 0, ?, ?)",
            (subject, description, priority, author_id, assignee_id, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, ticket_id):
        row = self.conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row else None

    def list(self, status=None, priority=None, assignee_id=None, limit=10, offset=0):
        clauses, params = _build_where(status, priority, assignee_id)
        clauses.append("is_deleted = 0")
        sql = (
            "SELECT * FROM tickets WHERE " + " AND ".join(clauses)
            + " ORDER BY id DESC LIMIT ? OFFSET ?"
        )
        rows = self.conn.execute(sql, params + [limit, offset]).fetchall()
        return [dict(r) for r in rows]

    def count(self, status=None, priority=None, assignee_id=None):
        clauses, params = _build_where(status, priority, assignee_id)
        sql = "SELECT COUNT(*) FROM tickets"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        return self.conn.execute(sql, params).fetchone()[0]

    def update(self, ticket_id, fields, now):
        names = [name for name in UPDATABLE_FIELDS if name in fields]
        assignments = ", ".join(f"{name} = ?" for name in names)
        values = [fields[name] for name in names]
        self.conn.execute(
            f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?",
            values + [now, ticket_id],
        )
        self.conn.commit()

    def set_status(self, ticket_id, status):
        self.conn.execute(
            "UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id)
        )
        self.conn.commit()

    def set_assignee(self, ticket_id, assignee_id, now):
        self.conn.execute(
            "UPDATE tickets SET assignee_id = ?, updated_at = ? WHERE id = ?",
            (assignee_id, now, ticket_id),
        )
        self.conn.commit()

    def soft_delete(self, ticket_id, now):
        self.conn.execute(
            "UPDATE tickets SET is_deleted = 1, updated_at = ? WHERE id = ?",
            (now, ticket_id),
        )
        self.conn.commit()
