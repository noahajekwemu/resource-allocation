"""Loading, validation, and planning helpers for controlled data imports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_SHEETS = (
    "Items", "Schools", "Warehouses", "Transactions", "Transaction_Details",
    "Requisitions", "Requisition_Details",
)

REQUIRED_COLUMNS = {
    "Items": ("Item_ID", "Item_Name", "Category"),
    "Schools": ("School_ID", "School_Name", "LGA", "Zone", "School_Type", "Status"),
    "Warehouses": ("Warehouse_ID", "Warehouse_Name", "LGA", "Zone", "Status"),
    "Transactions": (
        "Transaction_ID", "Date", "Type", "Warehouse_ID", "School_ID", "Source",
        "Requisition_ID", "Remarks",
    ),
    "Transaction_Details": ("Transaction_ID", "Item_ID", "Quantity", "Condition"),
    "Requisitions": (
        "Requisition_ID", "Date", "School_ID", "Requested_By", "Status",
        "Approved_By", "Approved_At", "Remarks",
    ),
    "Requisition_Details": (
        "Requisition_ID", "Item_ID", "Quantity_Requested", "Quantity_Approved",
        "Quantity_Fulfilled",
    ),
}

KEY_COLUMNS = {
    "Items": ("Item_ID",),
    "Schools": ("School_ID",),
    "Warehouses": ("Warehouse_ID",),
    "Transactions": ("Transaction_ID",),
    "Transaction_Details": ("Transaction_ID", "Item_ID"),
    "Requisitions": ("Requisition_ID",),
    "Requisition_Details": ("Requisition_ID", "Item_ID"),
}

COLUMN_ALIASES = {
    "Transactions": {
        "Date": ("Date", "Transaction_Date"),
        "Type": ("Type", "Transaction_Type"),
        "School_ID": ("School_ID", "Destination_School_ID"),
    },
    "Requisitions": {
        "Date": ("Date", "Request_Date"),
        "Approved_At": ("Approved_At", "Approval_Date"),
    },
}

NUMERIC_COLUMNS = {
    "Transaction_Details": ("Quantity",),
    "Requisition_Details": (
        "Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled",
    ),
}

DATE_COLUMNS = {
    "Transactions": ("Date",),
    "Requisitions": ("Date", "Approved_At"),
}

REQUISITION_STATUSES = {
    "Pending", "Approved", "Rejected", "Partially Fulfilled", "Fulfilled",
}


def normalize_column_name(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def canonicalize_columns(dataframe: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    """Return a copy whose recognized columns use the documented import names."""
    canonical = dataframe.copy()
    lookup = {normalize_column_name(column): column for column in canonical.columns}
    renames = {}
    for target in REQUIRED_COLUMNS.get(sheet_name, ()):
        candidates = COLUMN_ALIASES.get(sheet_name, {}).get(target, (target,))
        for candidate in candidates:
            source = lookup.get(normalize_column_name(candidate))
            if source is not None:
                renames[source] = target
                break
    return canonical.rename(columns=renames)


def load_import_file(file_path: str | Path, sheet_name: str) -> pd.DataFrame:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        dataframe = pd.read_csv(path, dtype=object, keep_default_na=False)
    elif suffix == ".xlsx":
        dataframe = pd.read_excel(path, sheet_name=sheet_name, dtype=object, keep_default_na=False)
    else:
        raise ValueError("Unsupported file type. Use a .csv or .xlsx file.")
    return canonicalize_columns(dataframe, sheet_name)


def load_workbook_batch(file_path: str | Path) -> dict[str, pd.DataFrame]:
    """Load supported companion tabs from an XLSX file for foreign-key checks."""
    path = Path(file_path)
    if path.suffix.lower() != ".xlsx":
        return {}
    workbook = pd.ExcelFile(path)
    return {
        name: canonicalize_columns(
            pd.read_excel(workbook, sheet_name=name, dtype=object, keep_default_na=False),
            name,
        )
        for name in SUPPORTED_SHEETS if name in workbook.sheet_names
    }


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def record_key(record: dict[str, Any], key_columns: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_text(record.get(column)) for column in key_columns)


def dataframe_keys(dataframe: pd.DataFrame, sheet_name: str) -> set[tuple[str, ...]]:
    canonical = canonicalize_columns(dataframe, sheet_name)
    keys = KEY_COLUMNS[sheet_name]
    if canonical.empty or any(column not in canonical.columns for column in keys):
        return set()
    return {record_key(record, keys) for record in canonical.to_dict(orient="records")}


def _ids(context: dict[str, pd.DataFrame], sheet_name: str, column: str) -> set[str]:
    dataframe = canonicalize_columns(context.get(sheet_name, pd.DataFrame()), sheet_name)
    if column not in dataframe.columns:
        return set()
    return {_text(value) for value in dataframe[column] if _text(value)}


def validate_import(
    dataframe: pd.DataFrame,
    sheet_name: str,
    existing: dict[str, pd.DataFrame] | None = None,
    batch: dict[str, pd.DataFrame] | None = None,
) -> list[str]:
    """Return all validation errors without modifying the provided data."""
    if sheet_name not in SUPPORTED_SHEETS:
        return [f"Unsupported target sheet: {sheet_name}"]
    data = canonicalize_columns(dataframe, sheet_name)
    existing = existing or {}
    batch = batch or {}
    errors: list[str] = []

    missing = [column for column in REQUIRED_COLUMNS[sheet_name] if column not in data.columns]
    if missing:
        return ["Missing required columns: " + ", ".join(missing)]

    keys = KEY_COLUMNS[sheet_name]
    for column in keys:
        blank_rows = [str(index + 2) for index, value in enumerate(data[column]) if not _text(value)]
        if blank_rows:
            errors.append(f"{column} is blank on row(s): {', '.join(blank_rows)}")

    key_values = [record_key(record, keys) for record in data.to_dict(orient="records")]
    duplicates = sorted({key for key in key_values if key_values.count(key) > 1 and all(key)})
    if duplicates:
        errors.append("Duplicate import key(s): " + ", ".join(" / ".join(key) for key in duplicates))

    for column in NUMERIC_COLUMNS.get(sheet_name, ()):
        for index, value in enumerate(data[column], start=2):
            text = _text(value)
            try:
                number = float(text)
                if not number.is_integer():
                    raise ValueError
                if number < 0:
                    errors.append(f"{column} cannot be negative on row {index}")
            except (TypeError, ValueError):
                errors.append(f"{column} must be a valid integer on row {index}")

    for column in DATE_COLUMNS.get(sheet_name, ()):
        for index, value in enumerate(data[column], start=2):
            text = _text(value)
            if not text and column == "Approved_At":
                continue
            if not text or pd.isna(pd.to_datetime(text, errors="coerce")):
                errors.append(f"{column} must contain a parseable date on row {index}")

    if sheet_name == "Transactions":
        for index, value in enumerate(data["Type"], start=2):
            if _text(value).upper() not in {"IN", "OUT"}:
                errors.append(f"Type must be IN or OUT on row {index}")
    if sheet_name == "Requisitions":
        for index, value in enumerate(data["Status"], start=2):
            if _text(value) not in REQUISITION_STATUSES:
                errors.append(f"Invalid requisition Status on row {index}: {_text(value)}")

    reference_context = dict(existing)
    for name, frame in batch.items():
        reference_context[name] = pd.concat(
            [reference_context.get(name, pd.DataFrame()), frame], ignore_index=True
        )

    foreign_keys: list[tuple[str, str, str, bool]] = []
    if sheet_name == "Transaction_Details":
        foreign_keys = [("Transaction_ID", "Transactions", "Transaction_ID", False), ("Item_ID", "Items", "Item_ID", False)]
    elif sheet_name == "Transactions":
        foreign_keys = [("Warehouse_ID", "Warehouses", "Warehouse_ID", False)]
    elif sheet_name == "Requisitions":
        foreign_keys = [("School_ID", "Schools", "School_ID", False)]
    elif sheet_name == "Requisition_Details":
        foreign_keys = [("Requisition_ID", "Requisitions", "Requisition_ID", False), ("Item_ID", "Items", "Item_ID", False)]

    for source_column, target_sheet, target_column, allow_blank in foreign_keys:
        valid = _ids(reference_context, target_sheet, target_column)
        for index, value in enumerate(data[source_column], start=2):
            source_id = _text(value)
            if source_id or not allow_blank:
                if source_id not in valid:
                    errors.append(f"Unknown {source_column} on row {index}: {source_id or '[blank]'}")

    if sheet_name == "Transactions":
        valid_schools = _ids(reference_context, "Schools", "School_ID")
        for index, record in enumerate(data.to_dict(orient="records"), start=2):
            school_id = _text(record["School_ID"])
            transaction_type = _text(record["Type"]).upper()
            if transaction_type == "OUT" and not school_id:
                errors.append(f"School_ID is required for OUT transaction on row {index}")
            elif school_id and school_id not in valid_schools:
                errors.append(f"Unknown School_ID on row {index}: {school_id}")

    return errors


def plan_import(
    dataframe: pd.DataFrame,
    existing_dataframe: pd.DataFrame,
    sheet_name: str,
    mode: str,
) -> dict[str, Any]:
    """Split validated records into append and update operations."""
    if mode not in {"append", "upsert"}:
        raise ValueError("Mode must be append or upsert.")
    data = canonicalize_columns(dataframe, sheet_name)
    existing = canonicalize_columns(existing_dataframe, sheet_name)
    keys = KEY_COLUMNS[sheet_name]
    existing_keys = dataframe_keys(existing, sheet_name)
    records = data.to_dict(orient="records")
    duplicate_keys = sorted({record_key(record, keys) for record in records} & existing_keys)
    errors = []
    if mode == "append" and duplicate_keys:
        errors.append("Existing key(s) cannot be appended: " + ", ".join(" / ".join(key) for key in duplicate_keys))
    return {
        "append": [record for record in records if record_key(record, keys) not in existing_keys],
        "update": [record for record in records if mode == "upsert" and record_key(record, keys) in existing_keys],
        "errors": errors,
    }
