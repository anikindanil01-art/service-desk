class CommentRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, ticket_id, author_id, text, now):
        cur = self.conn.execute(
            "INSERT INTO comments (ticket_id, author_id, text, created_at) "
            "VALUES (?, ?, ?, ?)",
            (ticket_id, author_id, text, now),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT * FROM comments WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)

    def list_by_ticket(self, ticket_id):
        rows = self.conn.execute(
            "SELECT * FROM comments WHERE ticket_id = ? ORDER BY id", (ticket_id,)
        ).fetchall()
        return [dict(r) for r in rows]
