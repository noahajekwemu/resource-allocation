import unittest
from unittest.mock import patch

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

    def test_form_redirects_unauthenticated_user_to_login(self):
        response = self.client.get("/forms/issue_stock.html")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?next=/forms/issue_stock.html", response.location)

    def test_form_is_served_to_allowed_role(self):
        self.login_as("Store_Officer")
        response = self.client.get("/forms/issue_stock.html")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Submit issued stock", response.data)

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
