import unittest
from unittest.mock import patch

import pandas as pd
from flask import Flask

from scripts import security_utils


class SecurityUtilsTests(unittest.TestCase):
    def test_production_requires_secret_key(self):
        app = Flask(__name__)
        with patch.dict(
            "os.environ", {"APP_ENV": "production"}, clear=True
        ), self.assertRaisesRegex(RuntimeError, "FORM_API_SECRET_KEY"):
            security_utils.configure_app_security(app)

    def test_development_uses_fallback_secret_key(self):
        app = Flask(__name__)
        with patch.dict("os.environ", {}, clear=True), self.assertLogs(
            level="WARNING"
        ) as logs:
            app_env = security_utils.configure_app_security(app)
        self.assertEqual(app_env, "development")
        self.assertEqual(app.secret_key, security_utils.DEVELOPMENT_SECRET_KEY)
        self.assertIn("insecure development fallback", " ".join(logs.output))

    def test_session_cookie_config_matches_environment(self):
        for app_env, secure in (("development", False), ("production", True)):
            app = Flask(__name__)
            with self.subTest(app_env=app_env), patch.dict(
                "os.environ",
                {"APP_ENV": app_env, "FORM_API_SECRET_KEY": "test-secret"},
                clear=True,
            ):
                security_utils.configure_app_security(app)
            self.assertTrue(app.config["SESSION_COOKIE_HTTPONLY"])
            self.assertEqual(app.config["SESSION_COOKIE_SAMESITE"], "Lax")
            self.assertEqual(app.config["SESSION_COOKIE_SECURE"], secure)
            self.assertEqual(
                app.config["PERMANENT_SESSION_LIFETIME"].total_seconds(), 3600
            )

    def test_password_hashing_and_verification(self):
        password_hash = security_utils.hash_password("correct horse battery staple")
        self.assertNotEqual(password_hash, "correct horse battery staple")
        self.assertTrue(security_utils.verify_password("correct horse battery staple", password_hash))
        self.assertFalse(security_utils.verify_password("wrong", password_hash))

    def test_authenticate_rejects_invalid_password(self):
        user = {"User_ID": "U1", "Email": "user@example.com", "Role": "Viewer", "Active": True, "Password_Hash": security_utils.hash_password("right")}
        with patch("scripts.security_utils.get_user_by_email", return_value=user):
            self.assertIsNone(security_utils.authenticate_user("user@example.com", "wrong"))

    def test_authenticate_rejects_inactive_user(self):
        user = {"User_ID": "U1", "Email": "user@example.com", "Role": "Viewer", "Active": False, "Password_Hash": security_utils.hash_password("right")}
        with patch("scripts.security_utils.get_user_by_email", return_value=user):
            self.assertIsNone(security_utils.authenticate_user("user@example.com", "right"))

    def test_get_user_does_not_match_email_case_or_space(self):
        users = pd.DataFrame([{"Email": " User@Example.com ", "Role": "Viewer"}])
        with patch("scripts.security_utils._read_users", return_value=users):
            self.assertEqual(security_utils.get_user_by_email("user@example.com")["Role"], "Viewer")

    def test_create_user_record_hashes_password_and_hides_it_publicly(self):
        record = security_utils.create_user_record(
            "USR006", "New User", " NEW@EXAMPLE.COM ", "Viewer", "secret"
        )
        self.assertNotEqual(record["Password_Hash"], "secret")
        self.assertTrue(security_utils.verify_password("secret", record["Password_Hash"]))
        self.assertNotIn("Password_Hash", security_utils.public_user_record(record))
        self.assertNotIn("Password", record)

    def test_create_school_user_requires_school_id(self):
        with self.assertRaisesRegex(ValueError, "School_ID"):
            security_utils.create_user_record(
                "USR006", "School User", "school@example.com",
                "School_User", "secret",
            )


if __name__ == "__main__":
    unittest.main()
