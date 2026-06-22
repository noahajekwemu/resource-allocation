import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.import_utils import load_import_file, plan_import, validate_import


class ImportUtilsTests(unittest.TestCase):
    def setUp(self):
        self.items = pd.DataFrame([
            {"Item_ID": "ITEM001", "Item_Name": "Book", "Category": "Textbooks"},
            {"Item_ID": "ITEM002", "Item_Name": "Chair", "Category": "Furniture"},
        ])
        self.context = {
            "Items": self.items,
            "Schools": pd.DataFrame([{"School_ID": "SCH001"}]),
            "Warehouses": pd.DataFrame([{"Warehouse_ID": "WH001"}]),
            "Transactions": pd.DataFrame([{"Transaction_ID": "TXN001"}]),
            "Requisitions": pd.DataFrame([{"Requisition_ID": "REQ001"}]),
        }

    def test_loads_csv(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = Path(temporary) / "Items.csv"
            self.items.to_csv(path, index=False)
            loaded = load_import_file(path, "Items")
        self.assertEqual(loaded.to_dict(orient="records"), self.items.to_dict(orient="records"))

    def test_loads_xlsx(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = Path(temporary) / "import.xlsx"
            self.items.to_excel(path, sheet_name="Items", index=False)
            loaded = load_import_file(path, "Items")
        self.assertEqual(list(loaded.columns), list(self.items.columns))
        self.assertEqual(len(loaded), 2)

    def test_missing_required_columns(self):
        errors = validate_import(self.items.drop(columns=["Category"]), "Items")
        self.assertIn("Missing required columns: Category", errors)

    def test_duplicate_ids_are_rejected(self):
        duplicate = pd.concat([self.items.iloc[[0]], self.items.iloc[[0]]], ignore_index=True)
        self.assertTrue(any("Duplicate import key" in error for error in validate_import(duplicate, "Items")))

    def test_invalid_and_negative_quantities(self):
        data = pd.DataFrame([
            {"Transaction_ID": "TXN001", "Item_ID": "ITEM001", "Quantity": "1.5", "Condition": "GOOD"},
            {"Transaction_ID": "TXN001", "Item_ID": "ITEM002", "Quantity": -1, "Condition": "GOOD"},
        ])
        errors = validate_import(data, "Transaction_Details", self.context)
        self.assertTrue(any("valid integer" in error for error in errors))
        self.assertTrue(any("cannot be negative" in error for error in errors))

    def test_invalid_requisition_status(self):
        data = pd.DataFrame([{
            "Requisition_ID": "REQ002", "Date": "2026-06-01", "School_ID": "SCH001",
            "Requested_By": "Officer", "Status": "Unknown", "Approved_By": "",
            "Approved_At": "", "Remarks": "",
        }])
        self.assertTrue(any("Invalid requisition Status" in error for error in validate_import(data, "Requisitions", self.context)))

    def test_foreign_keys_use_existing_and_batch_data(self):
        details = pd.DataFrame([{
            "Transaction_ID": "TXN002", "Item_ID": "ITEM003", "Quantity": 2, "Condition": "GOOD",
        }])
        errors = validate_import(details, "Transaction_Details", self.context)
        self.assertTrue(any("Unknown Transaction_ID" in error for error in errors))
        batch = {
            "Transactions": pd.DataFrame([{"Transaction_ID": "TXN002"}]),
            "Items": pd.DataFrame([{"Item_ID": "ITEM003", "Item_Name": "Desk", "Category": "Furniture"}]),
        }
        self.assertEqual(validate_import(details, "Transaction_Details", self.context, batch), [])

    def test_append_rejects_existing_and_upsert_splits_plan(self):
        incoming = pd.DataFrame([
            {"Item_ID": "ITEM001", "Item_Name": "Updated Book", "Category": "Textbooks"},
            {"Item_ID": "ITEM003", "Item_Name": "Desk", "Category": "Furniture"},
        ])
        append = plan_import(incoming, self.items, "Items", "append")
        self.assertTrue(append["errors"])
        upsert = plan_import(incoming, self.items, "Items", "upsert")
        self.assertEqual(len(upsert["update"]), 1)
        self.assertEqual(len(upsert["append"]), 1)


if __name__ == "__main__":
    unittest.main()
