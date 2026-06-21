"""Read-only CSV and JSON backup utility for the production Google Sheet."""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import db_connector
except (ImportError, ModuleNotFoundError):
    import db_connector


BACKUPS_DIR = Path(__file__).resolve().parents[1] / "backups"
GENERATED_BY = "scripts/backup_google_sheets.py"


def backup_folder_path(
    base_dir: Path = BACKUPS_DIR,
    timestamp: datetime | None = None,
) -> Path:
    """Return the timestamped destination path without creating it."""
    backup_time = timestamp or datetime.now(timezone.utc)
    return Path(base_dir) / backup_time.strftime("%Y%m%d_%H%M%S")


def _records_from_values(values: list[list[Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    if not values:
        return [], []

    headers = [str(value) for value in values[0]]
    records = []
    for source_row in values[1:]:
        row = list(source_row[:len(headers)])
        row.extend([""] * (len(headers) - len(row)))
        records.append(dict(zip(headers, row)))
    return headers, records


def serialize_worksheet(worksheet: Any) -> tuple[str, str, int]:
    """Return CSV text, JSON text, and data-row count for worksheet values."""
    headers, records = _records_from_values(worksheet.get_all_values())
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=headers)
    if headers:
        writer.writeheader()
        writer.writerows(records)
    json_text = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    return csv_buffer.getvalue(), json_text, len(records)


def export_worksheet(worksheet: Any, worksheet_name: str, destination: Path) -> int:
    """Export one worksheet without issuing any write operation to Google Sheets."""
    csv_text, json_text, row_count = serialize_worksheet(worksheet)
    destination.mkdir(parents=True, exist_ok=True)

    csv_path = destination / f"{worksheet_name}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        csv_file.write(csv_text)

    json_path = destination / f"{worksheet_name}.json"
    with json_path.open("w", encoding="utf-8") as json_file:
        json_file.write(json_text)

    return row_count


def build_manifest(
    timestamp: datetime,
    worksheets: list[str],
    row_counts: dict[str, int],
) -> dict[str, Any]:
    return {
        "backup_timestamp": timestamp.isoformat(),
        "spreadsheet_name": db_connector.SPREADSHEET_NAME,
        "worksheets_exported": worksheets,
        "row_counts": row_counts,
        "generated_by": GENERATED_BY,
    }


def create_backup(
    base_dir: Path = BACKUPS_DIR,
    timestamp: datetime | None = None,
) -> Path:
    """Export configured worksheets and return the created backup directory."""
    backup_time = timestamp or datetime.now(timezone.utc)
    destination = backup_folder_path(base_dir, backup_time)
    destination.mkdir(parents=True, exist_ok=False)

    spreadsheet = db_connector.connect_to_sheet(db_connector.SPREADSHEET_NAME)
    exported = []
    row_counts = {}
    for worksheet_name in db_connector.BACKUP_WORKSHEETS:
        logging.info("Exporting worksheet %s", worksheet_name)
        worksheet = spreadsheet.worksheet(worksheet_name)
        row_counts[worksheet_name] = export_worksheet(
            worksheet, worksheet_name, destination
        )
        exported.append(worksheet_name)

    manifest = build_manifest(backup_time, exported, row_counts)
    manifest_path = destination / "backup_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
        manifest_file.write("\n")

    return destination


def main() -> None:
    destination = create_backup()
    logging.info("Backup completed: %s", destination)
    print(f"Backup completed: {destination}")


if __name__ == "__main__":
    main()
