import csv
import io
import unittest

import pandas as pd

from scripts.report_utils import (
    get_audit_report,
    get_executive_summary,
    get_fulfillment_report,
    get_requisition_report,
    get_stock_report,
    records_to_csv_response,
)


def report_data():
    return {
        "items": pd.DataFrame([
            {"Item_ID": "ITEM-1", "Item_Name": "Book", "Category": "Learning", "Minimum_Stock": 10},
            {"Item_ID": "ITEM-2", "Item_Name": "Chair", "Category": "Furniture", "Minimum_Stock": 5},
        ]),
        "schools": pd.DataFrame([
            {"School_ID": "SCH-1", "School_Name": "Alpha School"},
            {"School_ID": "SCH-2", "School_Name": "Beta School"},
        ]),
        "warehouses": pd.DataFrame([
            {"Warehouse_ID": "WH-1", "Warehouse_Name": "Central Store"},
        ]),
        "transactions": pd.DataFrame([
            {"Transaction_ID": "TX-1", "Transaction_Type": "IN", "Warehouse_ID": "WH-1"},
            {"Transaction_ID": "TX-2", "Transaction_Type": "OUT", "Warehouse_ID": "WH-1"},
        ]),
        "transaction_details": pd.DataFrame([
            {"Transaction_ID": "TX-1", "Item_ID": "ITEM-1", "Quantity": 20},
            {"Transaction_ID": "TX-2", "Item_ID": "ITEM-1", "Quantity": 5},
        ]),
        "requisitions": pd.DataFrame([
            {
                "Requisition_ID": "REQ-1", "School_ID": "SCH-1",
                "Requested_By": "Head Teacher", "Status": "Partially Fulfilled",
                "Request_Date": "2026-06-01", "Approved_By": "Approver",
                "Approval_Date": "2026-06-02",
            },
            {
                "Requisition_ID": "REQ-2", "School_ID": "SCH-2",
                "Requested_By": "Head Teacher 2", "Status": "Rejected",
                "Request_Date": "2026-06-03", "Approved_By": "Approver",
                "Approval_Date": "2026-06-04",
            },
        ]),
        "requisition_details": pd.DataFrame([
            {
                "Requisition_ID": "REQ-1", "Item_ID": "ITEM-1",
                "Quantity_Requested": 10, "Quantity_Approved": 8,
                "Quantity_Fulfilled": 4,
            },
            {
                "Requisition_ID": "REQ-2", "Item_ID": "ITEM-2",
                "Quantity_Requested": 4, "Quantity_Approved": 0,
                "Quantity_Fulfilled": 0,
            },
        ]),
        "audit_log": pd.DataFrame([
            {
                "Audit_ID": "AUD-1", "User_ID": "USR-1", "Action": "LOGIN",
                "Status": "Success", "Password_Hash": "must-not-leak",
                "Before_State": '{"Email":"user@example.com","Password_Hash":"nested-secret"}',
            }
        ]),
    }


class ReportUtilsTests(unittest.TestCase):
    def test_executive_summary_structure(self):
        summary = get_executive_summary(report_data())
        required = {
            "total_items", "total_schools", "total_warehouses",
            "total_requisitions", "approved_requisitions",
            "rejected_requisitions", "fulfilled_requisitions",
            "partially_fulfilled_requisitions", "pending_requisitions",
            "total_stock_received", "total_stock_issued",
            "fulfillment_rate_percent", "low_stock_items", "generated_at",
        }
        self.assertEqual(set(summary), required)
        self.assertEqual(summary["total_stock_received"], 20)
        self.assertEqual(summary["total_stock_issued"], 5)
        self.assertEqual(summary["fulfillment_rate_percent"], 50.0)

    def test_stock_report_structure_and_totals(self):
        rows = get_stock_report(report_data())
        self.assertEqual(set(rows[0]), {
            "Item_ID", "Item_Name", "Category", "Warehouse_ID",
            "Warehouse_Name", "Quantity_Received", "Quantity_Issued",
            "Current_Stock",
        })
        book = next(row for row in rows if row["Item_ID"] == "ITEM-1")
        self.assertEqual(book["Warehouse_Name"], "Central Store")
        self.assertEqual(book["Current_Stock"], 15)

    def test_requisition_report_structure_and_school_filter(self):
        rows = get_requisition_report(school_id="SCH-1", data=report_data())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["School_Name"], "Alpha School")
        self.assertIn("Request_Date", rows[0])
        self.assertIn("Approval_Date", rows[0])
        self.assertNotIn("Approved_At", rows[0])
        self.assertEqual(rows[0]["Total_Requested"], 10)
        self.assertEqual(rows[0]["Fulfillment_Percent"], 50.0)

    def test_fulfillment_report_calculates_outstanding(self):
        rows = get_fulfillment_report(school_id="SCH-1", data=report_data())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Outstanding_Quantity"], 4)

    def test_csv_generation(self):
        response = records_to_csv_response(
            [{"Item_ID": "ITEM-1", "Item_Name": "Book, ruled"}],
            "stock_report.csv",
        )
        rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(rows, [{"Item_ID": "ITEM-1", "Item_Name": "Book, ruled"}])
        self.assertTrue(response.content_type.startswith("text/csv"))
        self.assertIn("stock_report.csv", response.headers["Content-Disposition"])

    def test_password_hash_is_never_exposed(self):
        rows = get_audit_report(data=report_data())
        self.assertNotIn("Password_Hash", rows[0])
        self.assertNotIn("Password_Hash", rows[0]["Before_State"])
        self.assertNotIn("nested-secret", rows[0]["Before_State"])
        combined = {
            "summary": get_executive_summary(report_data()),
            "stock": get_stock_report(report_data()),
            "requisitions": get_requisition_report(data=report_data()),
            "fulfillment": get_fulfillment_report(data=report_data()),
            "audit": rows,
        }
        self.assertNotIn("Password_Hash", str(combined))


if __name__ == "__main__":
    unittest.main()
