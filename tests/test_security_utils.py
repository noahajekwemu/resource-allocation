import unittest
from unittest.mock import patch

import pandas as pd

from scripts import security_utils


class SecurityUtilsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
