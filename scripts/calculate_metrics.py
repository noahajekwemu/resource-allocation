import json
import logging
import math
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SPREADSHEET_NAME = "Educational_Supplies_Logs"
WORKSHEETS = {
    "transactions": "Transactions",
    "transaction_details": "Transaction_Details",
    "items": "Items",
    "schools": "Schools",
    "warehouses": "Warehouses",
    "requisitions": "Requisitions",
    "requisition_details": "Requisition_Details",
}
OUTPUT_PATH = Path("dashboard") / "data.json"


def normalize_column_name(column_name: str) -> str:
    return str(column_name).strip().lower().replace(" ", "_")


def find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    required: bool = False,
) -> str | None:
    normalized = {normalize_column_name(column): column for column in dataframe.columns}
    for candidate in candidates:
        if normalize_column_name(candidate) in normalized:
            return normalized[normalize_column_name(candidate)]
    if required:
        logging.warning("Missing required column. Expected one of: %s", candidates)
    return None


def read_worksheet_data(worksheet_name: str) -> pd.DataFrame:
    try:
        from scripts.db_connector import read_worksheet
    except ModuleNotFoundError as exc:
        if exc.name not in {"scripts", "scripts.db_connector"}:
            raise
        import sys

        project_root = Path(__file__).resolve().parents[1]
        scripts_dir = Path(__file__).resolve().parent
        for path in (str(project_root), str(scripts_dir)):
            if path not in sys.path:
                sys.path.insert(0, path)
        try:
            from scripts.db_connector import read_worksheet
        except ModuleNotFoundError as fallback_exc:
            if fallback_exc.name not in {"scripts", "scripts.db_connector"}:
                raise
            from db_connector import read_worksheet

    logging.info("Reading %s / %s", SPREADSHEET_NAME, worksheet_name)
    return read_worksheet(SPREADSHEET_NAME, worksheet_name)


def read_all_data() -> dict[str, pd.DataFrame]:
    return {key: read_worksheet_data(name) for key, name in WORKSHEETS.items()}


