import unittest
from unittest.mock import patch

from scripts import form_api


def stored_detail(**overrides):
    detail = {
        "Req_Detail_ID": "RD001",
        "Item_ID": "ITEM-001",
        "Quantity_Requested": 10,
        "Quantity_Approved": 0,
        "Available_Stock": 8,
    }
    detail.update(overrides)
    return detail


class RequisitionApprovalTests(unittest.TestCase):
    def test_approval_allows_partial_quantity_when_stock_is_lower_than_requested(self):
        cleaned = form_api._clean_approval_items(
            [{"Req_Detail_ID": "RD001", "Quantity_Approved": 8}],
            [stored_detail()],
        )

        self.assertEqual(cleaned[0]["Quantity_Approved"], 8)

    def test_approval_rejects_quantity_above_requested_quantity(self):
        with self.assertRaisesRegex(ValueError, "cannot exceed requested"):
            form_api._clean_approval_items(
                [{"Req_Detail_ID": "RD001", "Quantity_Approved": 11}],
                [stored_detail()],
            )

    def test_approval_rejects_quantity_above_available_stock(self):
        with self.assertRaisesRegex(ValueError, "Insufficient stock"):
            form_api._clean_approval_items(
                [{"Req_Detail_ID": "RD001", "Quantity_Approved": 9}],
                [stored_detail()],
            )

    def test_approval_validates_combined_stock_for_duplicate_items(self):
        with self.assertRaisesRegex(ValueError, "Insufficient stock"):
            form_api._clean_approval_items(
                [
                    {"Req_Detail_ID": "RD001", "Quantity_Approved": 6},
                    {"Req_Detail_ID": "RD002", "Quantity_Approved": 3},
                ],
                [
                    stored_detail(),
                    stored_detail(Req_Detail_ID="RD002", Quantity_Requested=5),
                ],
            )

    def test_approval_notification_failure_does_not_block_route(self):
        client = form_api.app.test_client()
        with client.session_transaction() as session:
            session["user"] = {
                "User_ID": "USR001",
                "Full_Name": "Approver",
                "Email": "approver@example.com",
                "Role": "Approver",
            }

        before = {"header": {"Requisition_ID": "REQ001", "School_ID": "SCH-1"}, "details": []}
        with patch.object(form_api, "get_requisition", return_value=before), patch.object(
            form_api,
            "approve_requisition",
            return_value={"success": True, "requisition_id": "REQ001", "status": "Approved"},
        ), patch.object(form_api, "_audit"), patch.object(
            form_api, "_notification_users", return_value=[{"Email": "school@example.com", "Role": "School_User", "School_ID": "SCH-1"}]
        ), patch.object(
            form_api,
            "send_requisition_decision_notification",
            side_effect=RuntimeError("email unavailable"),
        ):
            response = client.post(
                "/api/approve-requisition",
                json={"Requisition_ID": "REQ001", "items": []},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
