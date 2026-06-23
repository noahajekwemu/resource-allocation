import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.calculate_metrics import (
    build_dashboard_data,
    sanitize_for_json,
    write_dashboard_data,
)


def sample_data():
    return {
        "items": pd.DataFrame(
            [
                {
                    "Item_ID": "ITEM-1",
                    "Item_Name": "Book",
                    "Category": "Learning",
                    "Minimum_Stock": 10,
                },
                {
                    "Item_ID": "ITEM-2",
                    "Item_Name": "Chair",
                    "Category": "Furniture",
                    "Minimum_Stock": 5,
                },
            ]
        ),
        "schools": pd.DataFrame(
            [
                {
                    "School_ID": "SCH-1",
                    "School_Name": "Alpha School",
                    "LGA": "North",
                    "School_Type": "Primary",
                },
                {
                    "School_ID": "SCH-2",
                    "School_Name": "Beta School",
                    "LGA": "South",
                    "School_Type": "Primary",
                },
            ]
        ),
        "warehouses": pd.DataFrame(
            [
                {"Warehouse_ID": "WH-1", "Warehouse_Name": "Central"},
                {"Warehouse_ID": "WH-2", "Warehouse_Name": "South Store"},
            ]
        ),
        "requisitions": pd.DataFrame(
            [
                {
                    "Requisition_ID": "REQ-1",
                    "School_ID": "SCH-1",
                    "Request_Date": "2026-01-01",
                    "Status": "Fulfilled",
                },
                {
                    "Requisition_ID": "REQ-2",
                    "School_ID": "SCH-2",
                    "Request_Date": "2026-01-04",
                    "Status": "Partially Fulfilled",
                },
                {
                    "Requisition_ID": "REQ-3",
                    "School_ID": "SCH-2",
                    "Request_Date": "2026-01-05",
                    "Status": "Pending",
                },
                {
                    "Requisition_ID": "REQ-4",
                    "School_ID": "SCH-1",
                    "Request_Date": "2026-01-06",
                    "Status": "Approved",
                },
                {
                    "Requisition_ID": "REQ-5",
                    "School_ID": "SCH-1",
                    "Request_Date": "2026-01-07",
                    "Status": "Rejected",
                },
            ]
        ),
        "requisition_details": pd.DataFrame(
            [
                {
                    "Req_Detail_ID": "RD-1",
                    "Requisition_ID": "REQ-1",
                    "Item_ID": "ITEM-1",
                    "Quantity_Requested": 10,
                    "Quantity_Approved": 10,
                    "Quantity_Fulfilled": 10,
                },
                {
                    "Req_Detail_ID": "RD-2",
                    "Requisition_ID": "REQ-2",
                    "Item_ID": "ITEM-2",
                    "Quantity_Requested": 10,
                    "Quantity_Approved": 10,
                    "Quantity_Fulfilled": 5,
                },
            ]
        ),
        "transactions": pd.DataFrame(
            [
                {
                    "Transaction_ID": "TX-1",
                    "Transaction_Date": "2026-01-01",
                    "Transaction_Type": "IN",
                    "Warehouse_ID": "WH-1",
                    "Destination_School_ID": "",
                    "Requisition_ID": "",
                    "Source": "UBEC",
                },
                {
                    "Transaction_ID": "TX-2",
                    "Transaction_Date": "2026-01-03",
                    "Transaction_Type": "OUT",
                    "Warehouse_ID": "WH-1",
                    "Destination_School_ID": "SCH-1",
                    "Requisition_ID": "REQ-1",
                },
                {
                    "Transaction_ID": "TX-3",
                    "Transaction_Date": "2026-02-01",
                    "Transaction_Type": "IN",
                    "Warehouse_ID": "WH-2",
                    "Destination_School_ID": "",
                    "Requisition_ID": "",
                    "Source": "State",
                },
                {
                    "Transaction_ID": "TX-4",
                    "Transaction_Date": "2026-02-05",
                    "Transaction_Type": "OUT",
                    "Warehouse_ID": "WH-2",
                    "Destination_School_ID": "SCH-2",
                    "Requisition_ID": "REQ-2",
                },
            ]
        ),
        "transaction_details": pd.DataFrame(
            [
                {
                    "Detail_ID": "TD-1",
                    "Transaction_ID": "TX-1",
                    "Item_ID": "ITEM-1",
                    "Quantity": 100,
                },
                {
                    "Detail_ID": "TD-2",
                    "Transaction_ID": "TX-2",
                    "Item_ID": "ITEM-1",
                    "Quantity": 10,
                },
                {
                    "Detail_ID": "TD-3",
                    "Transaction_ID": "TX-3",
                    "Item_ID": "ITEM-2",
                    "Quantity": 20,
                },
                {
                    "Detail_ID": "TD-4",
                    "Transaction_ID": "TX-4",
                    "Item_ID": "ITEM-2",
                    "Quantity": 5,
                },
            ]
        ),
    }


