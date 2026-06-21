import json
import unittest
from unittest.mock import MagicMock, patch

from scripts import form_api
from scripts.audit_utils import (
    AUDIT_LOG_COLUMNS,
    AUDIT_LOG_HEADERS,
    build_audit_row,
    write_audit_log,
)


class AuditUtilsTests(unittest.TestCase):
    def test_audit_row_formats_actor_states_and_required_columns(self):
        row = build_audit_row(
            "approve requisition", "Requisition", "REQ001",
            {"Status": "Pending"}, {"Status": "Approved"}, "Success",
            user={"User_ID": "U1", "Email": "approver@example.com", "Role": "Approver"},
            ip_address="127.0.0.1",
        )
        self.assertEqual(list(row), AUDIT_LOG_COLUMNS)
        self.assertEqual(row["User_ID"], "U1")
        self.assertEqual(row["Role"], "Approver")
        self.assertEqual(json.loads(row["Before_State"]), {"Status": "Pending"})
        self.assertEqual(json.loads(row["After_State"]), {"Status": "Approved"})
        self.assertEqual(row["IPAddress"], "127.0.0.1")

    @patch("scripts.db_connector.connect_to_sheet")
    def test_write_audit_log_creates_missing_headers(self, connect_to_sheet):
        worksheet = MagicMock()
        worksheet.row_values.return_value = []
        connect_to_sheet.return_value.worksheet.return_value = worksheet

        write_audit_log("logout", "User", "U1", None, None, "Success")

        worksheet.update.assert_called_once_with(
            range_name="A1:M1", values=[AUDIT_LOG_HEADERS]
        )
        worksheet.append_row.assert_called_once()

    @patch("scripts.db_connector.connect_to_sheet")
    def test_write_audit_log_appends_columns_in_header_order(self, connect_to_sheet):
        worksheet = MagicMock()
        worksheet.row_values.return_value = AUDIT_LOG_HEADERS.copy()
        connect_to_sheet.return_value.worksheet.return_value = worksheet

        row = write_audit_log(
            "receive stock", "Transaction", "TX1",
            {"Quantity": 1}, {"Quantity": 3}, "Success",
            user={"User_ID": "U1", "Email": "store@example.com", "Role": "Storekeeper"},
        )

        worksheet.update.assert_not_called()
        worksheet.append_row.assert_called_once_with(
            [row[column] for column in AUDIT_LOG_HEADERS]
        )

    def test_none_and_mapping_states_are_json_serialized(self):
        row = build_audit_row(
            "submit requisition", "Requisition", "REQ1",
            None, {"Items": ["ITEM1"]}, "Success",
        )

        self.assertEqual(json.loads(row["Before_State"]), None)
        self.assertEqual(json.loads(row["After_State"]), {"Items": ["ITEM1"]})

    def test_failed_login_audit_payload(self):
        with form_api.app.test_request_context(
            "/login", method="POST", json={"email": "bad@example.com", "password": "wrong"}
        ), patch("scripts.form_api.authenticate_user", return_value=None), patch(
            "scripts.form_api._audit"
        ) as audit:
            response = form_api.login_route()

        self.assertEqual(response[1], 401)
        audit.assert_called_once_with(
            "login", "User", "bad@example.com", None, {"Email": "bad@example.com"},
            status="Failed", remarks="Invalid credentials", user={"Email": "bad@example.com"},
        )

    def test_successful_login_audit_payload(self):
        user = {
            "User_ID": "U1", "Email": "user@example.com", "Role": "Requester",
            "Status": "Active",
        }
        with form_api.app.test_request_context(
            "/login", method="POST", json={"email": "user@example.com", "password": "valid"}
        ), patch("scripts.form_api.authenticate_user", return_value=user), patch(
            "scripts.form_api._audit"
        ) as audit:
            response = form_api.login_route()

        self.assertEqual(response.status_code, 200)
        audit.assert_called_once_with(
            "login", "User", "U1", None, {"Email": "user@example.com"},
            status="Success", user=user,
        )


if __name__ == "__main__":
    unittest.main()