def clean_id_series(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def safe_text_column(dataframe: pd.DataFrame, column: str | None) -> pd.Series:
    if column and column in dataframe.columns:
        return dataframe[column].fillna("").astype(str).str.strip()
    return pd.Series([""] * len(dataframe), index=dataframe.index, dtype="object")


def safe_numeric_column(dataframe: pd.DataFrame, column: str | None) -> pd.Series:
    if column and column in dataframe.columns:
        return pd.to_numeric(dataframe[column], errors="coerce").fillna(0)
    return pd.Series([0] * len(dataframe), index=dataframe.index, dtype="float64")


def prepare_items(items: pd.DataFrame) -> pd.DataFrame:
    columns = ["Item_ID", "Item_Name", "Category", "Minimum_Stock"]
    if items.empty:
        return pd.DataFrame(columns=columns)
    item_id = find_column(items, ["Item_ID", "Item ID"], required=True)
    prepared = pd.DataFrame(index=items.index)
    prepared["Item_ID"] = clean_id_series(items[item_id]) if item_id else ""
    prepared["Item_Name"] = safe_text_column(
        items, find_column(items, ["Item_Name", "Item Name", "Item"])
    )
    prepared["Category"] = safe_text_column(
        items, find_column(items, ["Category", "Item_Category", "Item Category"])
    )
    minimum_stock_column = find_column(
        items, ["Minimum_Stock", "Minimum Stock", "Reorder_Level", "Reorder Level"]
    )
    prepared["Minimum_Stock"] = safe_numeric_column(items, minimum_stock_column)
    if minimum_stock_column:
        raw_minimum_stock = safe_text_column(items, minimum_stock_column)
        prepared["Minimum_Stock"] = prepared["Minimum_Stock"].where(
            raw_minimum_stock != "", 10
        )
    else:
        prepared["Minimum_Stock"] = 10
    prepared["Item_Name"] = prepared["Item_Name"].where(
        prepared["Item_Name"] != "", prepared["Item_ID"]
    )
    prepared["Category"] = prepared["Category"].where(
        prepared["Category"] != "", "Uncategorized"
    )
    prepared["Minimum_Stock"] = prepared["Minimum_Stock"].round().astype(int)
    return prepared[prepared["Item_ID"] != ""].drop_duplicates("Item_ID", keep="last")


def prepare_schools(schools: pd.DataFrame) -> pd.DataFrame:
    columns = ["School_ID", "School_Name", "LGA", "School_Type"]
    if schools.empty:
        return pd.DataFrame(columns=columns)
    school_id = find_column(schools, ["School_ID", "School ID"], required=True)
    prepared = pd.DataFrame(index=schools.index)
    prepared["School_ID"] = clean_id_series(schools[school_id]) if school_id else ""
    prepared["School_Name"] = safe_text_column(
        schools, find_column(schools, ["School_Name", "School Name", "School"])
    )
    prepared["LGA"] = safe_text_column(
        schools, find_column(schools, ["LGA", "Local_Government", "Local Government"])
    )
    prepared["School_Type"] = safe_text_column(
        schools, find_column(schools, ["School_Type", "School Type", "Type"])
    )
    prepared["School_Name"] = prepared["School_Name"].where(
        prepared["School_Name"] != "", prepared["School_ID"]
    )
    prepared["LGA"] = prepared["LGA"].where(prepared["LGA"] != "", "Unknown")
    prepared["School_Type"] = prepared["School_Type"].where(
        prepared["School_Type"] != "", "Unknown"
    )
    return prepared[prepared["School_ID"] != ""].drop_duplicates("School_ID", keep="last")


def prepare_warehouses(warehouses: pd.DataFrame) -> pd.DataFrame:
    columns = ["Warehouse_ID", "Warehouse_Name"]
    if warehouses.empty:
        return pd.DataFrame(columns=columns)
    warehouse_id = find_column(warehouses, ["Warehouse_ID", "Warehouse ID"], required=True)
    prepared = pd.DataFrame(index=warehouses.index)
    prepared["Warehouse_ID"] = clean_id_series(warehouses[warehouse_id]) if warehouse_id else ""
    prepared["Warehouse_Name"] = safe_text_column(
        warehouses,
        find_column(warehouses, ["Warehouse_Name", "Warehouse Name", "Warehouse"]),
    )
    prepared["Warehouse_Name"] = prepared["Warehouse_Name"].where(
        prepared["Warehouse_Name"] != "", prepared["Warehouse_ID"]
    )
    return prepared[prepared["Warehouse_ID"] != ""].drop_duplicates(
        "Warehouse_ID", keep="last"
    )


def prepare_requisitions(requisitions: pd.DataFrame) -> pd.DataFrame:
    columns = ["Requisition_ID", "School_ID", "Request_Date", "Status"]
    if requisitions.empty:
        return pd.DataFrame(columns=columns)
    requisition_id = find_column(
        requisitions, ["Requisition_ID", "Requisition ID"], required=True
    )
    prepared = pd.DataFrame(index=requisitions.index)
    prepared["Requisition_ID"] = (
        clean_id_series(requisitions[requisition_id]) if requisition_id else ""
    )
    prepared["School_ID"] = safe_text_column(
        requisitions, find_column(requisitions, ["School_ID", "School ID"])
    )
    prepared["Request_Date"] = safe_text_column(
        requisitions, find_column(requisitions, ["Request_Date", "Request Date"])
    )
    prepared["Status"] = safe_text_column(
        requisitions, find_column(requisitions, ["Status", "Requisition_Status"])
    )
    return prepared[prepared["Requisition_ID"] != ""].drop_duplicates(
        "Requisition_ID", keep="last"
    )


def prepare_requisition_details(details: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Req_Detail_ID",
        "Requisition_ID",
        "Item_ID",
        "Quantity_Requested",
        "Quantity_Approved",
        "Quantity_Fulfilled",
    ]
    if details.empty:
        return pd.DataFrame(columns=columns)
    prepared = pd.DataFrame(index=details.index)
    for output, candidates in {
        "Req_Detail_ID": ["Req_Detail_ID", "Req Detail ID", "Detail_ID"],
        "Requisition_ID": ["Requisition_ID", "Requisition ID"],
        "Item_ID": ["Item_ID", "Item ID"],
    }.items():
        prepared[output] = safe_text_column(details, find_column(details, candidates))
    for output, candidates in {
        "Quantity_Requested": ["Quantity_Requested", "Requested Quantity"],
        "Quantity_Approved": ["Quantity_Approved", "Approved Quantity"],
        "Quantity_Fulfilled": ["Quantity_Fulfilled", "Fulfilled Quantity"],
    }.items():
        prepared[output] = safe_numeric_column(details, find_column(details, candidates))
    return prepared[
        (prepared["Requisition_ID"] != "") & (prepared["Item_ID"] != "")
    ]


def prepare_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Transaction_ID",
        "Transaction_Date",
        "Transaction_Type",
        "Warehouse_ID",
        "Destination_School_ID",
        "Requisition_ID",
        "Source",
        "Status",
        "Remarks",
    ]
    if transactions.empty:
        return pd.DataFrame(columns=columns)
    transaction_id = find_column(
        transactions, ["Transaction_ID", "Transaction ID"], required=True
    )
    prepared = pd.DataFrame(index=transactions.index)
    prepared["Transaction_ID"] = (
        clean_id_series(transactions[transaction_id]) if transaction_id else ""
    )
    mappings = {
        "Transaction_Date": ["Transaction_Date", "Transaction Date", "Date"],
        "Transaction_Type": ["Transaction_Type", "Transaction Type", "Type"],
        "Warehouse_ID": ["Warehouse_ID", "Warehouse ID"],
        "Destination_School_ID": [
            "Destination_School_ID",
            "Destination School ID",
            "School_ID",
            "School ID",
        ],
        "Requisition_ID": ["Requisition_ID", "Requisition ID"],
        "Source": ["Source"],
        "Status": ["Status"],
        "Remarks": ["Remarks", "Notes"],
    }
    for output, candidates in mappings.items():
        prepared[output] = safe_text_column(transactions, find_column(transactions, candidates))
    prepared["Transaction_Type"] = prepared["Transaction_Type"].str.upper()
    return prepared[prepared["Transaction_ID"] != ""]


