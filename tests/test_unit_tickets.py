import unittest
from unittest.mock import MagicMock

from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.services.tickets import TicketService
from tests.helpers import ADMIN, EXECUTOR, STRANGER, USER, make_ticket, make_user


class TicketServiceBase(unittest.TestCase):
    def setUp(self):
        self.tickets = MagicMock()
        self.users = MagicMock()
        self.service = TicketService(self.tickets, self.users)


class CreateTicketTests(TicketServiceBase):
    def test_create_ok(self):
        self.tickets.create.return_value = 5
        self.tickets.get.return_value = make_ticket(id=5, priority="HIGH")
        result = self.service.create(
            USER, {"subject": " Тема ", "description": "Описание", "priority": "HIGH"}
        )
        self.assertEqual(result["id"], 5)
        self.assertNotIn("is_deleted", result)
        args = self.tickets.create.call_args[0]
        self.assertEqual(args[0], "Тема")
        self.assertEqual(args[3], USER["id"])

    def test_create_default_priority(self):
        self.tickets.create.return_value = 1
        self.tickets.get.return_value = make_ticket()
        self.service.create(USER, {"subject": "a", "description": "b"})
        self.assertEqual(self.tickets.create.call_args[0][2], "MEDIUM")

    def test_create_empty_subject(self):
        with self.assertRaises(ValidationError):
            self.service.create(USER, {"subject": "  ", "description": "b"})

    def test_create_missing_description(self):
        with self.assertRaises(ValidationError):
            self.service.create(USER, {"subject": "a"})

    def test_create_subject_too_long(self):
        with self.assertRaises(ValidationError):
            self.service.create(USER, {"subject": "a" * 201, "description": "b"})

    def test_create_invalid_priority(self):
        with self.assertRaises(ValidationError):
            self.service.create(USER, {"subject": "a", "description": "b", "priority": "URGENT"})

    def test_create_invalid_assignee_type(self):
        with self.assertRaises(ValidationError):
            self.service.create(USER, {"subject": "a", "description": "b", "assignee_id": "2"})


class ListTicketsTests(TicketServiceBase):
    def test_list_first_page(self):
        self.tickets.list.return_value = [make_ticket()]
        self.tickets.count.return_value = 1
        result = self.service.list()
        self.tickets.list.assert_called_once_with(None, None, None, 10, 0)
        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["items"]), 1)

    def test_list_offset_for_third_page(self):
        self.tickets.list.return_value = []
        self.tickets.count.return_value = 0
        self.service.list(page=3, page_size=10)
        self.assertEqual(self.tickets.list.call_args[0][4], 20)

    def test_list_passes_filters(self):
        self.tickets.list.return_value = []
        self.tickets.count.return_value = 0
        self.service.list(status="NEW", priority="HIGH", assignee_id=2)
        self.tickets.list.assert_called_once_with("NEW", "HIGH", 2, 10, 0)

    def test_list_page_size_is_capped(self):
        self.tickets.list.return_value = []
        self.tickets.count.return_value = 0
        result = self.service.list(page_size=1000)
        self.assertEqual(result["page_size"], 100)

    def test_list_invalid_status(self):
        with self.assertRaises(ValidationError):
            self.service.list(status="DONE")

    def test_list_invalid_priority(self):
        with self.assertRaises(ValidationError):
            self.service.list(priority="URGENT")

    def test_list_invalid_page(self):
        with self.assertRaises(ValidationError):
            self.service.list(page=0)
        with self.assertRaises(ValidationError):
            self.service.list(page_size=0)


class GetTicketTests(TicketServiceBase):
    def test_get_ok(self):
        self.tickets.get.return_value = make_ticket(id=3)
        self.assertEqual(self.service.get(3)["id"], 3)

    def test_get_not_found(self):
        self.tickets.get.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.get(3)

    def test_get_deleted_is_not_found(self):
        self.tickets.get.return_value = make_ticket(is_deleted=1)
        with self.assertRaises(NotFoundError):
            self.service.get(1)


class UpdateTicketTests(TicketServiceBase):
    def test_author_can_update(self):
        self.tickets.get.return_value = make_ticket()
        self.service.update(USER, 1, {"subject": "Новая тема"})
        self.assertEqual(self.tickets.update.call_args[0][1], {"subject": "Новая тема"})

    def test_assignee_can_update(self):
        self.tickets.get.return_value = make_ticket(assignee_id=EXECUTOR["id"])
        self.service.update(EXECUTOR, 1, {"priority": "LOW"})
        self.tickets.update.assert_called_once()

    def test_admin_can_update(self):
        self.tickets.get.return_value = make_ticket()
        self.service.update(ADMIN, 1, {"description": "Новое описание"})
        self.tickets.update.assert_called_once()

    def test_stranger_cannot_update(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ForbiddenError):
            self.service.update(STRANGER, 1, {"subject": "x"})
        self.tickets.update.assert_not_called()

    def test_update_without_fields(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ValidationError):
            self.service.update(USER, 1, {})

    def test_update_invalid_priority(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ValidationError):
            self.service.update(USER, 1, {"priority": "URGENT"})

    def test_update_not_found(self):
        self.tickets.get.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.update(USER, 1, {"subject": "x"})


