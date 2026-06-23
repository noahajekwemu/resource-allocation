import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import pandas as pd

from scripts import seed_sample_data
from scripts.calculate_metrics import build_dashboard_data
from scripts.db_connector import append_records


class SeedSampleDataTests(unittest.TestCase):
    def setUp(self):
        self.data = seed_sample_data.build_sample_data()

    def test_sample_data_meets_minimum_counts_and_status_mix(self):
        self.assertGreaterEqual(len(self.data["Items"]), 12)
        self.assertGreaterEqual(len(self.data["Schools"]), 20)
        self.assertGreaterEqual(len(self.data["Warehouses"]), 5)
        self.assertGreaterEqual(len(self.data["Transactions"]), 25)
        self.assertGreaterEqual(len(self.data["Requisitions"]), 15)
        statuses = pd.Series(row["Status"] for row in self.data["Requisitions"])
        self.assertGreaterEqual(statuses.eq("Fulfilled").sum(), 5)
        self.assertGreaterEqual(statuses.eq("Partially Fulfilled").sum(), 3)
        self.assertGreaterEqual(statuses.eq("Pending").sum(), 3)
        self.assertGreaterEqual(statuses.eq("Approved").sum(), 2)
        self.assertGreaterEqual(statuses.eq("Rejected").sum(), 2)

    def test_sample_data_has_valid_references_and_transaction_details(self):
        item_ids = {row["Item_ID"] for row in self.data["Items"]}
        school_ids = {row["School_ID"] for row in self.data["Schools"]}
        warehouse_ids = {row["Warehouse_ID"] for row in self.data["Warehouses"]}
        transaction_ids = {row["Transaction_ID"] for row in self.data["Transactions"]}
        requisition_ids = {row["Requisition_ID"] for row in self.data["Requisitions"]}
        for row in self.data["Transaction_Details"]:
            self.assertIn(row["Transaction_ID"], transaction_ids)
            self.assertIn(row["Item_ID"], item_ids)
        self.assertEqual(
            {row["Transaction_ID"] for row in self.data["Transaction_Details"]},
            transaction_ids,
        )
        for row in self.data["Transactions"]:
            self.assertIn(row["Warehouse_ID"], warehouse_ids)
            if row["Destination_School_ID"]:
                self.assertIn(row["Destination_School_ID"], school_ids)
        for row in self.data["Requisition_Details"]:
            self.assertIn(row["Requisition_ID"], requisition_ids)
            self.assertIn(row["Item_ID"], item_ids)

    def test_sample_data_uses_official_optional_schema_names(self):
        self.assertIn("Minimum_Stock", self.data["Items"][0])
        self.assertNotIn("Reorder_Level", self.data["Items"][0])
        self.assertIn("LGA", self.data["Warehouses"][0])
        self.assertIn("Zone", self.data["Warehouses"][0])
        self.assertNotIn("Location", self.data["Warehouses"][0])

    def test_dry_run_does_not_connect_or_write(self):
        with patch("scripts.seed_sample_data.append_demo_data") as append, redirect_stdout(
            StringIO()
        ) as output:
            result = seed_sample_data.main(["--dry-run"])
        self.assertEqual(result, 0)
        append.assert_not_called()
        self.assertIn("WARNING: Users and Audit_Log were not modified", output.getvalue())

    def test_append_skips_existing_ids(self):
        def existing(_sheet, worksheet):
            id_column = seed_sample_data.ID_COLUMNS[worksheet]
            spaced_column = id_column.replace("_", " ")
            return pd.DataFrame([{
                spaced_column: self.data[worksheet][0][id_column]
            }])

        with patch("scripts.db_connector.read_worksheet", side_effect=existing), patch(
            "scripts.db_connector.append_records",
            side_effect=lambda _sheet, _worksheet, records: len(records),
        ) as append:
            counts = seed_sample_data.append_demo_data(self.data)
        self.assertEqual(len(append.call_args_list), len(seed_sample_data.SEED_ORDER))
        for worksheet in seed_sample_data.SEED_ORDER:
            self.assertEqual(counts[worksheet], len(self.data[worksheet]) - 1)

    def test_bulk_append_refuses_protected_worksheets(self):
        for worksheet in ("Users", "Audit_Log"):
            with self.subTest(worksheet=worksheet), self.assertRaisesRegex(
                ValueError, "protected worksheet"
            ):
                append_records("sheet", worksheet, [{"ID": "1"}])

    def test_seed_data_populates_all_dashboard_requisition_datasets(self):
        dashboard = build_dashboard_data({
            "items": pd.DataFrame(self.data["Items"]),
            "schools": pd.DataFrame(self.data["Schools"]),
            "warehouses": pd.DataFrame(self.data["Warehouses"]),
            "transactions": pd.DataFrame(self.data["Transactions"]),
            "transaction_details": pd.DataFrame(self.data["Transaction_Details"]),
            "requisitions": pd.DataFrame(self.data["Requisitions"]),
            "requisition_details": pd.DataFrame(self.data["Requisition_Details"]),
        })
        for key in (
            "requisition_status_distribution",
            "requested_vs_approved_vs_fulfilled",
            "top_requested_items",
            "requests_by_lga",
        ):
            self.assertTrue(dashboard["charts"][key], key)
        self.assertTrue(dashboard["tables"]["recent_requisitions"])
        self.assertTrue(dashboard["tables"]["fulfillment_summary"])
        stocks = {row["Item_ID"]: row for row in dashboard["tables"]["stock_levels"]}
        self.assertEqual(stocks["ITEM012"]["Current_Stock"], 0)
        self.assertLessEqual(
            stocks["ITEM011"]["Current_Stock"], stocks["ITEM011"]["Minimum_Stock"]
        )
        self.assertGreater(
            stocks["ITEM005"]["Current_Stock"], stocks["ITEM005"]["Minimum_Stock"]
        )


if __name__ == "__main__":
    unittest.main()
