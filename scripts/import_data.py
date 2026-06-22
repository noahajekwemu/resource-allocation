"""Safely validate and import CSV or XLSX data into Google Sheets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import db_connector
from scripts.import_utils import (
    KEY_COLUMNS,
    SUPPORTED_SHEETS,
    load_import_file,
    load_workbook_batch,
    plan_import,
    validate_import,
)


REPORTS_DIR = Path(__file__).resolve().parents[1] / "import_reports"


def read_existing_data() -> dict[str, pd.DataFrame]:
    return {
        sheet_name: db_connector.read_worksheet(
            db_connector.SPREADSHEET_NAME, sheet_name
        )
        for sheet_name in SUPPORTED_SHEETS
    }


def write_import_report(
    report: dict[str, Any],
    reports_dir: str | Path = REPORTS_DIR,
    timestamp: datetime | None = None,
) -> Path:
    report_time = timestamp or datetime.now(timezone.utc)
    destination = Path(reports_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"import_report_{report_time.strftime('%Y%m%d_%H%M%S')}.json"
    with path.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, ensure_ascii=False, indent=2, default=str)
        report_file.write("\n")
    return path


def build_report(file_path: str | Path, sheet_name: str, mode: str, commit: bool) -> dict[str, Any]:
    return {
        "target_sheet": sheet_name,
        "file_path": str(Path(file_path)),
        "mode": mode,
        "total_rows_read": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "rows_to_append": 0,
        "rows_to_update": 0,
        "validation_errors": [],
        "commit_status": "pending" if commit else "dry-run",
    }


def execute_import(
    file_path: str | Path,
    sheet_name: str,
    mode: str = "append",
    commit: bool = False,
    reports_dir: str | Path = REPORTS_DIR,
) -> tuple[dict[str, Any], Path]:
    """Validate, plan, optionally commit, and report one import."""
    report = build_report(file_path, sheet_name, mode, commit)
    try:
        dataframe = load_import_file(file_path, sheet_name)
        report["total_rows_read"] = len(dataframe)
        existing = read_existing_data()
        batch = load_workbook_batch(file_path)
        errors = validate_import(dataframe, sheet_name, existing, batch)
        plan = plan_import(dataframe, existing.get(sheet_name, pd.DataFrame()), sheet_name, mode)
        errors.extend(plan["errors"])
        report["validation_errors"] = errors
        report["invalid_rows"] = len(dataframe) if errors else 0
        report["valid_rows"] = 0 if errors else len(dataframe)
        report["rows_to_append"] = len(plan["append"]) if not errors else 0
        report["rows_to_update"] = len(plan["update"]) if not errors else 0

        if errors:
            report["commit_status"] = "validation-failed"
        elif not commit:
            report["commit_status"] = "dry-run-valid"
        else:
            print("Backup recommended: run python -m scripts.backup_google_sheets before importing.")
            try:
                result = db_connector.apply_import_plan(
                    db_connector.SPREADSHEET_NAME,
                    sheet_name,
                    plan["append"],
                    plan["update"],
                    KEY_COLUMNS[sheet_name],
                )
                imported_count = result["appended"] + result["updated"]
                report["commit_status"] = "committed"
                db_connector.write_import_audit(
                    db_connector.SPREADSHEET_NAME,
                    {
                        "target_sheet": sheet_name,
                        "imported_row_count": imported_count,
                        "mode": mode,
                        "file_name": Path(file_path).name,
                    },
                    "Success",
                )
            except Exception:
                report["commit_status"] = "commit-failed"
                try:
                    db_connector.write_import_audit(
                        db_connector.SPREADSHEET_NAME,
                        {
                            "target_sheet": sheet_name,
                            "imported_row_count": 0,
                            "mode": mode,
                            "file_name": Path(file_path).name,
                        },
                        "Failure",
                    )
                except Exception:
                    pass
                raise
    except Exception as exc:
        if not report["validation_errors"]:
            report["validation_errors"] = [str(exc)]
            report["invalid_rows"] = report["total_rows_read"]
            report["commit_status"] = "failed"
        report_path = write_import_report(report, reports_dir)
        setattr(exc, "import_report", report)
        setattr(exc, "import_report_path", report_path)
        raise

    report_path = write_import_report(report, reports_dir)
    return report, report_path


def print_report(report: dict[str, Any], report_path: Path) -> None:
    labels = (
        ("target_sheet", "Target sheet"), ("file_path", "File path"),
        ("mode", "Mode"), ("total_rows_read", "Total rows read"),
        ("valid_rows", "Valid rows"), ("invalid_rows", "Invalid rows"),
        ("rows_to_append", "Rows to append"), ("rows_to_update", "Rows to update"),
        ("commit_status", "Commit status"),
    )
    for key, label in labels:
        print(f"{label}: {report[key]}")
    print("Validation errors:")
    if report["validation_errors"]:
        for error in report["validation_errors"]:
            print(f"- {error}")
    else:
        print("- None")
    print(f"Import report: {report_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="CSV or XLSX file to import")
    parser.add_argument("--sheet", required=True, choices=SUPPORTED_SHEETS)
    parser.add_argument("--mode", choices=("append", "upsert"), default="append")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--dry-run", action="store_true", help="validate without writing")
    action.add_argument("--commit", action="store_true", help="write a valid import")
    args = parser.parse_args(argv)
    try:
        report, report_path = execute_import(
            args.file, args.sheet, args.mode, args.commit
        )
    except Exception as exc:
        report = getattr(exc, "import_report", build_report(args.file, args.sheet, args.mode, args.commit))
        report_path = getattr(exc, "import_report_path", write_import_report(report))
        print_report(report, report_path)
        return 1
    print_report(report, report_path)
    return 0 if not report["validation_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
