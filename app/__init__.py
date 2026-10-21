from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from app.api.auth import auth_bp
from app.api.docs import docs_bp
from app.api.tickets import tickets_bp
from app.config import Config
from app.db import close_db
from app.errors import AppError


def create_app(overrides=None):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(docs_bp)

    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return jsonify({"error": error.description}), error.code

    return app
