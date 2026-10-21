"""Описание API в формате OpenAPI 3.0 (отдаётся по /openapi.json, UI на /docs)."""

STATUSES = ["NEW", "IN_PROGRESS", "RESOLVED", "CLOSED"]
PRIORITIES = ["LOW", "MEDIUM", "HIGH"]
ROLES = ["USER", "EXECUTOR", "ADMIN"]


def _ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def _json(schema):
    return {"application/json": {"schema": schema}}


def _resp(description, schema=None):
    result = {"description": description}
    if schema is not None:
        result["content"] = _json(schema)
    return result


ERRORS = {
    "400": _resp("Неверные данные", _ref("Error")),
    "401": _resp("Нет или неверный токен", _ref("Error")),
    "403": _resp("Недостаточно прав", _ref("Error")),
    "404": _resp("Не найдено", _ref("Error")),
    "409": _resp("Конфликт (например, недопустимый переход статуса)", _ref("Error")),
}


def _errors(*codes):
    return {code: ERRORS[code] for code in codes}


ID_PARAM = {"name": "ticket_id", "in": "path", "required": True, "schema": {"type": "integer"}}


def _query(name, schema):
    return {"name": name, "in": "query", "required": False, "schema": schema}


def build_spec():
    secured = [{"bearerAuth": []}]
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Сервис заявок",
            "version": "1.0.0",
            "description": "REST API учёта заявок (Service Desk)",
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
            "schemas": {
                "Error": {"type": "object", "properties": {"error": {"type": "string"}}},
                "RegisterRequest": {
                    "type": "object",
                    "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                        "role": {"type": "string", "enum": ROLES},
                    },
                },
                "LoginRequest": {
                    "type": "object",
                    "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                    },
                },
                "Token": {
                    "type": "object",
                    "properties": {
                        "access_token": {"type": "string"},
                        "token_type": {"type": "string"},
                    },
                },
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "username": {"type": "string"},
                        "role": {"type": "string", "enum": ROLES},
                        "created_at": {"type": "string"},
                    },
                },
                "Ticket": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": PRIORITIES},
                        "status": {"type": "string", "enum": STATUSES},
                        "author_id": {"type": "integer"},
                        "assignee_id": {"type": "integer", "nullable": True},
                        "created_at": {"type": "string"},
                        "updated_at": {"type": "string"},
                    },
                },
                "TicketCreate": {
                    "type": "object",
                    "required": ["subject", "description"],
                    "properties": {
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": PRIORITIES},
                        "assignee_id": {"type": "integer", "nullable": True},
                    },
                },
                "TicketUpdate": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "description": {"type": "string"},
                        "priority": {"type": "string", "enum": PRIORITIES},
                    },
                },
                "TicketPage": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array", "items": _ref("Ticket")},
                        "total": {"type": "integer"},
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                    },
                },
                "StatusChange": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {"status": {"type": "string", "enum": STATUSES}},
                },
                "AssigneeChange": {
                    "type": "object",
                    "required": ["assignee_id"],
                    "properties": {"assignee_id": {"type": "integer"}},
                },
                "Comment": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "ticket_id": {"type": "integer"},
                        "author_id": {"type": "integer"},
                        "text": {"type": "string"},
                        "created_at": {"type": "string"},
                    },
                },
                "CommentCreate": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {"text": {"type": "string"}},
                },
            },
        },
        "paths": {
            "/auth/register": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Регистрация пользователя",
                    "requestBody": {"required": True, "content": _json(_ref("RegisterRequest"))},
                    "responses": {"201": _resp("Пользователь создан", _ref("User")),
                                  **_errors("400", "409")},
                }
            },
            "/auth/login": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Вход, выдача JWT-токена",
                    "requestBody": {"required": True, "content": _json(_ref("LoginRequest"))},
                    "responses": {"200": _resp("JWT-токен", _ref("Token")),
                                  **_errors("400", "401")},
                }
            },
            "/tickets": {
                "get": {
                    "tags": ["tickets"],
                    "summary": "Список заявок с фильтрами и постраничной навигацией",
                    "security": secured,
                    "parameters": [
                        _query("status", {"type": "string", "enum": STATUSES}),
                        _query("priority", {"type": "string", "enum": PRIORITIES}),
                        _query("assignee_id", {"type": "integer"}),
                        _query("page", {"type": "integer", "default": 1}),
                        _query("page_size", {"type": "integer", "default": 10}),
                    ],
                    "responses": {"200": _resp("Страница заявок", _ref("TicketPage")),
                                  **_errors("400", "401")},
                },
                "post": {
                    "tags": ["tickets"],
                    "summary": "Создание заявки",
                    "security": secured,
                    "requestBody": {"required": True, "content": _json(_ref("TicketCreate"))},
                    "responses": {"201": _resp("Заявка создана", _ref("Ticket")),
                                  **_errors("400", "401")},
                },
            },
            "/tickets/{ticket_id}": {
                "parameters": [ID_PARAM],
                "get": {
                    "tags": ["tickets"],
                    "summary": "Заявка по идентификатору",
                    "security": secured,
                    "responses": {"200": _resp("Заявка", _ref("Ticket")),
                                  **_errors("401", "404")},
                },
                "put": {
                    "tags": ["tickets"],
                    "summary": "Редактирование заявки",
                    "security": secured,
                    "requestBody": {"required": True, "content": _json(_ref("TicketUpdate"))},
                    "responses": {"200": _resp("Заявка обновлена", _ref("Ticket")),
                                  **_errors("400", "401", "403", "404")},
                },
                "delete": {
                    "tags": ["tickets"],
                    "summary": "Мягкое удаление заявки (только ADMIN)",
                    "security": secured,
                    "responses": {"204": _resp("Заявка удалена"),
                                  **_errors("401", "403", "404")},
                },
            },
            "/tickets/{ticket_id}/status": {
                "parameters": [ID_PARAM],
                "patch": {
                    "tags": ["tickets"],
                    "summary": "Смена статуса заявки",
                    "security": secured,
                    "requestBody": {"required": True, "content": _json(_ref("StatusChange"))},
                    "responses": {"200": _resp("Статус изменён", _ref("Ticket")),
                                  **_errors("400", "401", "403", "404", "409")},
                },
            },
            "/tickets/{ticket_id}/assignee": {
                "parameters": [ID_PARAM],
                "patch": {
                    "tags": ["tickets"],
                    "summary": "Назначение исполнителя (только ADMIN)",
                    "security": secured,
                    "requestBody": {"required": True, "content": _json(_ref("AssigneeChange"))},
                    "responses": {"200": _resp("Исполнитель назначен", _ref("Ticket")),
                                  **_errors("400", "401", "403", "404")},
                },
            },
            "/tickets/{ticket_id}/comments": {
                "parameters": [ID_PARAM],
                "get": {
                    "tags": ["comments"],
                    "summary": "Список комментариев заявки",
                    "security": secured,
                    "responses": {
                        "200": _resp("Комментарии",
                                     {"type": "array", "items": _ref("Comment")}),
                        **_errors("401", "404"),
                    },
                },
                "post": {
                    "tags": ["comments"],
                    "summary": "Добавление комментария",
                    "security": secured,
                    "requestBody": {"required": True, "content": _json(_ref("CommentCreate"))},
                    "responses": {"201": _resp("Комментарий добавлен", _ref("Comment")),
                                  **_errors("400", "401", "404")},
                },
            },
        },
    }
