import unittest
from unittest.mock import MagicMock

import jwt

from app.errors import AuthError, ConflictError, NotFoundError, ValidationError
from app.security import create_token, decode_token, hash_password, verify_password
from app.services.auth import AuthService
from app.services.comments import CommentService
from app.services.common import require_text
from tests.helpers import USER, make_ticket, make_user

SECRET = "test-secret"


class AuthServiceTests(unittest.TestCase):
    def setUp(self):
        self.users = MagicMock()
        self.service = AuthService(self.users, SECRET, 60, 1000)

    def test_register_ok_defaults_to_user_role(self):
        self.users.get_by_username.return_value = None
        self.users.create.side_effect = lambda name, pw, role, now: make_user(1, role, name)
        result = self.service.register({"username": "ivan", "password": "secret1"})
        self.assertEqual(result["role"], "USER")
        self.assertNotIn("password_hash", result)

    def test_register_stores_hash_not_password(self):
        self.users.get_by_username.return_value = None
        self.users.create.side_effect = lambda name, pw, role, now: make_user(1, role, name)
        self.service.register({"username": "ivan", "password": "secret1"})
        stored = self.users.create.call_args[0][1]
        self.assertNotEqual(stored, "secret1")
        self.assertTrue(verify_password("secret1", stored))

    def test_register_with_role(self):
        self.users.get_by_username.return_value = None
        self.users.create.side_effect = lambda name, pw, role, now: make_user(1, role, name)
        result = self.service.register(
            {"username": "boss", "password": "secret1", "role": "ADMIN"}
        )
        self.assertEqual(result["role"], "ADMIN")

    def test_register_short_username(self):
        with self.assertRaises(ValidationError):
            self.service.register({"username": "ab", "password": "secret1"})

    def test_register_short_password(self):
        with self.assertRaises(ValidationError):
            self.service.register({"username": "ivan", "password": "123"})

    def test_register_bad_role(self):
        with self.assertRaises(ValidationError):
            self.service.register({"username": "ivan", "password": "secret1", "role": "ROOT"})

    def test_register_duplicate(self):
        self.users.get_by_username.return_value = make_user()
        with self.assertRaises(ConflictError):
            self.service.register({"username": "ivan", "password": "secret1"})

    def test_login_ok(self):
        stored = hash_password("secret1", 1000)
        user = make_user(5, "USER", "ivan")
        user["password_hash"] = stored
        self.users.get_by_username.return_value = user
        result = self.service.login({"username": "ivan", "password": "secret1"})
        self.assertEqual(result["token_type"], "Bearer")
        payload = decode_token(result["access_token"], SECRET)
        self.assertEqual(payload["sub"], "5")
        self.assertEqual(payload["role"], "USER")

    def test_login_wrong_password(self):
        user = make_user()
        user["password_hash"] = hash_password("secret1", 1000)
        self.users.get_by_username.return_value = user
        with self.assertRaises(AuthError):
            self.service.login({"username": "user", "password": "wrong"})

    def test_login_unknown_user(self):
        self.users.get_by_username.return_value = None
        with self.assertRaises(AuthError):
            self.service.login({"username": "ghost", "password": "secret1"})

    def test_login_missing_fields(self):
        with self.assertRaises(ValidationError):
            self.service.login({"username": "ivan"})


class SecurityTests(unittest.TestCase):
    def test_hash_is_salted(self):
        self.assertNotEqual(hash_password("abc123", 1000), hash_password("abc123", 1000))

    def test_verify_password(self):
        stored = hash_password("abc123", 1000)
        self.assertTrue(verify_password("abc123", stored))
        self.assertFalse(verify_password("abc124", stored))

    def test_verify_broken_hash(self):
        self.assertFalse(verify_password("abc123", "broken"))

    def test_token_roundtrip(self):
        token = create_token(7, "ADMIN", SECRET, 5)
        payload = decode_token(token, SECRET)
        self.assertEqual(payload["sub"], "7")

    def test_token_wrong_secret(self):
        token = create_token(7, "ADMIN", SECRET, 5)
        with self.assertRaises(jwt.PyJWTError):
            decode_token(token, "other-secret")

    def test_expired_token(self):
        token = create_token(7, "ADMIN", SECRET, -5)
        with self.assertRaises(jwt.ExpiredSignatureError):
            decode_token(token, SECRET)


class CommentServiceTests(unittest.TestCase):
    def setUp(self):
        self.comments = MagicMock()
        self.tickets = MagicMock()
        self.service = CommentService(self.comments, self.tickets)

    def test_add_ok(self):
        self.tickets.get.return_value = make_ticket()
        self.comments.create.return_value = {"id": 1, "text": "Привет"}
        result = self.service.add(USER, 1, {"text": " Привет "})
        self.assertEqual(result["id"], 1)
        self.assertEqual(self.comments.create.call_args[0][:3], (1, USER["id"], "Привет"))

    def test_add_ticket_not_found(self):
        self.tickets.get.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.add(USER, 1, {"text": "Привет"})

    def test_add_empty_text(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ValidationError):
            self.service.add(USER, 1, {"text": "   "})
        self.comments.create.assert_not_called()

    def test_add_too_long_text(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ValidationError):
            self.service.add(USER, 1, {"text": "a" * 2001})

    def test_list_ok(self):
        self.tickets.get.return_value = make_ticket()
        self.comments.list_by_ticket.return_value = [{"id": 1}, {"id": 2}]
        self.assertEqual(len(self.service.list(1)), 2)

    def test_list_ticket_not_found(self):
        self.tickets.get.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.list(1)


class RequireTextTests(unittest.TestCase):
    def test_trims_value(self):
        self.assertEqual(require_text({"a": "  x "}, "a", 10), "x")

    def test_not_a_string(self):
        with self.assertRaises(ValidationError):
            require_text({"a": 5}, "a", 10)


if __name__ == "__main__":
    unittest.main()
