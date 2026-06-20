"""Shared inventory calculations."""

from typing import Callable

import pandas as pd

try:
    from scripts import db_connector
except (ImportError, ModuleNotFoundError):
    import db_connector


SPREADSHEET_NAME = "Educational_Supplies_Logs"
TRANSACTIONS_WORKSHEET = "Transactions"
TRANSACTION_DETAILS_WORKSHEET = "Transaction_Details"


def _read_worksheet(sheet_name: str, worksheet_name: str) -> pd.DataFrame:
    return db_connector.read_worksheet(sheet_name, worksheet_name)


def _find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    required: bool = True,
) -> str | None:
    return db_connector.find_column(dataframe, candidates, required=required)


def calculate_available_stock(
    item_id: str,
    transactions: pd.DataFrame | None = None,
    transaction_details: pd.DataFrame | None = None,
    read_worksheet: Callable[[str, str], pd.DataFrame] | None = None,
    sheet_name: str = SPREADSHEET_NAME,
) -> int:
    """Calculate available stock for an item as total IN quantity minus total OUT quantity."""
    reader = read_worksheet or _read_worksheet
    transactions = (
        transactions
        if transactions is not None
        else reader(sheet_name, TRANSACTIONS_WORKSHEET)
    )
    transaction_details = (
        transaction_details
        if transaction_details is not None
        else reader(sheet_name, TRANSACTION_DETAILS_WORKSHEET)
    )

    if transactions.empty or transaction_details.empty:
        return 0

    transaction_id_column = _find_column(transactions, ["Transaction_ID", "Transaction ID"])
    transaction_type_column = _find_column(
        transactions, ["Transaction_Type", "Transaction Type", "Type"]
    )
    detail_transaction_id_column = _find_column(
        transaction_details, ["Transaction_ID", "Transaction ID"]
    )
    item_id_column = _find_column(transaction_details, ["Item_ID", "Item ID"])
    quantity_column = _find_column(transaction_details, ["Quantity", "Qty"])

    merged = transaction_details.merge(
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

    quantities = pd.to_numeric(item_movements[quantity_column], errors="coerce").fillna(0).abs()
    movement_types = item_movements[transaction_type_column].fillna("").astype(str).str.upper()

    total_in = quantities.loc[movement_types == "IN"].sum()
    total_out = quantities.loc[movement_types == "OUT"].sum()

    return int(total_in - total_out)
