from app.errors import ValidationError


def require_text(data, field, max_length):
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Поле {field} обязательно и должно быть непустой строкой")
    if len(value) > max_length:
        raise ValidationError(f"Поле {field} не должно быть длиннее {max_length} символов")
    return value.strip()
