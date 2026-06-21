import csv
import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from scripts import backup_google_sheets
from scripts import db_connector


class BackupGoogleSheetsTests(unittest.TestCase):
    def test_backup_folder_path_uses_timestamp(self):
        timestamp = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
        path = backup_google_sheets.backup_folder_path(
            Path("backups"), timestamp
        )
        self.assertEqual(path, Path("backups") / "20260621_120000")

    def test_export_worksheet_writes_csv_and_json(self):
        worksheet = MagicMock()
        worksheet.get_all_values.return_value = [
            ["Item_ID", "Item_Name", "Quantity"],
            ["ITEM001", "Exercise Book", 25],
            ["ITEM002", "Pencil"],
        ]
        csv_text, json_text, row_count = backup_google_sheets.serialize_worksheet(
            worksheet
        )
        csv_rows = list(csv.DictReader(io.StringIO(csv_text)))
        json_rows = json.loads(json_text)

        self.assertEqual(row_count, 2)
        self.assertEqual(csv_rows[0]["Item_Name"], "Exercise Book")
        self.assertEqual(csv_rows[1]["Quantity"], "")
        self.assertEqual(json_rows[0]["Quantity"], 25)
        self.assertEqual(json_rows[1]["Quantity"], "")
        worksheet.get_all_values.assert_called_once_with()

    def test_build_manifest_includes_required_metadata(self):
        timestamp = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
        worksheets = list(db_connector.BACKUP_WORKSHEETS)
        row_counts = {name: 1 for name in worksheets}
        manifest = backup_google_sheets.build_manifest(
            timestamp, worksheets, row_counts
        )
        self.assertEqual(manifest["backup_timestamp"], timestamp.isoformat())
        self.assertEqual(manifest["spreadsheet_name"], db_connector.SPREADSHEET_NAME)
        self.assertEqual(manifest["worksheets_exported"], worksheets)
        self.assertEqual(manifest["row_counts"], row_counts)
        self.assertEqual(
            manifest["generated_by"], "scripts/backup_google_sheets.py"
        )


if __name__ == "__main__":
    unittest.main()
