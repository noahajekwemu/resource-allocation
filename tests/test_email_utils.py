import os
import unittest
from unittest.mock import MagicMock, patch

from scripts import email_utils


class EmailUtilsTests(unittest.TestCase):
    def setUp(self):
        self.original_env = os.environ.copy()
        for key in (
            "EMAIL_NOTIFICATIONS_ENABLED",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_FROM_EMAIL",
            "SMTP_USE_TLS",
        ):
            os.environ.pop(key, None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)

    def enable_email(self):
        os.environ.update(
            {
                "EMAIL_NOTIFICATIONS_ENABLED": "true",
                "SMTP_HOST": "smtp.example.com",
                "SMTP_PORT": "587",
                "SMTP_USERNAME": "mailer",
                "SMTP_PASSWORD": "secret-password",
                "SMTP_FROM_EMAIL": "noreply@example.com",
                "SMTP_USE_TLS": "true",
            }
        )

    def test_send_email_noops_when_disabled(self):
        with patch("scripts.email_utils.smtplib.SMTP") as smtp:
            sent = email_utils.send_email("user@example.com", "Subject", "Body")

        self.assertFalse(sent)
        smtp.assert_not_called()

    def test_send_email_missing_config_logs_warning_without_password(self):
        os.environ["EMAIL_NOTIFICATIONS_ENABLED"] = "true"
        audit_writer = MagicMock()

        with self.assertLogs("scripts.email_utils", level="WARNING") as logs:
            sent = email_utils.send_email(
                "user@example.com", "Subject", "Body", audit_writer=audit_writer
            )

        self.assertFalse(sent)
        self.assertIn("SMTP configuration is missing", "\n".join(logs.output))
        self.assertNotIn("SMTP_PASSWORD", "\n".join(logs.output))
        self.assertNotIn("secret-password", "\n".join(logs.output))
        audit_writer.assert_called_once()
        self.assertEqual(audit_writer.call_args.args[0], "EMAIL_FAILED")

    def test_send_email_uses_smtp_and_writes_sent_audit(self):
        self.enable_email()
        audit_writer = MagicMock()
        smtp_instance = MagicMock()

        with patch("scripts.email_utils.smtplib.SMTP") as smtp:
            smtp.return_value.__enter__.return_value = smtp_instance
            sent = email_utils.send_email(
                ["user@example.com"], "Subject", "Body", audit_writer=audit_writer
            )

        self.assertTrue(sent)
        smtp.assert_called_once_with("smtp.example.com", 587, timeout=20)
        smtp_instance.starttls.assert_called_once_with()
        smtp_instance.login.assert_called_once_with("mailer", "secret-password")
        smtp_instance.send_message.assert_called_once()
        self.assertEqual(audit_writer.call_args.args[0], "EMAIL_SENT")

    def test_send_email_failure_does_not_raise_or_log_password(self):
        self.enable_email()
        audit_writer = MagicMock()
        with patch("scripts.email_utils.smtplib.SMTP", side_effect=RuntimeError("boom")):
            with self.assertLogs("scripts.email_utils", level="WARNING") as logs:
                sent = email_utils.send_email(
                    "user@example.com", "Subject", "Body", audit_writer=audit_writer
                )

        self.assertFalse(sent)
        self.assertNotIn("secret-password", "\n".join(logs.output))
        self.assertEqual(audit_writer.call_args.args[0], "EMAIL_FAILED")

    def test_recipient_emails_filters_by_role_school_and_active_status(self):
        users = [
            {"Email": "admin@example.com", "Role": "Admin", "Active": True},
            {"Email": "school@example.com", "Role": "School_User", "School_ID": "SCH-1"},
            {"Email": "other@example.com", "Role": "School_User", "School_ID": "SCH-2"},
            {"Email": "inactive@example.com", "Role": "Admin", "Active": False},
        ]

        self.assertEqual(
            email_utils.recipient_emails(users, {"School_User"}, "SCH-1"),
            ["school@example.com"],
        )
        self.assertEqual(
            email_utils.recipient_emails(users, {"Admin"}),
            ["admin@example.com"],
        )

    def test_workflow_helpers_build_expected_subjects(self):
        users = [{"Email": "approver@example.com", "Role": "Approver"}]
        with patch("scripts.email_utils.send_email", return_value=True) as send_email:
            result = email_utils.send_requisition_submitted_notification(
                {"requisition_id": "REQ001", "School_ID": "SCH-1"},
                users,
            )

        self.assertTrue(result)
        self.assertEqual(send_email.call_args.args[0], ["approver@example.com"])
        self.assertIn("REQ001", send_email.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