class DashboardMetricsTests(unittest.TestCase):
    def setUp(self):
        self.dashboard = build_dashboard_data(sample_data())

    def test_inventory_and_requisition_kpis(self):
        kpis = self.dashboard["kpis"]
        self.assertEqual(kpis["inventory_accuracy"], 100.0)
        self.assertEqual(kpis["total_items"], 2)
        self.assertEqual(kpis["total_stock_units"], 105)
        self.assertEqual(kpis["low_stock_items"], 0)
        self.assertEqual(kpis["total_requisitions"], 5)
        self.assertEqual(kpis["pending_requisitions"], 1)
        self.assertEqual(kpis["approved_requisitions"], 1)
        self.assertEqual(kpis["fulfilled_requisitions"], 1)
        self.assertEqual(kpis["rejected_requisitions"], 1)

    def test_fulfillment_kpis(self):
        kpis = self.dashboard["kpis"]
        self.assertEqual(kpis["fulfillment_rate"], 75.0)
        self.assertEqual(kpis["partially_fulfilled_requisitions"], 1)
        self.assertEqual(kpis["average_fulfillment_days"], 2.0)

    def test_distribution_warehouse_and_monthly_metrics(self):
        schools = self.dashboard["school_distribution"]
        self.assertEqual(schools["top_10_schools"][0], {"school": "Alpha School", "quantity": 10})
        self.assertEqual(schools["bottom_10_schools"][0], {"school": "Beta School", "quantity": 5})
        self.assertEqual(
            self.dashboard["lga_distribution"],
            [{"lga": "North", "quantity": 10}, {"lga": "South", "quantity": 5}],
        )
        self.assertEqual(
            self.dashboard["warehouse_analytics"]["stock_levels"][0]["stock_level"],
            90,
        )
        self.assertEqual(
            self.dashboard["warehouse_analytics"]["total_outflows"][0]["total_outflows"],
            10,
        )
        self.assertEqual(
            self.dashboard["monthly_stock_movements"],
            [
                {"month": "2026-01", "in_quantity": 100, "out_quantity": 10},
                {"month": "2026-02", "in_quantity": 20, "out_quantity": 5},
            ],
        )

    def test_dashboard_data_is_json_serializable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data.json"
            write_dashboard_data(self.dashboard, output)
            with output.open(encoding="utf-8") as data_file:
                written = json.load(data_file)
        self.assertEqual(written["kpis"]["total_items"], 2)

    def test_dashboard_contains_official_top_level_sections(self):
        expected = {
            "inventory",
            "requisitions",
            "distribution",
            "accountability",
            "stock_levels",
            "requisition_status_breakdown",
            "requested_vs_approved_vs_fulfilled",
            "top_requested_items",
            "requests_by_lga",
            "recent_inventory_movements",
            "recent_requisitions",
            "fulfillment_summary",
            "last_updated",
        }
        self.assertTrue(expected.issubset(self.dashboard))

    def test_flat_transaction_rows_are_used_when_details_are_missing(self):
        data = sample_data()
        data["transactions"] = pd.DataFrame([
            {
                "Transaction_ID": "TX-FLAT-1",
                "Transaction_Date": "2026-03-01",
                "Transaction_Type": "IN",
                "Warehouse_ID": "WH-1",
                "Destination_School_ID": "",
                "Item_ID": "ITEM-1",
                "Quantity": 12,
            }
        ])
        data["transaction_details"] = pd.DataFrame()

        dashboard = build_dashboard_data(data)

        self.assertEqual(dashboard["kpis"]["total_stock_units"], 12)
        book_stock = next(row for row in dashboard["stock_levels"] if row["Item_ID"] == "ITEM-1")
        self.assertEqual(book_stock["Minimum_Stock"], 10)

    def test_missing_minimum_stock_uses_default_threshold(self):
        data = sample_data()
        data["items"] = pd.DataFrame([
            {"Item_ID": "ITEM-1", "Item_Name": "Book", "Category": "Learning"}
        ])
        data["transactions"] = pd.DataFrame([
            {
                "Transaction_ID": "TX-1",
                "Transaction_Date": "2026-01-01",
                "Transaction_Type": "IN",
                "Warehouse_ID": "WH-1",
                "Destination_School_ID": "",
            }
        ])
        data["transaction_details"] = pd.DataFrame([
            {"Detail_ID": "TD-1", "Transaction_ID": "TX-1", "Item_ID": "ITEM-1", "Quantity": 8}
        ])

        dashboard = build_dashboard_data(data)

        self.assertEqual(dashboard["kpis"]["low_stock_items"], 1)
        self.assertEqual(dashboard["stock_levels"][0]["Minimum_Stock"], 10)

    def test_sanitize_for_json_converts_invalid_numbers_to_none(self):
        sanitized = sanitize_for_json(
            {
                "float_nan": float("nan"),
                "numpy_nan": np.float64(np.nan),
                "positive_infinity": float("inf"),
                "negative_infinity": np.float64(-np.inf),
            }
        )

        self.assertEqual(
            sanitized,
            {
                "float_nan": None,
                "numpy_nan": None,
                "positive_infinity": None,
                "negative_infinity": None,
            },
        )

    def test_sanitize_for_json_converts_nat_and_dates(self):
        sanitized = sanitize_for_json(
            {
                "pandas_nat": pd.NaT,
                "numpy_nat": np.datetime64("NaT"),
                "timestamp": pd.Timestamp("2026-01-02T03:04:05Z"),
            }
        )

        self.assertIsNone(sanitized["pandas_nat"])
        self.assertIsNone(sanitized["numpy_nat"])
        self.assertEqual(sanitized["timestamp"], "2026-01-02T03:04:05+00:00")

    def test_sanitize_for_json_recurses_nested_dictionaries_and_lists(self):
        sanitized = sanitize_for_json(
            {
                "outer": [
                    {"value": np.float64(np.nan)},
                    (float("inf"), pd.Timestamp("2026-01-01")),
                ],
                "series": pd.Series([1, np.nan]),
                "frame": pd.DataFrame([{"Date": pd.NaT, "Quantity": np.int64(3)}]),
            }
        )

        self.assertEqual(sanitized["outer"][0]["value"], None)
        self.assertEqual(sanitized["outer"][1], [None, "2026-01-01T00:00:00"])
        self.assertEqual(sanitized["series"], [1, None])
        self.assertEqual(sanitized["frame"], [{"Date": None, "Quantity": 3}])

    def test_write_dashboard_data_outputs_parseable_strict_json(self):
        dashboard = {
            "generated_at": pd.Timestamp("2026-01-01T00:00:00Z"),
            "rows": [{"Date": np.nan, "Quantity": np.float64(np.inf)}],
        }

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data.json"
            write_dashboard_data(dashboard, output)
            raw_json = output.read_text(encoding="utf-8")

        parsed = json.loads(raw_json)
        self.assertNotIn("NaN", raw_json)
        self.assertNotIn("Infinity", raw_json)
        self.assertEqual(parsed["rows"], [{"Date": None, "Quantity": None}])

    def test_strict_json_dump_rejects_unsanitized_nan(self):
        with self.assertRaises(ValueError):
            json.dumps({"value": math.nan}, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