class DeleteTicketTests(TicketServiceBase):
    def test_admin_soft_deletes(self):
        self.tickets.get.return_value = make_ticket()
        self.service.delete(ADMIN, 1)
        self.tickets.soft_delete.assert_called_once()

    def test_non_admin_forbidden(self):
        self.tickets.get.return_value = make_ticket()
        for user in (USER, EXECUTOR, STRANGER):
            with self.assertRaises(ForbiddenError):
                self.service.delete(user, 1)
        self.tickets.soft_delete.assert_not_called()

    def test_delete_already_deleted(self):
        self.tickets.get.return_value = make_ticket(is_deleted=1)
        with self.assertRaises(NotFoundError):
            self.service.delete(ADMIN, 1)


class ChangeStatusTests(TicketServiceBase):
    def _set_status(self, status):
        self.tickets.get.return_value = make_ticket(status=status, assignee_id=EXECUTOR["id"])

    def test_allowed_transitions(self):
        chain = [("NEW", "IN_PROGRESS"), ("IN_PROGRESS", "RESOLVED"), ("RESOLVED", "CLOSED")]
        for current, new in chain:
            with self.subTest(transition=f"{current}->{new}"):
                self._set_status(current)
                self.service.change_status(EXECUTOR, 1, {"status": new})
                self.tickets.set_status.assert_called_with(1, new)

    def test_forbidden_transitions(self):
        bad = [
            ("CLOSED", "NEW"),
            ("CLOSED", "IN_PROGRESS"),
            ("NEW", "RESOLVED"),
            ("NEW", "CLOSED"),
            ("IN_PROGRESS", "NEW"),
            ("RESOLVED", "NEW"),
            ("RESOLVED", "IN_PROGRESS"),
        ]
        for current, new in bad:
            with self.subTest(transition=f"{current}->{new}"):
                self._set_status(current)
                with self.assertRaises(ConflictError):
                    self.service.change_status(ADMIN, 1, {"status": new})
        self.tickets.set_status.assert_not_called()

    def test_admin_can_change_status(self):
        self.tickets.get.return_value = make_ticket(status="NEW")
        self.service.change_status(ADMIN, 1, {"status": "IN_PROGRESS"})
        self.tickets.set_status.assert_called_once_with(1, "IN_PROGRESS")

    def test_other_executor_forbidden(self):
        self.tickets.get.return_value = make_ticket(assignee_id=555)
        with self.assertRaises(ForbiddenError):
            self.service.change_status(EXECUTOR, 1, {"status": "IN_PROGRESS"})

    def test_author_cannot_change_status(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ForbiddenError):
            self.service.change_status(USER, 1, {"status": "IN_PROGRESS"})

    def test_unknown_status_value(self):
        self._set_status("NEW")
        with self.assertRaises(ValidationError):
            self.service.change_status(EXECUTOR, 1, {"status": "DONE"})

    def test_missing_status_value(self):
        self._set_status("NEW")
        with self.assertRaises(ValidationError):
            self.service.change_status(EXECUTOR, 1, {})


class AssignTests(TicketServiceBase):
    def test_admin_assigns_executor(self):
        self.tickets.get.return_value = make_ticket()
        self.users.get_by_id.return_value = EXECUTOR
        self.service.assign(ADMIN, 1, {"assignee_id": EXECUTOR["id"]})
        self.assertEqual(self.tickets.set_assignee.call_args[0][:2], (1, EXECUTOR["id"]))

    def test_non_admin_forbidden(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ForbiddenError):
            self.service.assign(USER, 1, {"assignee_id": 2})

    def test_user_not_found(self):
        self.tickets.get.return_value = make_ticket()
        self.users.get_by_id.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.assign(ADMIN, 1, {"assignee_id": 404})

    def test_assignee_must_be_executor(self):
        self.tickets.get.return_value = make_ticket()
        self.users.get_by_id.return_value = make_user(7, "USER")
        with self.assertRaises(ValidationError):
            self.service.assign(ADMIN, 1, {"assignee_id": 7})
        self.tickets.set_assignee.assert_not_called()

    def test_assignee_id_must_be_number(self):
        self.tickets.get.return_value = make_ticket()
        with self.assertRaises(ValidationError):
            self.service.assign(ADMIN, 1, {"assignee_id": "abc"})


if __name__ == "__main__":
    unittest.main()
