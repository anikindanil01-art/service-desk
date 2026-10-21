class UserRepository:
    def __init__(self, conn):
        self.conn = conn

    def create(self, username, password_hash, role, created_at):
        cur = self.conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username, password_hash, role, created_at),
        )
        self.conn.commit()
        return self.get_by_id(cur.lastrowid)

    def get_by_id(self, user_id):
        row = self.conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_by_username(self, username):
        row = self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None
