import csv
import json
import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import generate_monthly_report


REPORT_TEST_ROOT = Path(__file__).resolve().parents[1] / "reports" / "monthly" / "_test"


def clean_report_test_root():
    shutil.rmtree(REPORT_TEST_ROOT, ignore_errors=True)


class MonthlyReportTests(unittest.TestCase):
    def setUp(self):
        clean_report_test_root()

    def tearDown(self):
        clean_report_test_root()

    def test_default_report_month_uses_previous_month(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(generate_monthly_report.default_report_month(now), "2025-12")

    def test_write_report_files_creates_json_csv_and_html(self):
        summary = {
            "report_month": "2026-06",
            "generated_at": "2026-07-01T00:00:00+00:00",
            "total_stock_received": 20,
            "total_stock_issued": 5,
            "requisitions_by_status": {"Fulfilled": 1},
            "fulfillment_rate_percent": 50.0,
            "top_requested_items": [{"Item_Name": "Book", "quantity_requested": 10}],
            "low_stock_items": [],
        }

        paths = generate_monthly_report.write_report_files(
            summary, REPORT_TEST_ROOT / "2026-06"
        )
        json_data = json.loads(paths["json"].read_text(encoding="utf-8"))
        with paths["csv"].open(encoding="utf-8") as csv_file:
            csv_rows = list(csv.DictReader(csv_file))
        html_text = paths["html"].read_text(encoding="utf-8")

        self.assertEqual(json_data["total_stock_received"], 20)
        self.assertEqual(csv_rows[0]["metric"], "report_month")
        self.assertIn("Monthly Executive Summary - 2026-06", html_text)

    def test_generate_monthly_report_uses_requested_month_and_output_dir(self):
        summary = {
            "report_month": "2026-06",
            "generated_at": "2026-07-01T00:00:00+00:00",
            "total_stock_received": 20,
            "total_stock_issued": 5,
            "requisitions_by_status": {},
            "fulfillment_rate_percent": 0,
            "top_requested_items": [],
            "low_stock_items": [],
        }
        with patch(
            "scripts.generate_monthly_report.get_monthly_executive_summary",
            return_value=summary,
        ) as mocked_summary:
            paths = generate_monthly_report.generate_monthly_report(
                "2026-06", REPORT_TEST_ROOT
            )

            mocked_summary.assert_called_once_with("2026-06")
            self.assertTrue(paths["json"].exists())
            self.assertEqual(paths["json"].parent.name, "2026-06")


if __name__ == "__main__":
    unittest.main()
