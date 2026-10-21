from flask import Blueprint, jsonify

from app.openapi import build_spec

docs_bp = Blueprint("docs", __name__)

SWAGGER_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Сервис заявок - Swagger UI</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({url: "/openapi.json", dom_id: "#swagger-ui"});
  </script>
</body>
</html>
"""


@docs_bp.get("/openapi.json")
def openapi_json():
    return jsonify(build_spec())


@docs_bp.get("/docs")
def swagger_ui():
    return SWAGGER_PAGE
