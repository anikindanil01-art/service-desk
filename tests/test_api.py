import os
import shutil
import tempfile
import unittest

from app import create_app
from app.db import connect
from app.migrate import run_migrations


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        db_path = os.path.join(self.tmp, "test.db")
        conn = connect(db_path)
        run_migrations(conn)
        conn.close()
        self.app = create_app(
            {"DATABASE": db_path, "TESTING": True, "PASSWORD_ITERATIONS": 1000}
        )
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def register(self, username, role="USER", password="secret1"):
        response = self.client.post(
            "/auth/register",
            json={"username": username, "password": password, "role": role},
        )
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def login(self, username, password="secret1"):
        response = self.client.post(
            "/auth/login", json={"username": username, "password": password}
        )
        self.assertEqual(response.status_code, 200)
        return {"Authorization": "Bearer " + response.get_json()["access_token"]}

    def make_user(self, username, role="USER"):
        user = self.register(username, role)
        return user, self.login(username)

    def create_ticket(self, headers, **fields):
        body = {"subject": "Тема", "description": "Описание", "priority": "MEDIUM"}
        body.update(fields)
        response = self.client.post("/tickets", json=body, headers=headers)
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()


class AuthApiTests(ApiTestCase):
    def test_register_and_login(self):
        user = self.register("ivan")
        self.assertEqual(user["role"], "USER")
        headers = self.login("ivan")
        self.assertTrue(headers["Authorization"].startswith("Bearer "))

    def test_duplicate_username(self):
        self.register("ivan")
        response = self.client.post(
            "/auth/register", json={"username": "ivan", "password": "secret1"}
        )
        self.assertEqual(response.status_code, 409)

    def test_wrong_password(self):
        self.register("ivan")
        response = self.client.post(
            "/auth/login", json={"username": "ivan", "password": "wrong-pass"}
        )
        self.assertEqual(response.status_code, 401)

    def test_invalid_json_body(self):
        response = self.client.post("/auth/login", data="not json")
        self.assertEqual(response.status_code, 400)

    def test_protected_endpoint_without_token(self):
        self.assertEqual(self.client.get("/tickets").status_code, 401)

    def test_protected_endpoint_with_bad_token(self):
        response = self.client.get("/tickets", headers={"Authorization": "Bearer abc.def"})
        self.assertEqual(response.status_code, 401)


