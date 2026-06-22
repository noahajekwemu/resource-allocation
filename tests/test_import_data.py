import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts import import_data
from scripts.import_utils import SUPPORTED_SHEETS


def empty_existing():
    return {name: pd.DataFrame() for name in SUPPORTED_SHEETS}


class ImportDataTests(unittest.TestCase):
    def make_items_csv(self, directory):
        path = Path(directory) / "Items.csv"
        pd.DataFrame([{
            "Item_ID": "ITEM001", "Item_Name": "Mathematics Textbook", "Category": "Textbooks",
        }]).to_csv(path, index=False)
        return path

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = self.make_items_csv(temporary)
            with patch("scripts.import_data.read_existing_data", return_value=empty_existing()), patch(
                "scripts.import_data.db_connector.apply_import_plan"
            ) as apply, patch("scripts.import_data.db_connector.write_import_audit") as audit:
                report, report_path = import_data.execute_import(
                    path, "Items", commit=False, reports_dir=temporary
                )
            self.assertEqual(report["commit_status"], "dry-run-valid")
            self.assertEqual(report["rows_to_append"], 1)
            self.assertTrue(report_path.exists())
            apply.assert_not_called()
            audit.assert_not_called()

    def test_commit_applies_valid_plan_and_audits(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = self.make_items_csv(temporary)
            with patch("scripts.import_data.read_existing_data", return_value=empty_existing()), patch(
                "scripts.import_data.db_connector.apply_import_plan",
                return_value={"appended": 1, "updated": 0},
            ) as apply, patch("scripts.import_data.db_connector.write_import_audit") as audit:
                report, _ = import_data.execute_import(
                    path, "Items", commit=True, reports_dir=temporary
                )
            self.assertEqual(report["commit_status"], "committed")
            apply.assert_called_once()
            audit.assert_called_once()
            self.assertEqual(audit.call_args.args[2], "Success")

    def test_validation_failure_prevents_all_writes(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = Path(temporary) / "Items.csv"
            pd.DataFrame([{"Item_ID": "ITEM001", "Item_Name": "Book"}]).to_csv(path, index=False)
            with patch("scripts.import_data.read_existing_data", return_value=empty_existing()), patch(
                "scripts.import_data.db_connector.apply_import_plan"
            ) as apply, patch("scripts.import_data.db_connector.write_import_audit") as audit:
                report, _ = import_data.execute_import(path, "Items", commit=True, reports_dir=temporary)
            self.assertEqual(report["commit_status"], "validation-failed")
            apply.assert_not_called()
            audit.assert_not_called()

    def test_append_duplicate_rejection_and_upsert_behavior(self):
        existing = empty_existing()
        existing["Items"] = pd.DataFrame([{
            "Item_ID": "ITEM001", "Item_Name": "Old", "Category": "Textbooks",
        }])
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = self.make_items_csv(temporary)
            with patch("scripts.import_data.read_existing_data", return_value=existing):
                append, _ = import_data.execute_import(path, "Items", mode="append", reports_dir=temporary)
                upsert, _ = import_data.execute_import(path, "Items", mode="upsert", reports_dir=temporary)
        self.assertEqual(append["commit_status"], "validation-failed")
        self.assertEqual(upsert["rows_to_update"], 1)
        self.assertEqual(upsert["commit_status"], "dry-run-valid")

    def test_report_generation_writes_timestamped_json(self):
        report = import_data.build_report("Items.csv", "Items", "append", False)
        timestamp = datetime(2026, 6, 22, 12, 30, 45, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            path = import_data.write_import_report(report, temporary, timestamp)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(path.name, "import_report_20260622_123045.json")
        self.assertEqual(payload["target_sheet"], "Items")


if __name__ == "__main__":
    unittest.main()
