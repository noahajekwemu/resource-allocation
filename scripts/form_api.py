import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SPREADSHEET_NAME = "Educational_Supplies_Logs"
ITEMS_WORKSHEET = "Items"
SCHOOLS_WORKSHEET = "Schools"
WAREHOUSES_WORKSHEET = "Warehouses"
REQUISITIONS_WORKSHEET = "Requisitions"
TRANSACTIONS_WORKSHEET = "Transactions"
TRANSACTION_DETAILS_WORKSHEET = "Transaction_Details"


def _load_db_connector() -> Any:
    """Load db_connector when an operation needs Google Sheets access."""
    try:
        from scripts import db_connector
    except ModuleNotFoundError:
        import sys

        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from scripts import db_connector

    return db_connector


def _read_worksheet(worksheet_name: str) -> pd.DataFrame:
    """Read a worksheet through db_connector."""
    db_connector = _load_db_connector()
    return db_connector.read_worksheet(SPREADSHEET_NAME, worksheet_name)


def _append_row(worksheet_name: str, row: list[Any]) -> None:
    """Append a row to a worksheet through db_connector."""
    db_connector = _load_db_connector()
    db_connector.append_row(SPREADSHEET_NAME, worksheet_name, row)


def _worksheet_headers(worksheet_name: str) -> list[str]:
    """Return first-row worksheet headers through db_connector."""
    db_connector = _load_db_connector()
    worksheet = db_connector.connect_to_sheet(SPREADSHEET_NAME).worksheet(worksheet_name)
    return worksheet.row_values(1)


def _append_dict_row(worksheet_name: str, values: dict[str, Any]) -> None:
    """Append a dictionary row using the worksheet header order."""
    headers = _worksheet_headers(worksheet_name)
    if not headers:
        raise ValueError(f"{worksheet_name} worksheet must have a header row.")

    row = [values.get(header, "") for header in headers]
    _append_row(worksheet_name, row)


def _normalize_column_name(column_name: str) -> str:
    """Normalize a column name for flexible matching."""
    return str(column_name).strip().lower().replace(" ", "_")


def _find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    required: bool = True,
) -> str | None:
    """Find a dataframe column using one or more possible names."""
    normalized_columns = {
        _normalize_column_name(column): column for column in dataframe.columns
    }

    for candidate in candidates:
        normalized_candidate = _normalize_column_name(candidate)
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    if required:
        raise ValueError(f"Missing required column. Expected one of: {', '.join(candidates)}")

    return None


def _now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _current_year() -> str:
    """Return the current year used in generated IDs."""
    return datetime.now(timezone.utc).strftime("%Y")


def _next_id(worksheet_name: str, id_column_candidates: list[str], prefix: str) -> str:
    """Generate the next sequential ID for the current year."""
    year = _current_year()
    dataframe = _read_worksheet(worksheet_name)

    if dataframe.empty:
        return f"{prefix}-{year}-000001"

    id_column = _find_column(dataframe, id_column_candidates, required=False)
    if not id_column:
        return f"{prefix}-{year}-000001"

    pattern = re.compile(rf"^{re.escape(prefix)}-{year}-(\d+)$")
    highest_number = 0

    for value in dataframe[id_column].fillna("").astype(str):
        match = pattern.match(value.strip())
        if match:
            highest_number = max(highest_number, int(match.group(1)))

    return f"{prefix}-{year}-{highest_number + 1:06d}"


def _next_detail_ids(count: int) -> list[str]:
    """Generate the next detail IDs for a multi-item transaction."""
    first_id = _next_id(TRANSACTION_DETAILS_WORKSHEET, ["Detail_ID", "Detail ID"], "TD")
    prefix, year, number = first_id.split("-")
    start_number = int(number)
    return [f"{prefix}-{year}-{start_number + index:06d}" for index in range(count)]