class TicketCrudApiTests(ApiTestCase):
    def test_create_and_get_ticket(self):
        user, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers, subject="Не работает VPN", priority="HIGH")
        self.assertEqual(ticket["status"], "NEW")
        self.assertEqual(ticket["author_id"], user["id"])
        response = self.client.get(f"/tickets/{ticket['id']}", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["subject"], "Не работает VPN")

    def test_create_without_token_is_denied(self):
        response = self.client.post("/tickets", json={"subject": "a", "description": "b"})
        self.assertEqual(response.status_code, 401)

    def test_create_invalid_body(self):
        _, headers = self.make_user("ivan")
        response = self.client.post("/tickets", json={"subject": ""}, headers=headers)
        self.assertEqual(response.status_code, 400)

    def test_get_unknown_ticket(self):
        _, headers = self.make_user("ivan")
        self.assertEqual(self.client.get("/tickets/999", headers=headers).status_code, 404)

    def test_filter_by_priority_and_status(self):
        _, headers = self.make_user("ivan")
        admin, admin_headers = self.make_user("boss", "ADMIN")
        self.create_ticket(headers, subject="t1", priority="LOW")
        high = self.create_ticket(headers, subject="t2", priority="HIGH")
        self.create_ticket(headers, subject="t3", priority="HIGH")
        self.client.patch(
            f"/tickets/{high['id']}/status", json={"status": "IN_PROGRESS"}, headers=admin_headers
        )
        by_priority = self.client.get("/tickets?priority=HIGH", headers=headers).get_json()
        self.assertEqual(len(by_priority["items"]), 2)
        by_status = self.client.get("/tickets?status=IN_PROGRESS", headers=headers).get_json()
        self.assertEqual([t["id"] for t in by_status["items"]], [high["id"]])
        both = self.client.get(
            "/tickets?priority=HIGH&status=NEW", headers=headers
        ).get_json()
        self.assertEqual(len(both["items"]), 1)

    def test_filter_by_assignee(self):
        _, headers = self.make_user("ivan")
        _, admin_headers = self.make_user("boss", "ADMIN")
        executor, _ = self.make_user("exec", "EXECUTOR")
        first = self.create_ticket(headers, subject="t1")
        self.create_ticket(headers, subject="t2")
        self.client.patch(
            f"/tickets/{first['id']}/assignee",
            json={"assignee_id": executor["id"]},
            headers=admin_headers,
        )
        result = self.client.get(
            f"/tickets?assignee_id={executor['id']}", headers=headers
        ).get_json()
        self.assertEqual([t["id"] for t in result["items"]], [first["id"]])

    def test_pagination(self):
        _, headers = self.make_user("ivan")
        for i in range(5):
            self.create_ticket(headers, subject=f"t{i}")
        page1 = self.client.get("/tickets?page=1&page_size=2", headers=headers).get_json()
        page3 = self.client.get("/tickets?page=3&page_size=2", headers=headers).get_json()
        self.assertEqual(len(page1["items"]), 2)
        self.assertEqual(len(page3["items"]), 1)
        self.assertEqual(page1["total"], 5)

    def test_invalid_filter_values(self):
        _, headers = self.make_user("ivan")
        self.assertEqual(self.client.get("/tickets?status=DONE", headers=headers).status_code, 400)
        self.assertEqual(self.client.get("/tickets?page=abc", headers=headers).status_code, 400)

    def test_update_by_author(self):
        _, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers)
        response = self.client.put(
            f"/tickets/{ticket['id']}", json={"subject": "Новая тема"}, headers=headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["subject"], "Новая тема")

    def test_update_by_stranger_is_denied(self):
        _, headers = self.make_user("ivan")
        _, other_headers = self.make_user("petr")
        ticket = self.create_ticket(headers)
        response = self.client.put(
            f"/tickets/{ticket['id']}", json={"subject": "Взлом"}, headers=other_headers
        )
        self.assertEqual(response.status_code, 403)


