import unittest
from unittest.mock import patch

import pandas as pd

from scripts import db_connector


def requisitions_dataframe(**overrides):
    row = {
        "Requisition_ID": "REQ-2026-000001",
        "School_ID": "SCH-001",
        "Request_Date": "2026-06-11",
        "Status": "Pending",
        "Approved_By": "",
        "Approval_Date": "",
        "Remarks": "Classroom supplies",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def requisition_details_dataframe(**overrides):
    row = {
        "Req_Detail_ID": "RD-2026-000001",
        "Requisition_ID": "REQ-2026-000001",
        "Item_ID": "ITEM-001",
        "Quantity_Requested": 10,
        "Quantity_Approved": 0,
        "Quantity_Fulfilled": 0,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def items_dataframe():
    return pd.DataFrame([{"Item_ID": "ITEM-001", "Item_Name": "Exercise Book"}])


def schools_dataframe():
    return pd.DataFrame([{"School_ID": "SCH-001", "School_Name": "Demo School"}])


class RequisitionValidationTests(unittest.TestCase):
    def test_valid_requisition_data_passes(self):
        db_connector.validate_requisition_data(
            requisitions_dataframe(),
            requisition_details_dataframe(),
            items_dataframe(),
            schools_dataframe(),
        )

    def test_requisition_detail_requires_existing_requisition_id(self):
        with self.assertRaisesRegex(ValueError, "unknown Requisition_ID"):
            db_connector.validate_requisition_data(
                requisitions_dataframe(),
                requisition_details_dataframe(Requisition_ID="REQ-404"),
                items_dataframe(),
                schools_dataframe(),
            )

    def test_requisition_detail_requires_existing_item_id(self):
        with self.assertRaisesRegex(ValueError, "unknown Item_ID"):
            db_connector.validate_requisition_data(
                requisitions_dataframe(),
                requisition_details_dataframe(Item_ID="ITEM-404"),
                items_dataframe(),
                schools_dataframe(),
            )

    def test_requisition_requires_existing_school_id(self):
        with self.assertRaisesRegex(ValueError, "unknown School_ID"):
            db_connector.validate_requisition_data(
                requisitions_dataframe(School_ID="SCH-404"),
                requisition_details_dataframe(),
                items_dataframe(),
                schools_dataframe(),
            )

    def test_requisition_status_must_be_allowed_value(self):
        with self.assertRaisesRegex(ValueError, "invalid Status"):
            db_connector.validate_requisition_data(
                requisitions_dataframe(Status="In Review"),
                requisition_details_dataframe(),
                items_dataframe(),
                schools_dataframe(),
            )

    def test_read_requisition_worksheets_reads_normalized_sheets(self):
        worksheet_data = {
            db_connector.REQUISITIONS_WORKSHEET: requisitions_dataframe(),
            db_connector.REQUISITION_DETAILS_WORKSHEET: requisition_details_dataframe(),
            db_connector.ITEMS_WORKSHEET: items_dataframe(),
            db_connector.SCHOOLS_WORKSHEET: schools_dataframe(),
        }

        with patch.object(
            db_connector,
            "read_worksheet",
            side_effect=lambda sheet_name, worksheet_name: worksheet_data[worksheet_name],
        ) as read_worksheet:
            data = db_connector.read_requisition_worksheets("Educational_Supplies_Logs")

        self.assertEqual(
            [
                call.args[1]
                for call in read_worksheet.call_args_list
            ],
            [
                db_connector.REQUISITIONS_WORKSHEET,
                db_connector.SCHOOLS_WORKSHEET,
                db_connector.REQUISITION_DETAILS_WORKSHEET,
                db_connector.ITEMS_WORKSHEET,
            ],
        )
        self.assertIn("requisitions", data)
        self.assertIn("requisition_details", data)

    def test_read_requisition_worksheets_checks_requisitions_before_details(self):
        invalid_requisitions = requisitions_dataframe().drop(columns=["Requisition_ID"])
        worksheet_data = {
            db_connector.REQUISITIONS_WORKSHEET: invalid_requisitions,
            db_connector.SCHOOLS_WORKSHEET: schools_dataframe(),
        }

        with patch.object(
            db_connector,
            "read_worksheet",
            side_effect=lambda sheet_name, worksheet_name: worksheet_data[worksheet_name],
        ) as read_worksheet:
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                db_connector.read_requisition_worksheets("Educational_Supplies_Logs")

        self.assertEqual(
            [
                call.args[1]
                for call in read_worksheet.call_args_list
            ],
            [
                db_connector.REQUISITIONS_WORKSHEET,
                db_connector.SCHOOLS_WORKSHEET,
            ],
        )


if __name__ == "__main__":
    unittest.main()