def prepare_transaction_details(details: pd.DataFrame) -> pd.DataFrame:
    columns = ["Detail_ID", "Transaction_ID", "Item_ID", "Quantity", "Condition"]
    if details.empty:
        return pd.DataFrame(columns=columns)
    prepared = pd.DataFrame(index=details.index)
    prepared["Detail_ID"] = safe_text_column(
        details, find_column(details, ["Detail_ID", "Detail ID"])
    )
    prepared["Transaction_ID"] = safe_text_column(
        details, find_column(details, ["Transaction_ID", "Transaction ID"], required=True)
    )
    prepared["Item_ID"] = safe_text_column(
        details, find_column(details, ["Item_ID", "Item ID"], required=True)
    )
    prepared["Quantity"] = safe_numeric_column(
        details, find_column(details, ["Quantity", "Qty"], required=True)
    )
    prepared["Condition"] = safe_text_column(
        details, find_column(details, ["Condition"])
    ).str.upper()
    return prepared[
        (prepared["Transaction_ID"] != "") & (prepared["Item_ID"] != "")
    ]


def prepare_legacy_flat_transaction_details(
    transactions: pd.DataFrame,
    existing_details: pd.DataFrame,
) -> pd.DataFrame:
    """Build fallback details from old flat Transactions rows without details."""
    columns = ["Detail_ID", "Transaction_ID", "Item_ID", "Quantity", "Condition"]
    if transactions.empty:
        return pd.DataFrame(columns=columns)

    item_id_column = find_column(transactions, ["Item_ID", "Item ID"], required=False)
    quantity_column = find_column(transactions, ["Quantity", "Qty"], required=False)
    transaction_id_column = find_column(
        transactions, ["Transaction_ID", "Transaction ID"], required=False
    )
    if not item_id_column or not quantity_column or not transaction_id_column:
        return pd.DataFrame(columns=columns)

    detail_transaction_ids = (
        set(existing_details["Transaction_ID"].fillna("").astype(str).str.strip())
        if not existing_details.empty and "Transaction_ID" in existing_details
        else set()
    )
    prepared = pd.DataFrame(index=transactions.index)
    prepared["Transaction_ID"] = clean_id_series(transactions[transaction_id_column])
    prepared["Item_ID"] = safe_text_column(transactions, item_id_column)
    prepared["Quantity"] = safe_numeric_column(transactions, quantity_column)
    prepared["Condition"] = safe_text_column(
        transactions, find_column(transactions, ["Condition"], required=False)
    ).str.upper()
    prepared["Detail_ID"] = prepared["Transaction_ID"].map(lambda value: f"{value}-FLAT")
    prepared = prepared[
        (prepared["Transaction_ID"] != "")
        & (prepared["Item_ID"] != "")
        & ~prepared["Transaction_ID"].isin(detail_transaction_ids)
    ]
    return prepared[columns]