class StatusAndAccessApiTests(ApiTestCase):
    def test_full_status_lifecycle(self):
        _, headers = self.make_user("ivan")
        _, admin_headers = self.make_user("boss", "ADMIN")
        ticket = self.create_ticket(headers)
        for new_status in ("IN_PROGRESS", "RESOLVED", "CLOSED"):
            response = self.client.patch(
                f"/tickets/{ticket['id']}/status",
                json={"status": new_status},
                headers=admin_headers,
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json()["status"], new_status)

    def test_forbidden_transition_returns_409(self):
        _, headers = self.make_user("ivan")
        _, admin_headers = self.make_user("boss", "ADMIN")
        ticket = self.create_ticket(headers)
        for new_status in ("IN_PROGRESS", "RESOLVED", "CLOSED"):
            self.client.patch(
                f"/tickets/{ticket['id']}/status", json={"status": new_status}, headers=admin_headers
            )
        response = self.client.patch(
            f"/tickets/{ticket['id']}/status", json={"status": "NEW"}, headers=admin_headers
        )
        self.assertEqual(response.status_code, 409)
        skip = self.create_ticket(headers)
        response = self.client.patch(
            f"/tickets/{skip['id']}/status", json={"status": "RESOLVED"}, headers=admin_headers
        )
        self.assertEqual(response.status_code, 409)

    def test_user_cannot_delete_ticket(self):
        _, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers)
        response = self.client.delete(f"/tickets/{ticket['id']}", headers=headers)
        self.assertEqual(response.status_code, 403)

    def test_admin_soft_deletes_ticket(self):
        _, headers = self.make_user("ivan")
        _, admin_headers = self.make_user("boss", "ADMIN")
        ticket = self.create_ticket(headers)
        response = self.client.delete(f"/tickets/{ticket['id']}", headers=admin_headers)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.get(f"/tickets/{ticket['id']}", headers=headers).status_code, 404
        )
        listing = self.client.get("/tickets", headers=headers).get_json()
        self.assertEqual(listing["items"], [])

    def test_user_cannot_change_status(self):
        _, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers)
        response = self.client.patch(
            f"/tickets/{ticket['id']}/status", json={"status": "IN_PROGRESS"}, headers=headers
        )
        self.assertEqual(response.status_code, 403)

    def test_assign_executor_and_work_on_ticket(self):
        _, headers = self.make_user("ivan")
        _, admin_headers = self.make_user("boss", "ADMIN")
        executor, executor_headers = self.make_user("exec", "EXECUTOR")
        _, other_executor_headers = self.make_user("exec2", "EXECUTOR")
        ticket = self.create_ticket(headers)
        response = self.client.patch(
            f"/tickets/{ticket['id']}/assignee",
            json={"assignee_id": executor["id"]},
            headers=admin_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["assignee_id"], executor["id"])
        ok = self.client.patch(
            f"/tickets/{ticket['id']}/status", json={"status": "IN_PROGRESS"}, headers=executor_headers
        )
        self.assertEqual(ok.status_code, 200)
        denied = self.client.patch(
            f"/tickets/{ticket['id']}/status", json={"status": "RESOLVED"}, headers=other_executor_headers
        )
        self.assertEqual(denied.status_code, 403)

    def test_assignee_must_be_executor(self):
        user, headers = self.make_user("ivan")
        _, admin_headers = self.make_user("boss", "ADMIN")
        ticket = self.create_ticket(headers)
        response = self.client.patch(
            f"/tickets/{ticket['id']}/assignee",
            json={"assignee_id": user["id"]},
            headers=admin_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_only_admin_can_assign(self):
        user, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers)
        response = self.client.patch(
            f"/tickets/{ticket['id']}/assignee", json={"assignee_id": user["id"]}, headers=headers
        )
        self.assertEqual(response.status_code, 403)


class CommentsApiTests(ApiTestCase):
    def test_add_and_list_comments(self):
        user, headers = self.make_user("ivan")
        _, other_headers = self.make_user("petr")
        ticket = self.create_ticket(headers)
        url = f"/tickets/{ticket['id']}/comments"
        first = self.client.post(url, json={"text": "Первый"}, headers=headers)
        second = self.client.post(url, json={"text": "Второй"}, headers=other_headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        comments = self.client.get(url, headers=headers).get_json()
        self.assertEqual([c["text"] for c in comments], ["Первый", "Второй"])
        self.assertEqual(comments[0]["author_id"], user["id"])

    def test_comment_requires_token(self):
        _, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers)
        response = self.client.post(f"/tickets/{ticket['id']}/comments", json={"text": "x"})
        self.assertEqual(response.status_code, 401)

    def test_empty_comment_rejected(self):
        _, headers = self.make_user("ivan")
        ticket = self.create_ticket(headers)
        response = self.client.post(
            f"/tickets/{ticket['id']}/comments", json={"text": ""}, headers=headers
        )
        self.assertEqual(response.status_code, 400)

    def test_comments_of_unknown_ticket(self):
        _, headers = self.make_user("ivan")
        self.assertEqual(self.client.get("/tickets/404/comments", headers=headers).status_code, 404)


class DocsApiTests(ApiTestCase):
    def test_openapi_and_swagger_available(self):
        spec = self.client.get("/openapi.json").get_json()
        self.assertEqual(spec["openapi"], "3.0.3")
        self.assertIn("/tickets/{ticket_id}/status", spec["paths"])
        self.assertEqual(self.client.get("/docs").status_code, 200)

    def test_unknown_route_returns_json_error(self):
        response = self.client.get("/unknown")
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.get_json())


class MigrationTests(unittest.TestCase):
    def test_migrations_are_applied_once(self):
        conn = connect(":memory:")
        first = run_migrations(conn)
        second = run_migrations(conn)
        self.assertEqual(first, ["0001_init.sql", "0002_indexes.sql"])
        self.assertEqual(second, [])
        conn.close()


if __name__ == "__main__":
    unittest.main()
