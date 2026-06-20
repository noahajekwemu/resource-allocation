import unittest
from unittest.mock import patch

import pandas as pd

from scripts import form_api


def requisitions_dataframe(status="Approved"):
    return pd.DataFrame(
        [
            {
                "Requisition_ID": "REQ001",
                "School_ID": "SCH-001",
                "Request_Date": "2026-06-11",
                "Status": status,
            }
        ]
    )


def requisition_details_dataframe(approved=10, fulfilled=0):
    return pd.DataFrame(
        [
            {
                "Req_Detail_ID": "RD001",
                "Requisition_ID": "REQ001",
                "Item_ID": "ITEM-001",
                "Quantity_Requested": 10,
                "Quantity_Approved": approved,
                "Quantity_Fulfilled": fulfilled,
            }
        ]
    )


def transactions_dataframe(requisition_id="REQ001"):
    return pd.DataFrame(
        [
            {
                "Transaction_ID": "TXN001",
                "Transaction_Type": "OUT",
                "Requisition_ID": requisition_id,
            }
        ]
    )


def transaction_details_dataframe(quantity):
    return pd.DataFrame(
        [
            {
                "Detail_ID": "TD001",
                "Transaction_ID": "TXN001",
                "Item_ID": "ITEM-001",
                "Quantity": quantity,
            }
        ]
    )


class RequisitionFulfillmentTests(unittest.TestCase):
    def run_fulfillment(self, requisitions, requisition_details, transaction_details):
        worksheet_data = {
            form_api.TRANSACTIONS_WORKSHEET: transactions_dataframe(),
            form_api.TRANSACTION_DETAILS_WORKSHEET: transaction_details,
            form_api.REQUISITIONS_WORKSHEET: requisitions,
            form_api.REQUISITION_DETAILS_WORKSHEET: requisition_details,
        }
        updates = []

        with patch.object(
            form_api,
            "_read_worksheet",
            side_effect=lambda worksheet_name: worksheet_data[worksheet_name],
        ), patch.object(
            form_api,
            "_update_row_by_id",
            side_effect=lambda worksheet, columns, row_id, values: updates.append(
                (worksheet, row_id, values)
            ),
        ):
            result = form_api.update_fulfillment("TXN001")

        return result, updates

    def test_partial_fulfillment_updates_quantity_and_status(self):
        result, updates = self.run_fulfillment(
            requisitions_dataframe(),
            requisition_details_dataframe(approved=10, fulfilled=0),
            transaction_details_dataframe(quantity=4),
        )

        self.assertEqual(result["status"], "Partially Fulfilled")
        self.assertIn(
            (form_api.REQUISITION_DETAILS_WORKSHEET, "RD001", {"Quantity_Fulfilled": 4}),
            updates,
        )
        self.assertIn(
            (form_api.REQUISITIONS_WORKSHEET, "REQ001", {"Status": "Partially Fulfilled"}),
            updates,
        )

    def test_full_fulfillment_updates_quantity_and_status(self):
        result, updates = self.run_fulfillment(
            requisitions_dataframe(status="Partially Fulfilled"),
            requisition_details_dataframe(approved=10, fulfilled=6),
            transaction_details_dataframe(quantity=4),
        )

        self.assertEqual(result["status"], "Fulfilled")
        self.assertIn(
            (form_api.REQUISITION_DETAILS_WORKSHEET, "RD001", {"Quantity_Fulfilled": 10}),
            updates,
        )
        self.assertIn(
            (form_api.REQUISITIONS_WORKSHEET, "REQ001", {"Status": "Fulfilled"}),
            updates,
        )

    def test_over_fulfillment_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeds approved quantity"):
            self.run_fulfillment(
                requisitions_dataframe(),
                requisition_details_dataframe(approved=10, fulfilled=6),
                transaction_details_dataframe(quantity=5),
            )

    def test_invalid_requisition_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Only Approved or Partially Fulfilled"):
            self.run_fulfillment(
                requisitions_dataframe(status="Pending"),
                requisition_details_dataframe(approved=10, fulfilled=0),
                transaction_details_dataframe(quantity=4),
            )


if __name__ == "__main__":
    unittest.main()