def _clean_line_items(line_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize transaction detail rows."""
    cleaned_items = []

    for index, line_item in enumerate(line_items, start=1):
        item_id = str(line_item.get("Item_ID") or line_item.get("item_id") or "").strip()
        condition = str(line_item.get("Condition") or line_item.get("condition") or "Good").strip()

        try:
            quantity = int(line_item.get("Quantity") or line_item.get("quantity") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Line {index}: quantity must be a number.") from exc

        if not item_id:
            raise ValueError(f"Line {index}: Item_ID is required.")
        if quantity <= 0:
            raise ValueError(f"Line {index}: quantity must be greater than zero.")

        cleaned_items.append(
            {
                "Item_ID": item_id,
                "Quantity": quantity,
                "Condition": condition or "Good",
            }
        )

    if not cleaned_items:
        raise ValueError("At least one item row is required.")

    return cleaned_items


def get_items() -> list[dict[str, Any]]:
    """Return item records for form dropdowns."""
    return _read_worksheet(ITEMS_WORKSHEET).to_dict(orient="records")


def get_schools() -> list[dict[str, Any]]:
    """Return school records for form dropdowns."""
    return _read_worksheet(SCHOOLS_WORKSHEET).to_dict(orient="records")


def get_warehouses() -> list[dict[str, Any]]:
    """Return warehouse records for form dropdowns."""
    return _read_worksheet(WAREHOUSES_WORKSHEET).to_dict(orient="records")


def get_available_stock(item_id: str) -> int:
    """Calculate available stock for an item from normalized transactions."""
    transactions = _read_worksheet(TRANSACTIONS_WORKSHEET)
    details = _read_worksheet(TRANSACTION_DETAILS_WORKSHEET)

    if transactions.empty or details.empty:
        return 0

    transaction_id_column = _find_column(transactions, ["Transaction_ID", "Transaction ID"])
    transaction_type_column = _find_column(
        transactions, ["Transaction_Type", "Transaction Type", "Type"]
    )
    detail_transaction_id_column = _find_column(details, ["Transaction_ID", "Transaction ID"])
    item_id_column = _find_column(details, ["Item_ID", "Item ID"])
    quantity_column = _find_column(details, ["Quantity", "Qty"])

    merged = details.merge(
        transactions[[transaction_id_column, transaction_type_column]],
        how="left",
        left_on=detail_transaction_id_column,
        right_on=transaction_id_column,
    )

    item_movements = merged[
        merged[item_id_column].fillna("").astype(str).str.strip() == str(item_id).strip()
    ].copy()

    if item_movements.empty:
        return 0

    item_movements[quantity_column] = pd.to_numeric(
        item_movements[quantity_column], errors="coerce"
    ).fillna(0)
    movement_types = item_movements[transaction_type_column].fillna("").astype(str).str.upper()

    signed_quantity = pd.Series(0, index=item_movements.index, dtype="float64")
    signed_quantity.loc[movement_types == "IN"] = item_movements.loc[
        movement_types == "IN", quantity_column
    ].abs()
    signed_quantity.loc[movement_types == "OUT"] = -item_movements.loc[
        movement_types == "OUT", quantity_column
    ].abs()
    signed_quantity.loc[movement_types == "ADJUSTMENT"] = item_movements.loc[
        movement_types == "ADJUSTMENT", quantity_column
    ]

    return int(signed_quantity.sum())


def _validate_out_stock(line_items: list[dict[str, Any]]) -> None:
    """Reject OUT transactions when requested quantities exceed available stock."""
    errors = []
    requested_by_item: dict[str, int] = {}

    for line_item in line_items:
        item_id = line_item["Item_ID"]
        requested_by_item[item_id] = requested_by_item.get(item_id, 0) + line_item["Quantity"]

    for item_id, requested_quantity in requested_by_item.items():
        available_quantity = get_available_stock(item_id)

        if available_quantity < requested_quantity:
            errors.append(
                f"{item_id}: requested {requested_quantity}, available {available_quantity}"
            )

    if errors:
        raise ValueError("Insufficient stock for: " + "; ".join(errors))


def _submit_transaction(
    transaction_type: str,
    payload: dict[str, Any],
    validate_stock: bool = False,
) -> dict[str, Any]:
    """Save a transaction header and its line items."""
    line_items = _clean_line_items(payload.get("items", []))

    if validate_stock:
        _validate_out_stock(line_items)

    transaction_id = _next_id(TRANSACTIONS_WORKSHEET, ["Transaction_ID", "Transaction ID"], "TXN")
    transaction_date = payload.get("Transaction_Date") or payload.get("transaction_date") or _now_iso()
    warehouse_id = payload.get("Warehouse_ID") or payload.get("warehouse_id") or ""
    school_id = (
        payload.get("Destination_School_ID")
        or payload.get("destination_school_id")
        or payload.get("School_ID")
        or payload.get("school_id")
        or ""
    )

    header = {
        "Transaction_ID": transaction_id,
        "Transaction_Date": transaction_date,
        "Transaction_Type": transaction_type,
        "Warehouse_ID": warehouse_id,
        "Destination_School_ID": school_id,
        "Source": payload.get("Source") or payload.get("source") or "",
        "Status": payload.get("Status") or payload.get("status") or "Completed",
        "Remarks": payload.get("Remarks") or payload.get("remarks") or "",
    }

    logging.info("Submitting %s transaction %s", transaction_type, transaction_id)
    _append_dict_row(TRANSACTIONS_WORKSHEET, header)

    detail_ids = _next_detail_ids(len(line_items))
    for detail_id, line_item in zip(detail_ids, line_items):
        _append_dict_row(
            TRANSACTION_DETAILS_WORKSHEET,
            {
                "Detail_ID": detail_id,
                "Transaction_ID": transaction_id,
                "Item_ID": line_item["Item_ID"],
                "Quantity": line_item["Quantity"],
                "Condition": line_item["Condition"],
            },
        )

    return {
        "transaction_id": transaction_id,
        "detail_ids": detail_ids,
        "line_items": len(line_items),
        "status": "success",
    }


def submit_receive_stock(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit an IN transaction with one or more item rows."""
    try:
        return _submit_transaction("IN", payload)
    except Exception as exc:
        logging.exception("Failed to submit receive stock transaction: %s", exc)
        raise


def submit_issue_stock(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit an OUT transaction after stock validation."""
    try:
        return _submit_transaction("OUT", payload, validate_stock=True)
    except Exception as exc:
        logging.exception("Failed to submit issue stock transaction: %s", exc)
        raise


def submit_requisition(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit a requisition and store requested line items."""
    try:
        line_items = _clean_line_items(payload.get("items", []))
        requisition_id = _next_id(
            REQUISITIONS_WORKSHEET,
            ["Requisition_ID", "Requisition ID"],
            "REQ",
        )

        base_values = {
            "Requisition_ID": requisition_id,
            "Requisition_Date": payload.get("Requisition_Date")
            or payload.get("requisition_date")
            or _now_iso(),
            "School_ID": payload.get("School_ID") or payload.get("school_id") or "",
            "Status": payload.get("Status") or payload.get("status") or "Pending",
            "Remarks": payload.get("Remarks") or payload.get("remarks") or "",
        }

        logging.info("Submitting requisition %s", requisition_id)
        for line_item in line_items:
            _append_dict_row(
                REQUISITIONS_WORKSHEET,
                {
                    **base_values,
                    "Item_ID": line_item["Item_ID"],
                    "Quantity": line_item["Quantity"],
                    "Condition": line_item["Condition"],
                },
            )

        return {
            "requisition_id": requisition_id,
            "line_items": len(line_items),
            "status": "success",
        }
    except Exception as exc:
        logging.exception("Failed to submit requisition: %s", exc)
        raise
