from flask import Blueprint, jsonify

from app.api.deps import auth_service, json_body

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/register")
def register():
    user = auth_service().register(json_body())
    return jsonify(user), 201


@auth_bp.post("/login")
def login():
    return jsonify(auth_service().login(json_body()))
