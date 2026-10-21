import hashlib
import hmac
import os
from datetime import datetime, timedelta

import jwt


def hash_password(password, iterations):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{iterations}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user_id, role, secret, expires_minutes):
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now() + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token, secret):
    return jwt.decode(token, secret, algorithms=["HS256"])