def build_movements(transactions: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    if transactions.empty or details.empty:
        movements = details.merge(transactions, how="left", on="Transaction_ID")
        movements["Signed_Quantity"] = pd.Series(
            [0.0] * len(movements), index=movements.index, dtype="float64"
        )
        return movements
    movements = details.merge(transactions, how="left", on="Transaction_ID")
    movement_type = movements["Transaction_Type"].fillna("").str.upper()
    quantity = pd.to_numeric(movements["Quantity"], errors="coerce").fillna(0)
    movements["Signed_Quantity"] = 0.0
    movements.loc[movement_type.eq("IN"), "Signed_Quantity"] = quantity.abs()
    movements.loc[movement_type.eq("OUT"), "Signed_Quantity"] = -quantity.abs()
    movements.loc[movement_type.eq("ADJUSTMENT"), "Signed_Quantity"] = quantity
    return movements


def build_stock_balances(items: pd.DataFrame, movements: pd.DataFrame) -> pd.DataFrame:
    stock = items[["Item_ID", "Item_Name", "Category", "Minimum_Stock"]].copy()
    balances = (
        movements.groupby("Item_ID")["Signed_Quantity"].sum().rename("Current_Stock")
        if not movements.empty
        else pd.Series(dtype="float64", name="Current_Stock")
    )
    stock = stock.merge(balances, how="left", on="Item_ID")
    stock["Current_Stock"] = stock["Current_Stock"].fillna(0).round().astype(int)
    return stock


def enrich_movements(
    movements: pd.DataFrame,
    items: pd.DataFrame,
    schools: pd.DataFrame,
    warehouses: pd.DataFrame,
) -> pd.DataFrame:
    enriched = movements.merge(
        items[["Item_ID", "Item_Name", "Category"]], how="left", on="Item_ID"
    )
    enriched = enriched.merge(
        schools, how="left", left_on="Destination_School_ID", right_on="School_ID"
    )
    enriched = enriched.merge(warehouses, how="left", on="Warehouse_ID")
    defaults = {
        "Item_Name": enriched.get("Item_ID", ""),
        "Category": "Uncategorized",
        "School_Name": enriched.get("Destination_School_ID", ""),
        "LGA": "Unknown",
        "School_Type": "Unknown",
        "Warehouse_Name": enriched.get("Warehouse_ID", ""),
    }
    for column, default in defaults.items():
        if column not in enriched:
            enriched[column] = default
        else:
            enriched[column] = enriched[column].fillna(default)
    return enriched


def calculate_inventory_accuracy(total_items: int, negative_stock_items: int) -> float:
    if total_items == 0:
        return 100.0
    return round(((total_items - negative_stock_items) / total_items) * 100, 2)


def calculate_fulfillment_rate(requisition_details: pd.DataFrame) -> float:
    if requisition_details.empty:
        return 0.0
    approved = float(requisition_details["Quantity_Approved"].clip(lower=0).sum())
    if approved <= 0:
        return 0.0
    fulfilled = float(requisition_details["Quantity_Fulfilled"].clip(lower=0).sum())
    return round(min(fulfilled, approved) / approved * 100, 2)


def calculate_average_fulfillment_days(
    requisitions: pd.DataFrame, transactions: pd.DataFrame
) -> float:
    fulfilled = requisitions[requisitions["Status"].str.upper().eq("FULFILLED")].copy()
    if fulfilled.empty or transactions.empty:
        return 0.0
    outflows = transactions[transactions["Transaction_Type"].eq("OUT")].copy()
    outflows["Fulfilled_Date"] = pd.to_datetime(
        outflows["Transaction_Date"], errors="coerce", utc=True
    )
    completion_dates = outflows.groupby("Requisition_ID")["Fulfilled_Date"].max()
    fulfilled["Request_Date_Parsed"] = pd.to_datetime(
        fulfilled["Request_Date"], errors="coerce", utc=True
    )
    fulfilled = fulfilled.join(completion_dates, on="Requisition_ID")
    days = (fulfilled["Fulfilled_Date"] - fulfilled["Request_Date_Parsed"]).dt.total_seconds()
    days = (days / 86400).dropna().clip(lower=0)
    return round(float(days.mean()), 2) if not days.empty else 0.0


def status_count(requisitions: pd.DataFrame, status: str) -> int:
    return int(requisitions["Status"].str.upper().eq(status.upper()).sum())


def build_kpis(
    stock: pd.DataFrame,
    movements: pd.DataFrame,
    schools: pd.DataFrame,
    warehouses: pd.DataFrame,
    requisitions: pd.DataFrame,
    requisition_details: pd.DataFrame,
    transactions: pd.DataFrame,
) -> dict[str, Any]:
    total_items = int(len(stock))
    total_stock_units = int(stock["Current_Stock"].sum())
    negative_stock_items = int(stock["Current_Stock"].lt(0).sum())
    outflows = movements[movements["Transaction_Type"].eq("OUT")]
    kpis = {
        "inventory_accuracy": calculate_inventory_accuracy(total_items, negative_stock_items),
        "total_items": total_items,
        "total_stock_units": total_stock_units,
        "low_stock_items": int(stock["Current_Stock"].le(stock["Minimum_Stock"]).sum()),
        "total_requisitions": int(len(requisitions)),
        "pending_requisitions": status_count(requisitions, "Pending"),
        "approved_requisitions": status_count(requisitions, "Approved"),
        "fulfilled_requisitions": status_count(requisitions, "Fulfilled"),
        "rejected_requisitions": status_count(requisitions, "Rejected"),
        "fulfillment_rate": calculate_fulfillment_rate(requisition_details),
        "partially_fulfilled_requisitions": status_count(
            requisitions, "Partially Fulfilled"
        ),
        "average_fulfillment_days": calculate_average_fulfillment_days(
            requisitions, transactions
        ),
    }
    kpis.update(
        {
            "total_inventory_items": total_items,
            "total_available_stock": max(total_stock_units, 0),
            "out_of_stock_items": int(stock["Current_Stock"].le(0).sum()),
            "damaged_items": int(movements["Condition"].eq("DAMAGED").sum()),
            "schools_served": int(
                outflows["Destination_School_ID"].replace("", pd.NA).dropna().nunique()
            ),
            "total_warehouses": int(len(warehouses)),
            "total_schools": int(len(schools)),
            "total_categories": int(stock["Category"].nunique()),
        }
    )
    return kpis


def quantity_records(
    dataframe: pd.DataFrame,
    group_column: str,
    quantity_column: str,
    label_key: str,
    limit: int | None = None,
    ascending: bool = False,
) -> list[dict[str, Any]]:
    if dataframe.empty or group_column not in dataframe:
        return []
    grouped = (
        dataframe.groupby(group_column, dropna=False)[quantity_column]
        .sum()
        .reset_index()
        .sort_values([quantity_column, group_column], ascending=[ascending, True])
    )
    if limit is not None:
        grouped = grouped.head(limit)
    return [
        {label_key: str(row[group_column]), "quantity": int(row[quantity_column])}
        for _, row in grouped.iterrows()
    ]


def build_school_distribution(outflows: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    all_schools = quantity_records(outflows, "School_Name", "Out_Quantity", "school")
    return {
        "all_schools": all_schools,
        "top_10_schools": all_schools[:10],
        "bottom_10_schools": sorted(
            all_schools, key=lambda row: (row["quantity"], row["school"])
        )[:10],
    }


def build_warehouse_analytics(
    enriched: pd.DataFrame, warehouses: pd.DataFrame
) -> dict[str, list[dict[str, Any]]]:
    rows = []
    for _, warehouse in warehouses.iterrows():
        warehouse_rows = enriched[enriched["Warehouse_ID"].eq(warehouse["Warehouse_ID"])]
        rows.append(
            {
                "warehouse_id": warehouse["Warehouse_ID"],
                "warehouse": warehouse["Warehouse_Name"],
                "stock_level": int(warehouse_rows["Signed_Quantity"].sum()),
                "total_outflows": int(
                    warehouse_rows.loc[
                        warehouse_rows["Transaction_Type"].eq("OUT"), "Quantity"
                    ].abs().sum()
                ),
            }
        )
    return {
        "stock_levels": sorted(rows, key=lambda row: (-row["stock_level"], row["warehouse"])),
        "total_outflows": sorted(
            rows, key=lambda row: (-row["total_outflows"], row["warehouse"])
        ),
    }


def build_monthly_stock_movements(enriched: pd.DataFrame) -> list[dict[str, Any]]:
    if enriched.empty:
        return []
    monthly = enriched.copy()
    monthly["_date"] = pd.to_datetime(monthly["Transaction_Date"], errors="coerce", utc=True)
    monthly = monthly.dropna(subset=["_date"])
    monthly["month"] = monthly["_date"].dt.strftime("%Y-%m")
    monthly["in_quantity"] = monthly["Quantity"].abs().where(
        monthly["Transaction_Type"].eq("IN"), 0
    )
    monthly["out_quantity"] = monthly["Quantity"].abs().where(
        monthly["Transaction_Type"].eq("OUT"), 0
    )
    grouped = monthly.groupby("month")[["in_quantity", "out_quantity"]].sum().reset_index()
    return [
        {
            "month": row["month"],
            "in_quantity": int(row["in_quantity"]),
            "out_quantity": int(row["out_quantity"]),
        }
        for _, row in grouped.sort_values("month").iterrows()
    ]


def build_stock_levels_table(stock: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {
            "Item_ID": row["Item_ID"],
            "Item_Name": row["Item_Name"],
            "Category": row["Category"],
            "Current_Stock": int(row["Current_Stock"]),
            "Reorder_Level": int(row["Reorder_Level"]),
            "Minimum_Stock": int(row["Minimum_Stock"]),
        }
        for _, row in stock.assign(Reorder_Level=stock["Minimum_Stock"])
        .sort_values(["Category", "Item_Name"])
        .iterrows()
    ]


def build_recent_movements_table(enriched: pd.DataFrame, limit: int = 50) -> list[dict[str, Any]]:
    if enriched.empty:
        return []
    rows = enriched.copy()
    rows["_date"] = pd.to_datetime(rows["Transaction_Date"], errors="coerce", utc=True)
    summaries = (
        rows.groupby(
            [
                "Transaction_ID",
                "Transaction_Date",
                "Transaction_Type",
                "School_Name",
                "Warehouse_Name",
            ],
            dropna=False,
        )["Quantity"]
        .sum()
        .reset_index(name="Total_Items")
    )
    dates = rows.groupby("Transaction_ID")["_date"].max()
    summaries = summaries.join(dates, on="Transaction_ID").sort_values(
        "_date", ascending=False, na_position="last"
    ).head(limit)
    return [
        {
            "Transaction_ID": row["Transaction_ID"],
            "Transaction_Date": row["Transaction_Date"],
            "Transaction_Type": row["Transaction_Type"],
            "School_Name": row["School_Name"],
            "Warehouse_Name": row["Warehouse_Name"],
            "Total_Items": int(row["Total_Items"]),
        }
        for _, row in summaries.iterrows()
    ]


def build_requisition_analytics(
    requisitions: pd.DataFrame,
    details: pd.DataFrame,
    items: pd.DataFrame,
    schools: pd.DataFrame,
) -> dict[str, list[dict[str, Any]]]:
    status_rows = (
        requisitions.groupby("Status").size().reset_index(name="quantity")
        if not requisitions.empty else pd.DataFrame(columns=["Status", "quantity"])
    )
    status_distribution = [
        {"status": str(row["Status"]), "quantity": int(row["quantity"])}
        for _, row in status_rows.sort_values("Status").iterrows()
    ]

    detail_items = details.merge(
        items[["Item_ID", "Item_Name"]], on="Item_ID", how="left"
    )
    detail_items["Item_Name"] = detail_items["Item_Name"].fillna(
        detail_items["Item_ID"]
    )
    by_item = (
        detail_items.groupby("Item_Name")[[
            "Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"
        ]].sum().reset_index()
        if not detail_items.empty
        else pd.DataFrame(columns=[
            "Item_Name", "Quantity_Requested", "Quantity_Approved",
            "Quantity_Fulfilled",
        ])
    )
    by_item = by_item.sort_values(
        ["Quantity_Requested", "Item_Name"], ascending=[False, True]
    )
    requested_comparison = [
        {
            "item": row["Item_Name"],
            "requested": int(row["Quantity_Requested"]),
            "approved": int(row["Quantity_Approved"]),
            "fulfilled": int(row["Quantity_Fulfilled"]),
        }
        for _, row in by_item.iterrows()
    ]
    top_requested = [
        {"item": row["Item_Name"], "quantity": int(row["Quantity_Requested"])}
        for _, row in by_item.head(10).iterrows()
    ]

    totals = (
        details.groupby("Requisition_ID")[[
            "Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"
        ]].sum().reset_index()
        if not details.empty
        else pd.DataFrame(columns=[
            "Requisition_ID", "Quantity_Requested", "Quantity_Approved",
            "Quantity_Fulfilled",
        ])
    )
    requisition_rows = requisitions.merge(totals, on="Requisition_ID", how="left").merge(
        schools, on="School_ID", how="left"
    )
    for column in ("Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"):
        requisition_rows[column] = requisition_rows[column].fillna(0)

    requests_by_lga_frame = (
        requisition_rows.groupby("LGA")["Quantity_Requested"].sum().reset_index()
        if not requisition_rows.empty
        else pd.DataFrame(columns=["LGA", "Quantity_Requested"])
    )
    requests_by_lga = [
        {"lga": str(row["LGA"]), "quantity": int(row["Quantity_Requested"])}
        for _, row in requests_by_lga_frame.sort_values(
            ["Quantity_Requested", "LGA"], ascending=[False, True]
        ).iterrows()
    ]

    recent_frame = requisition_rows.copy()
    recent_frame["_date"] = pd.to_datetime(
        recent_frame["Request_Date"], errors="coerce", utc=True
    )
    recent_requisitions = [
        {
            "Requisition_ID": row["Requisition_ID"],
            "Request_Date": row["Request_Date"],
            "School_Name": row["School_Name"], "LGA": row["LGA"],
            "Status": row["Status"],
            "Requested_Quantity": int(row["Quantity_Requested"]),
            "Fulfilled_Quantity": int(row["Quantity_Fulfilled"]),
        }
        for _, row in recent_frame.sort_values(
            "_date", ascending=False, na_position="last"
        ).head(50).iterrows()
    ]

    fulfillment_frame = (
        requisition_rows.groupby(["School_Name", "LGA"], dropna=False)[[
            "Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"
        ]].sum().reset_index()
        if not requisition_rows.empty
        else pd.DataFrame(columns=[
            "School_Name", "LGA", "Quantity_Requested", "Quantity_Approved",
            "Quantity_Fulfilled",
        ])
    )
    fulfillment_summary = []
    for _, row in fulfillment_frame.iterrows():
        approved = float(row["Quantity_Approved"])
        fulfilled = float(row["Quantity_Fulfilled"])
        fulfillment_summary.append({
            "School_Name": row["School_Name"], "LGA": row["LGA"],
            "Requested_Quantity": int(row["Quantity_Requested"]),
            "Approved_Quantity": int(approved), "Fulfilled_Quantity": int(fulfilled),
            "Fulfillment_Rate": round(fulfilled / approved * 100, 2)
            if approved > 0 else 0.0,
        })

    return {
        "requisition_status_distribution": status_distribution,
        "requested_vs_approved_vs_fulfilled": requested_comparison,
        "top_requested_items": top_requested,
        "requests_by_lga": requests_by_lga,
        "recent_requisitions": recent_requisitions,
        "fulfillment_summary": fulfillment_summary,
    }


def build_dashboard_data(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    raw_transactions = data.get("transactions", pd.DataFrame())
    transactions = prepare_transactions(raw_transactions)
    transaction_details = prepare_transaction_details(
        data.get("transaction_details", pd.DataFrame())
    )
    legacy_details = prepare_legacy_flat_transaction_details(
        raw_transactions, transaction_details
    )
    if not legacy_details.empty:
        transaction_details = pd.concat(
            [transaction_details, legacy_details], ignore_index=True
        )
    items = prepare_items(data.get("items", pd.DataFrame()))
    schools = prepare_schools(data.get("schools", pd.DataFrame()))
    warehouses = prepare_warehouses(data.get("warehouses", pd.DataFrame()))
    requisitions = prepare_requisitions(data.get("requisitions", pd.DataFrame()))
    requisition_details = prepare_requisition_details(
        data.get("requisition_details", pd.DataFrame())
    )

    movements = build_movements(transactions, transaction_details)
    stock = build_stock_balances(items, movements)
    enriched = enrich_movements(movements, items, schools, warehouses)
    outflows = enriched[enriched["Transaction_Type"].eq("OUT")].copy()
    inflows = enriched[enriched["Transaction_Type"].eq("IN")].copy()
    outflows["Out_Quantity"] = outflows["Quantity"].abs()
    inflows["In_Quantity"] = inflows["Quantity"].abs()

    school_distribution = build_school_distribution(outflows)
    lga_distribution = quantity_records(outflows, "LGA", "Out_Quantity", "lga")
    warehouse_analytics = build_warehouse_analytics(enriched, warehouses)
    monthly_movements = build_monthly_stock_movements(enriched)
    requisition_analytics = build_requisition_analytics(
        requisitions, requisition_details, items, schools
    )

    charts = {
        "requisition_status_distribution": requisition_analytics[
            "requisition_status_distribution"
        ],
        "requested_vs_approved_vs_fulfilled": requisition_analytics[
            "requested_vs_approved_vs_fulfilled"
        ],
        "top_requested_items": requisition_analytics["top_requested_items"],
        "requests_by_lga": requisition_analytics["requests_by_lga"],
        "inventory_by_category": quantity_records(
            stock, "Category", "Current_Stock", "category"
        ),
        "distribution_by_lga": lga_distribution,
        "distribution_by_school_type": quantity_records(
            outflows, "School_Type", "Out_Quantity", "school_type"
        ),
        "top_distributed_items": quantity_records(
            outflows, "Item_Name", "Out_Quantity", "item", limit=10
        ),
        "top_schools": school_distribution["top_10_schools"],
        "bottom_schools": school_distribution["bottom_10_schools"],
        "stock_source_analysis": quantity_records(
            inflows, "Source", "In_Quantity", "source"
        ),
        "warehouse_stock_levels": warehouse_analytics["stock_levels"],
        "warehouse_outflows": warehouse_analytics["total_outflows"],
        "monthly_stock_movements": monthly_movements,
    }
    stock_levels = build_stock_levels_table(stock)
    low_stock = stock[stock["Current_Stock"].le(stock["Minimum_Stock"])]

    generated_at = datetime.now(timezone.utc).isoformat()
    kpis = build_kpis(
        stock,
        movements,
        schools,
        warehouses,
        requisitions,
        requisition_details,
        transactions,
    )
    return {
        "generated_at": generated_at,
        "last_updated": generated_at,
        "kpis": kpis,
        "inventory": {
            "total_items": kpis["total_items"],
            "total_stock_units": kpis["total_stock_units"],
            "low_stock_items": kpis["low_stock_items"],
            "out_of_stock_items": kpis["out_of_stock_items"],
        },
        "requisitions": {
            "total_requisitions": kpis["total_requisitions"],
            "pending_requisitions": kpis["pending_requisitions"],
            "approved_requisitions": kpis["approved_requisitions"],
            "fulfilled_requisitions": kpis["fulfilled_requisitions"],
            "rejected_requisitions": kpis["rejected_requisitions"],
            "partially_fulfilled_requisitions": kpis[
                "partially_fulfilled_requisitions"
            ],
            "fulfillment_rate": kpis["fulfillment_rate"],
        },
        "distribution": {
            "by_lga": lga_distribution,
            "by_school_type": charts["distribution_by_school_type"],
            "by_school": school_distribution,
        },
        "accountability": {
            "inventory_accuracy": kpis["inventory_accuracy"],
            "damaged_items": kpis["damaged_items"],
            "average_fulfillment_days": kpis["average_fulfillment_days"],
        },
        "stock_levels": stock_levels,
        "requisition_status_breakdown": requisition_analytics[
            "requisition_status_distribution"
        ],
        "requested_vs_approved_vs_fulfilled": requisition_analytics[
            "requested_vs_approved_vs_fulfilled"
        ],
        "top_requested_items": requisition_analytics["top_requested_items"],
        "requests_by_lga": requisition_analytics["requests_by_lga"],
        "recent_inventory_movements": build_recent_movements_table(enriched),
        "recent_requisitions": requisition_analytics["recent_requisitions"],
        "fulfillment_summary": requisition_analytics["fulfillment_summary"],
        "school_distribution": school_distribution,
        "lga_distribution": lga_distribution,
        "warehouse_analytics": warehouse_analytics,
        "monthly_stock_movements": monthly_movements,
        "charts": charts,
        "tables": {
            "stock_levels": stock_levels,
            "low_stock_alerts": build_stock_levels_table(low_stock),
            "recent_movements": build_recent_movements_table(enriched),
            "recent_requisitions": requisition_analytics["recent_requisitions"],
            "fulfillment_summary": requisition_analytics["fulfillment_summary"],
        },
    }


def sanitize_for_json(value: Any) -> Any:
    if value is None:
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, pd.DataFrame):
        return sanitize_for_json(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return sanitize_for_json(value.tolist())
    if isinstance(value, dict):
        return {
            str(sanitize_for_json(key)): sanitize_for_json(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_for_json(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, np.datetime64):
        return None if np.isnat(value) else str(value)
    if isinstance(value, np.generic):
        return sanitize_for_json(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (int, str, bool)):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def write_dashboard_data(data: dict[str, Any], output_path: Path = OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sanitized_data = sanitize_for_json(data)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(sanitized_data, output_file, indent=2, allow_nan=False)


def main() -> None:
    dashboard_data = build_dashboard_data(read_all_data())
    write_dashboard_data(dashboard_data)
    logging.info("Dashboard metrics written to %s", OUTPUT_PATH)


if __name__ == "__main__":
    main()
