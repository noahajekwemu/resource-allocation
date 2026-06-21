import unittest
from unittest.mock import patch

import pandas as pd
from werkzeug.exceptions import Forbidden

from scripts import form_api
from scripts.security_utils import user_can


class RolePermissionTests(unittest.TestCase):
    def setUp(self):
        form_api.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = form_api.app.test_client()

    def login_as(self, role, school_id=""):
        with self.client.session_transaction() as flask_session:
            flask_session["user"] = {
                "User_ID": "U1", "Email": "user@example.com", "Full_Name": "Test User",
                "Role": role, "School_ID": school_id,
            }

    def test_role_permission_map(self):
        self.assertTrue(user_can("approve_requisition", {"Role": "Approver"}))
        self.assertFalse(user_can("issue_stock", {"Role": "Approver"}))
        self.assertTrue(user_can("issue_stock", {"Role": "Store_Officer"}))
        self.assertFalse(user_can("approve_requisition", {"Role": "Store_Officer"}))

    def test_school_user_cannot_submit_for_another_school(self):
        self.login_as("School_User", "SCH-001")
        with patch("scripts.form_api.submit_requisition") as submit:
            response = self.client.post("/submit_requisition", json={"School_ID": "SCH-002", "items": []})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.get_json()["success"])
        submit.assert_not_called()

    def test_approver_cannot_issue_stock(self):
        self.login_as("Approver")
        response = self.client.post("/submit_issue_stock", json={"items": []})
        self.assertEqual(response.status_code, 403)

    def test_store_officer_cannot_approve_requisition(self):
        self.login_as("Store_Officer")
        response = self.client.post("/approve_requisition", json={"Requisition_ID": "REQ001"})
        self.assertEqual(response.status_code, 403)

    def test_write_endpoint_requires_login(self):
        response = self.client.post("/submit_receive_stock", json={"items": []})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "Please log in.")

    def test_health_allows_configured_dashboard_origins(self):
        allowed_origins = [
            "https://noahajekwemu.github.io",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ]
        for origin in allowed_origins:
            with self.subTest(origin=origin):
                response = self.client.get("/health", headers={"Origin": origin})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), {"status": "ok"})
                self.assertEqual(
                    response.headers.get("Access-Control-Allow-Origin"), origin
                )

    def test_health_rejects_unconfigured_cors_origin(self):
        response = self.client.get(
            "/health", headers={"Origin": "https://example.com"}
        )
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_protected_write_endpoint_has_no_cors_access(self):
        response = self.client.post(
            "/submit_receive_stock",
            json={"items": []},
            headers={"Origin": "https://noahajekwemu.github.io"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_form_redirects_unauthenticated_user_to_login(self):
        response = self.client.get("/forms/issue_stock.html")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?next=/forms/issue_stock.html", response.location)

    def test_form_is_served_to_allowed_role(self):
        self.login_as("Store_Officer")
        response = self.client.get("/forms/issue_stock.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Submit issued stock", response.data)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_form_is_forbidden_to_disallowed_role(self):
        self.login_as("Approver")
        response = self.client.get("/forms/issue_stock.html")
        self.assertEqual(response.status_code, 403)

    def test_unknown_form_returns_not_found_after_login(self):
        self.login_as("Admin")
        response = self.client.get("/forms/unknown.html")
        self.assertEqual(response.status_code, 404)

    def test_successful_login_redirects_to_role_default(self):
        expected_paths = {
            "Admin": "/forms/approve_requisition.html",
            "Approver": "/forms/approve_requisition.html",
            "Store_Officer": "/forms/issue_stock.html",
            "School_User": "/forms/requisition_form.html",
            "Viewer": "/api/items",
        }
        for role, expected_path in expected_paths.items():
            user = {
                "User_ID": "U1", "Email": "user@example.com", "Role": role,
                "School_ID": "SCH-001",
            }
            with self.subTest(role=role), patch(
                "scripts.form_api.authenticate_user", return_value=user
            ), patch("scripts.form_api._audit"):
                response = self.client.post(
                    "/login", data={"email": user["Email"], "password": "secret"}
                )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, expected_path)

    def test_successful_login_makes_session_permanent(self):
        user = {"User_ID": "U1", "Email": "admin@example.com", "Role": "Admin"}
        with patch("scripts.form_api.authenticate_user", return_value=user), patch(
            "scripts.form_api._audit"
        ):
            response = self.client.post(
                "/login", data={"email": user["Email"], "password": "secret"}
            )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as flask_session:
            self.assertTrue(flask_session.permanent)

    def test_403_handler_returns_friendly_message(self):
        with form_api.app.test_request_context("/forbidden"):
            response = form_api.app.make_response(
                form_api.app.handle_user_exception(Forbidden())
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json()["error"], "Access forbidden.")

    def test_admin_can_access_user_management_page(self):
        self.login_as("Admin")
        response = self.client.get("/forms/user_management.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"User Management", response.data)
        self.assertNotIn(b"Password_Hash", response.data)

    def test_non_admin_cannot_access_user_management_page(self):
        for role in ("Approver", "Store_Officer", "School_User", "Viewer"):
            with self.subTest(role=role):
                self.client = form_api.app.test_client()
                self.login_as(role)
                response = self.client.get("/forms/user_management.html")
                self.assertEqual(response.status_code, 403)

    def test_user_management_redirects_unauthenticated_user(self):
        response = self.client.get("/forms/user_management.html")
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/login?next=/forms/user_management.html", response.location
        )

    def test_get_users_hides_password_hash(self):
        self.login_as("Admin")
        users = pd.DataFrame([{
            "User_ID": "USR001", "Full_Name": "Admin User",
            "Email": "admin@example.com", "Role": "Admin", "School_ID": "",
            "Password_Hash": "must-not-leak", "Active": True,
            "Created_At": "2026-01-01T00:00:00+00:00",
        }])
        with patch("scripts.form_api._read_worksheet", return_value=users):
            response = self.client.get("/api/users")
        self.assertEqual(response.status_code, 200)
        returned_user = response.get_json()["users"][0]
        self.assertNotIn("Password_Hash", returned_user)
        self.assertEqual(returned_user["Email"], "admin@example.com")

    def test_admin_can_create_user_and_audit_action(self):
        self.login_as("Admin")
        users = pd.DataFrame([{"User_ID": "USR005", "Email": "old@example.com"}])
        payload = {
            "Full_Name": "New Viewer", "Email": "new@example.com",
            "Role": "Viewer", "School_ID": "", "Password": "secret",
        }
        with patch("scripts.form_api._read_worksheet", return_value=users), patch(
            "scripts.form_api._append_dict_row"
        ) as append, patch("scripts.form_api._audit") as audit:
            response = self.client.post("/api/users", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["user"]["User_ID"], "USR006")
        stored = append.call_args.args[1]
        self.assertNotIn("Password", stored)
        self.assertNotEqual(stored["Password_Hash"], "secret")
        audit.assert_called_once()
        self.assertEqual(audit.call_args.args[0], "CREATE_USER")

    def test_duplicate_user_email_is_rejected(self):
        self.login_as("Admin")
        users = pd.DataFrame([{"User_ID": "USR001", "Email": "user@example.com"}])
        with patch("scripts.form_api._read_worksheet", return_value=users), patch(
            "scripts.form_api._append_dict_row"
        ) as append, patch("scripts.form_api._audit"):
            response = self.client.post("/api/users", json={
                "Full_Name": "Duplicate", "Email": " USER@example.com ",
                "Role": "Viewer", "Password": "secret",
            })
        self.assertEqual(response.status_code, 400)
        self.assertIn("already exists", response.get_json()["error"])
        append.assert_not_called()

    def test_create_user_rejects_invalid_role(self):
        self.login_as("Admin")
        with patch("scripts.form_api._read_worksheet", return_value=pd.DataFrame()), patch(
            "scripts.form_api._append_dict_row"
        ) as append, patch("scripts.form_api._audit"):
            response = self.client.post("/api/users", json={
                "Full_Name": "Invalid Role", "Email": "invalid@example.com",
                "Role": "Owner", "Password": "secret",
            })
        self.assertEqual(response.status_code, 400)
        append.assert_not_called()

    def test_create_school_user_requires_school_id(self):
        self.login_as("Admin")
        with patch("scripts.form_api._read_worksheet", return_value=pd.DataFrame()), patch(
            "scripts.form_api._append_dict_row"
        ) as append, patch("scripts.form_api._audit"):
            response = self.client.post("/api/users", json={
                "Full_Name": "School User", "Email": "school@example.com",
                "Role": "School_User", "Password": "secret",
            })
        self.assertEqual(response.status_code, 400)
        self.assertIn("School_ID", response.get_json()["error"])
        append.assert_not_called()

    def test_admin_can_deactivate_user(self):
        self.login_as("Admin")
        users = pd.DataFrame([{
            "User_ID": "USR002", "Full_Name": "Target", "Email": "target@example.com",
            "Role": "Viewer", "School_ID": "", "Password_Hash": "hash",
            "Active": True, "Created_At": "2026-01-01",
        }])
        with patch("scripts.form_api._read_worksheet", return_value=users), patch(
            "scripts.form_api._update_row_by_id"
        ) as update, patch("scripts.form_api._audit") as audit:
            response = self.client.patch("/api/users/USR002", json={"Active": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["user"]["Active"])
        self.assertEqual(update.call_args.args[3], {"Active": False})
        self.assertEqual(audit.call_args.args[0], "DEACTIVATE_USER")

    def test_admin_can_reset_password(self):
        self.login_as("Admin")
        users = pd.DataFrame([{
            "User_ID": "USR002", "Full_Name": "Target", "Email": "target@example.com",
            "Role": "Viewer", "School_ID": "", "Password_Hash": "old-hash",
            "Active": True, "Created_At": "2026-01-01",
        }])
        with patch("scripts.form_api._read_worksheet", return_value=users), patch(
            "scripts.form_api._update_row_by_id"
        ) as update, patch("scripts.form_api._audit") as audit:
            response = self.client.post(
                "/api/users/USR002/reset-password", json={"Password": "new-secret"}
            )
        self.assertEqual(response.status_code, 200)
        stored_hash = update.call_args.args[3]["Password_Hash"]
        self.assertNotEqual(stored_hash, "new-secret")
        self.assertEqual(audit.call_args.args[0], "RESET_USER_PASSWORD")
        self.assertNotIn("Password_Hash", str(audit.call_args))

    def test_404_handler_returns_friendly_message(self):
        response = self.client.get("/route-that-does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Resource not found.")

    def test_authenticated_api_response_has_no_store_header(self):
        self.login_as("Viewer")
        with patch("scripts.form_api.get_items", return_value=[]):
            response = self.client.get("/api/items")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_login_honors_permitted_local_next_form(self):
        user = {"User_ID": "U1", "Email": "admin@example.com", "Role": "Admin"}
        with patch("scripts.form_api.authenticate_user", return_value=user), patch(
            "scripts.form_api._audit"
        ):
            response = self.client.post(
                "/login?next=/forms/issue_stock.html",
                data={"email": user["Email"], "password": "secret"},
            )
        self.assertEqual(response.location, "/forms/issue_stock.html")

    def test_login_rejects_next_form_not_permitted_for_role(self):
        user = {"User_ID": "U1", "Email": "approver@example.com", "Role": "Approver"}
        with patch("scripts.form_api.authenticate_user", return_value=user), patch(
            "scripts.form_api._audit"
        ):
            response = self.client.post(
                "/login?next=/forms/issue_stock.html",
                data={"email": user["Email"], "password": "secret"},
            )
        self.assertEqual(response.location, "/forms/approve_requisition.html")

    def test_login_rejects_unsafe_next_urls(self):
        user = {"User_ID": "U1", "Email": "admin@example.com", "Role": "Admin"}
        unsafe_urls = ["http://evil.com", "https://evil.com", "//evil.com"]
        for unsafe_url in unsafe_urls:
            with self.subTest(next=unsafe_url), patch(
                "scripts.form_api.authenticate_user", return_value=user
            ), patch("scripts.form_api._audit"):
                response = self.client.post(
                    "/login",
                    query_string={"next": unsafe_url},
                    data={"email": user["Email"], "password": "secret"},
                )
            self.assertEqual(response.location, "/forms/approve_requisition.html")


if __name__ == "__main__":
    unittest.main()
