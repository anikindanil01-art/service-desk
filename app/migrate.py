"""Простой запуск SQL-миграций из каталога migrations/.

Применённые миграции записываются в таблицу schema_migrations,
повторный запуск применяет только новые файлы.
Запуск: python -m app.migrate
"""
from pathlib import Path

from app.config import Config
from app.db import connect
from app.models import utcnow_iso

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def run_migrations(conn, directory=MIGRATIONS_DIR):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    done = []
    for path in sorted(Path(directory).glob("*.sql")):
        if path.name in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (path.name, utcnow_iso()),
        )
        conn.commit()
        done.append(path.name)
    return done


if __name__ == "__main__":
    connection = connect(Config.DATABASE)
    result = run_migrations(connection)
    connection.close()
    if result:
        print("Применены миграции:", ", ".join(result))
    else:
        print("Новых миграций нет")
