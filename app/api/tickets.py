from flask import Blueprint, g, jsonify, request

from app.api.deps import (
    comment_service,
    int_arg,
    json_body,
    login_required,
    ticket_service,
)

tickets_bp = Blueprint("tickets", __name__, url_prefix="/tickets")


@tickets_bp.get("")
@login_required
def list_tickets():
    result = ticket_service().list(
        status=request.args.get("status"),
        priority=request.args.get("priority"),
        assignee_id=int_arg("assignee_id"),
        page=int_arg("page", 1),
        page_size=int_arg("page_size", 10),
    )
    return jsonify(result)


@tickets_bp.post("")
@login_required
def create_ticket():
    ticket = ticket_service().create(g.current_user, json_body())
    return jsonify(ticket), 201


@tickets_bp.get("/<int:ticket_id>")
@login_required
def get_ticket(ticket_id):
    return jsonify(ticket_service().get(ticket_id))


@tickets_bp.put("/<int:ticket_id>")
@login_required
def update_ticket(ticket_id):
    return jsonify(ticket_service().update(g.current_user, ticket_id, json_body()))


@tickets_bp.delete("/<int:ticket_id>")
@login_required
def delete_ticket(ticket_id):
    ticket_service().delete(g.current_user, ticket_id)
    return "", 204


@tickets_bp.patch("/<int:ticket_id>/status")
@login_required
def change_status(ticket_id):
    return jsonify(ticket_service().change_status(g.current_user, ticket_id, json_body()))


@tickets_bp.patch("/<int:ticket_id>/assignee")
@login_required
def assign_ticket(ticket_id):
    return jsonify(ticket_service().assign(g.current_user, ticket_id, json_body()))


@tickets_bp.get("/<int:ticket_id>/comments")
@login_required
def list_comments(ticket_id):
    return jsonify(comment_service().list(ticket_id))


@tickets_bp.post("/<int:ticket_id>/comments")
@login_required
def add_comment(ticket_id):
    comment = comment_service().add(g.current_user, ticket_id, json_body())
    return jsonify(comment), 201
