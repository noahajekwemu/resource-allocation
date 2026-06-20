import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.calculate_metrics import build_dashboard_data, write_dashboard_data


def sample_data():
    return {
        "items": pd.DataFrame(
            [
                {
                    "Item_ID": "ITEM-1",
                    "Item_Name": "Book",
                    "Category": "Learning",
                    "Reorder_Level": 10,
                },
                {
                    "Item_ID": "ITEM-2",
                    "Item_Name": "Chair",
                    "Category": "Furniture",
                    "Reorder_Level": 5,
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


if __name__ == "__main__":
    unittest.main()
