"""Generate monthly executive reports from the production Google Sheet."""

import argparse
import csv
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.report_utils import (
    get_monthly_executive_summary,
    monthly_summary_to_csv_rows,
    monthly_summary_to_html,
)


REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports" / "monthly"


def default_report_month(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    year = current.year
    month = current.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def report_output_dir(report_month: str, base_dir: Path = REPORTS_DIR) -> Path:
    return Path(base_dir) / report_month


def write_report_files(
    summary: dict[str, Any],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "executive_summary.json"
    csv_path = output_dir / "executive_summary.csv"
    html_path = output_dir / "executive_summary.html"

    with json_path.open("w", encoding="utf-8") as json_file:
        json.dump(summary, json_file, ensure_ascii=False, indent=2, allow_nan=False)
        json_file.write("\n")

    rows = monthly_summary_to_csv_rows(summary)
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["metric", "value"])
        writer.writeheader()
        writer.writerows(rows)

    html_path.write_text(monthly_summary_to_html(summary), encoding="utf-8")
    return {"json": json_path, "csv": csv_path, "html": html_path}


def generate_monthly_report(
    report_month: str | None = None,
    output_base_dir: Path = REPORTS_DIR,
) -> dict[str, Path]:
    month = report_month or os.environ.get("REPORT_MONTH") or default_report_month()
    summary = get_monthly_executive_summary(month)
    return write_report_files(summary, report_output_dir(month, output_base_dir))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate monthly executive reports.")
    parser.add_argument(
        "--month",
        help="Report month in YYYY-MM format. Defaults to REPORT_MONTH or the previous month.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPORTS_DIR,
        help="Base directory for monthly report output.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    paths = generate_monthly_report(args.month, args.output_dir)
    logging.info("Monthly report generated for %s", paths["json"].parent.name)
    print(f"Monthly report generated: {paths['json'].parent}")


if __name__ == "__main__":
    main()
