import sqlite3

from flask import current_app, g


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
