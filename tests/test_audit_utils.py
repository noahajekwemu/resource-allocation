import json
import unittest

from scripts.audit_utils import AUDIT_LOG_COLUMNS, build_audit_row


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


if __name__ == "__main__":
    unittest.main()
