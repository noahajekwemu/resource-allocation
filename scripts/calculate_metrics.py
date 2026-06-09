import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SPREADSHEET_NAME = "Educational_Supplies_Logs"
TRANSACTIONS_WORKSHEET = "Transactions"
TRANSACTION_DETAILS_WORKSHEET = "Transaction_Details"
ITEMS_WORKSHEET = "Items"
SCHOOLS_WORKSHEET = "Schools"
WAREHOUSES_WORKSHEET = "Warehouses"
REQUISITIONS_WORKSHEET = "Requisitions"
OUTPUT_PATH = Path("dashboard") / "data.json"


def normalize_column_name(column_name: str) -> str:
    """Normalize a worksheet column name for flexible matching."""
    return str(column_name).strip().lower().replace(" ", "_")


def find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
    required: bool = False,
) -> str | None:
    """Return the first matching column from a list of possible names."""
    normalized_columns = {
        normalize_column_name(column): column for column in dataframe.columns
    }

    for candidate in candidates:
        normalized_candidate = normalize_column_name(candidate)
        if normalized_candidate in normalized_columns:
            return normalized_columns[normalized_candidate]

    if required:
        logging.warning("Missing required column. Expected one of: %s", candidates)

    return None


def read_worksheet_data(worksheet_name: str) -> pd.DataFrame:
    """Read worksheet data using db_connector.py."""
    try:
        from scripts.db_connector import read_worksheet
    except ModuleNotFoundError:
        import sys

        sys.path.append(str(Path(__file__).resolve().parents[1]))
        from scripts.db_connector import read_worksheet

    try:
        logging.info("Reading %s / %s", SPREADSHEET_NAME, worksheet_name)
        return read_worksheet(SPREADSHEET_NAME, worksheet_name)
    except Exception as exc:
        logging.exception("Failed to read worksheet %s: %s", worksheet_name, exc)
        raise


def read_all_data() -> dict[str, pd.DataFrame]:
    """Load all worksheets needed for dashboard aggregation."""
    return {
        "transactions": read_worksheet_data(TRANSACTIONS_WORKSHEET),
        "transaction_details": read_worksheet_data(TRANSACTION_DETAILS_WORKSHEET),
        "items": read_worksheet_data(ITEMS_WORKSHEET),
        "schools": read_worksheet_data(SCHOOLS_WORKSHEET),
        "warehouses": read_worksheet_data(WAREHOUSES_WORKSHEET),
        "requisitions": read_worksheet_data(REQUISITIONS_WORKSHEET),
    }


def clean_id_series(series: pd.Series) -> pd.Series:
    """Convert IDs to stripped strings for reliable joins."""
    return series.fillna("").astype(str).str.strip()


def safe_text_column(dataframe: pd.DataFrame, column: str | None) -> pd.Series:
    """Return a text column or an empty text series when the column is missing."""
    if column and column in dataframe.columns:
        return dataframe[column].fillna("").astype(str).str.strip()
    return pd.Series([""] * len(dataframe), index=dataframe.index, dtype="object")


def safe_numeric_column(dataframe: pd.DataFrame, column: str | None) -> pd.Series:
    """Return a numeric column or a zero series when the column is missing."""
    if column and column in dataframe.columns:
        return pd.to_numeric(dataframe[column], errors="coerce").fillna(0)
    return pd.Series([0] * len(dataframe), index=dataframe.index, dtype="float64")


def prepare_items(items: pd.DataFrame) -> pd.DataFrame:
    """Normalize Items data and keep one row for every Item_ID."""
    columns = ["Item_ID", "Item_Name", "Category", "Reorder_Level"]
    if items.empty:
        return pd.DataFrame(columns=columns)

    item_id_column = find_column(items, ["Item_ID", "Item ID"], required=True)
    item_name_column = find_column(items, ["Item_Name", "Item Name", "Item"])
    category_column = find_column(items, ["Category", "Item_Category", "Item Category"])
    reorder_column = find_column(items, ["Reorder_Level", "Reorder Level", "Minimum_Stock"])

    prepared = pd.DataFrame(index=items.index)
    prepared["Item_ID"] = clean_id_series(items[item_id_column]) if item_id_column else ""
    prepared["Item_Name"] = safe_text_column(items, item_name_column)
    prepared["Category"] = safe_text_column(items, category_column)
    prepared["Reorder_Level"] = safe_numeric_column(items, reorder_column).round().astype(int)
    prepared["Item_Name"] = prepared["Item_Name"].where(
        prepared["Item_Name"] != "", prepared["Item_ID"]
    )
    prepared["Category"] = prepared["Category"].where(
        prepared["Category"] != "", "Uncategorized"
    )
    return prepared[prepared["Item_ID"] != ""].drop_duplicates("Item_ID", keep="last")


def prepare_schools(schools: pd.DataFrame) -> pd.DataFrame:
    """Normalize Schools data for joins and distribution charts."""
    columns = ["School_ID", "School_Name", "LGA", "School_Type"]
    if schools.empty:
        return pd.DataFrame(columns=columns)

    school_id_column = find_column(schools, ["School_ID", "School ID"], required=True)
    school_name_column = find_column(schools, ["School_Name", "School Name", "School"])
    lga_column = find_column(schools, ["LGA", "Local_Government", "Local Government"])
    school_type_column = find_column(schools, ["School_Type", "School Type", "Type"])

    prepared = pd.DataFrame(index=schools.index)
    prepared["School_ID"] = clean_id_series(schools[school_id_column]) if school_id_column else ""
    prepared["School_Name"] = safe_text_column(schools, school_name_column)
    prepared["LGA"] = safe_text_column(schools, lga_column)
    prepared["School_Type"] = safe_text_column(schools, school_type_column)
    prepared["School_Name"] = prepared["School_Name"].where(
        prepared["School_Name"] != "", prepared["School_ID"]
    )
    prepared["LGA"] = prepared["LGA"].where(prepared["LGA"] != "", "Unknown")
    prepared["School_Type"] = prepared["School_Type"].where(
        prepared["School_Type"] != "", "Unknown"
    )
    return prepared[prepared["School_ID"] != ""].drop_duplicates("School_ID", keep="last")


def prepare_warehouses(warehouses: pd.DataFrame) -> pd.DataFrame:
    """Normalize Warehouses data for joins and KPI counts."""
    columns = ["Warehouse_ID", "Warehouse_Name"]
    if warehouses.empty:
        return pd.DataFrame(columns=columns)

    warehouse_id_column = find_column(warehouses, ["Warehouse_ID", "Warehouse ID"], required=True)
    warehouse_name_column = find_column(
        warehouses, ["Warehouse_Name", "Warehouse Name", "Warehouse"]
    )

    prepared = pd.DataFrame(index=warehouses.index)
    prepared["Warehouse_ID"] = (
        clean_id_series(warehouses[warehouse_id_column]) if warehouse_id_column else ""
    )
    prepared["Warehouse_Name"] = safe_text_column(warehouses, warehouse_name_column)
    prepared["Warehouse_Name"] = prepared["Warehouse_Name"].where(
        prepared["Warehouse_Name"] != "", prepared["Warehouse_ID"]
    )
    return prepared[prepared["Warehouse_ID"] != ""].drop_duplicates(
        "Warehouse_ID", keep="last"
    )


def prepare_requisitions(requisitions: pd.DataFrame) -> pd.DataFrame:
    """Normalize Requisitions data and preserve the school relationship."""
    columns = ["School_ID", "Status"]
    if requisitions.empty:
        return pd.DataFrame(columns=columns)

    school_id_column = find_column(requisitions, ["School_ID", "School ID"])
    status_column = find_column(requisitions, ["Status", "Requisition_Status"])

    prepared = pd.DataFrame(index=requisitions.index)
    prepared["School_ID"] = (
        clean_id_series(requisitions[school_id_column]) if school_id_column else ""
    )
    prepared["Status"] = safe_text_column(requisitions, status_column)
    return prepared


def prepare_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    """Normalize Transactions header data."""
    columns = [
        "Transaction_ID",
        "Transaction_Date",
        "Transaction_Type",
        "Warehouse_ID",
        "Destination_School_ID",
        "Source",
        "Status",
        "Remarks",
    ]
    if transactions.empty:
        return pd.DataFrame(columns=columns)

    transaction_id_column = find_column(
        transactions, ["Transaction_ID", "Transaction ID"], required=True
    )
    transaction_date_column = find_column(
        transactions, ["Transaction_Date", "Transaction Date", "Date"]
    )
    transaction_type_column = find_column(
        transactions, ["Transaction_Type", "Transaction Type", "Type"], required=True
    )
    warehouse_id_column = find_column(transactions, ["Warehouse_ID", "Warehouse ID"])
    school_id_column = find_column(
        transactions,
        ["Destination_School_ID", "Destination School ID", "School_ID", "School ID"],
    )
    source_column = find_column(transactions, ["Source"])
    status_column = find_column(transactions, ["Status"])
    remarks_column = find_column(transactions, ["Remarks", "Notes"])

    prepared = pd.DataFrame(index=transactions.index)
    prepared["Transaction_ID"] = (
        clean_id_series(transactions[transaction_id_column]) if transaction_id_column else ""
    )
    prepared["Transaction_Date"] = safe_text_column(transactions, transaction_date_column)
    prepared["Transaction_Type"] = safe_text_column(
        transactions, transaction_type_column
    ).str.upper()
    prepared["Warehouse_ID"] = safe_text_column(transactions, warehouse_id_column)
    prepared["Destination_School_ID"] = safe_text_column(transactions, school_id_column)
    prepared["Source"] = safe_text_column(transactions, source_column)
    prepared["Status"] = safe_text_column(transactions, status_column)
    prepared["Remarks"] = safe_text_column(transactions, remarks_column)
    return prepared[prepared["Transaction_ID"] != ""]


def prepare_transaction_details(details: pd.DataFrame) -> pd.DataFrame:
    """Normalize Transaction_Details line-item data."""
    columns = ["Detail_ID", "Transaction_ID", "Item_ID", "Quantity", "Condition"]
    if details.empty:
        return pd.DataFrame(columns=columns)

    detail_id_column = find_column(details, ["Detail_ID", "Detail ID"])
    transaction_id_column = find_column(
        details, ["Transaction_ID", "Transaction ID"], required=True
    )
    item_id_column = find_column(details, ["Item_ID", "Item ID"], required=True)
    quantity_column = find_column(details, ["Quantity", "Qty"], required=True)
    condition_column = find_column(details, ["Condition"])

    prepared = pd.DataFrame(index=details.index)
    prepared["Detail_ID"] = safe_text_column(details, detail_id_column)
    prepared["Transaction_ID"] = (
        clean_id_series(details[transaction_id_column]) if transaction_id_column else ""
    )
    prepared["Item_ID"] = clean_id_series(details[item_id_column]) if item_id_column else ""
    prepared["Quantity"] = safe_numeric_column(details, quantity_column)
    prepared["Condition"] = safe_text_column(details, condition_column).str.upper()
    return prepared[(prepared["Transaction_ID"] != "") & (prepared["Item_ID"] != "")]


def calculate_signed_quantity(row: pd.Series) -> float:
    """Convert a joined transaction line into signed stock movement."""
    transaction_type = str(row.get("Transaction_Type", "")).upper()
    quantity = float(row.get("Quantity", 0))

    if transaction_type == "IN":
        return abs(quantity)
    if transaction_type == "OUT":
        return -abs(quantity)
    if transaction_type == "ADJUSTMENT":
        return quantity

    return 0


def build_movements(transactions: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    """Join transaction headers to line items and calculate signed movement quantities."""
    output_columns = [
        "Detail_ID",
        "Transaction_ID",
        "Transaction_Date",
        "Transaction_Type",
        "Warehouse_ID",
        "Destination_School_ID",
        "Source",
        "Status",
        "Remarks",
        "Item_ID",
        "Quantity",
        "Condition",
        "Signed_Quantity",
    ]
    if transactions.empty or details.empty:
        return pd.DataFrame(columns=output_columns)

    movements = details.merge(transactions, how="left", on="Transaction_ID")
    movements["Signed_Quantity"] = movements.apply(calculate_signed_quantity, axis=1)
    return movements[output_columns]


def build_stock_balances(items: pd.DataFrame, movements: pd.DataFrame) -> pd.DataFrame:
    """Generate current stock for every Item_ID from normalized movement rows."""
    stock = items[["Item_ID", "Item_Name", "Category", "Reorder_Level"]].copy()

    if movements.empty:
        stock["Current_Stock"] = 0
        return stock

    balances = (
        movements.groupby("Item_ID", dropna=False)["Signed_Quantity"]
        .sum()
        .reset_index()
        .rename(columns={"Signed_Quantity": "Current_Stock"})
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
    """Join movement rows to Items, Schools, and Warehouses."""
    if movements.empty:
        return movements.assign(
            Item_Name=pd.Series(dtype="object"),
            Category=pd.Series(dtype="object"),
            School_Name=pd.Series(dtype="object"),
            LGA=pd.Series(dtype="object"),
            School_Type=pd.Series(dtype="object"),
            Warehouse_Name=pd.Series(dtype="object"),
        )

    enriched = movements.merge(
        items[["Item_ID", "Item_Name", "Category"]], how="left", on="Item_ID"
    )
    enriched = enriched.merge(
        schools,
        how="left",
        left_on="Destination_School_ID",
        right_on="School_ID",
    )
    enriched = enriched.merge(warehouses, how="left", on="Warehouse_ID")
    enriched["Item_Name"] = enriched["Item_Name"].fillna(enriched["Item_ID"])
    enriched["Category"] = enriched["Category"].fillna("Uncategorized")
    enriched["School_Name"] = enriched["School_Name"].fillna(
        enriched["Destination_School_ID"]
    )
    enriched["LGA"] = enriched["LGA"].fillna("Unknown")
    enriched["School_Type"] = enriched["School_Type"].fillna("Unknown")
    enriched["Warehouse_Name"] = enriched["Warehouse_Name"].fillna(enriched["Warehouse_ID"])
    return enriched


def count_pending_requisitions(requisitions: pd.DataFrame) -> int:
    """Count requisitions where Status is Pending."""
    if requisitions.empty or "Status" not in requisitions.columns:
        return 0
    return int(requisitions["Status"].str.upper().eq("PENDING").sum())


def calculate_inventory_accuracy(total_inventory_items: int, negative_stock_items: int) -> float:
    """Calculate inventory accuracy percentage rounded to two decimals."""
    if total_inventory_items == 0:
        return 100.0
    return round(
        ((total_inventory_items - negative_stock_items) / total_inventory_items) * 100,
        2,
    )


def build_kpis(
    stock_balances: pd.DataFrame,
    movements: pd.DataFrame,
    schools: pd.DataFrame,
    warehouses: pd.DataFrame,
    requisitions: pd.DataFrame,
) -> dict[str, Any]:
    """Build all KPI values for the dashboard."""
    total_inventory_items = int(len(stock_balances))
    negative_stock_items = int((stock_balances["Current_Stock"] < 0).sum())
    out_movements = movements[movements["Transaction_Type"] == "OUT"]

    return {
        "inventory_accuracy": calculate_inventory_accuracy(
            total_inventory_items, negative_stock_items
        ),
        "total_inventory_items": total_inventory_items,
        "total_available_stock": int(stock_balances["Current_Stock"].clip(lower=0).sum()),
        "low_stock_items": int(
            (stock_balances["Current_Stock"] <= stock_balances["Reorder_Level"]).sum()
        ),
        "out_of_stock_items": int((stock_balances["Current_Stock"] <= 0).sum()),
        "damaged_items": int(movements["Condition"].eq("DAMAGED").sum())
        if "Condition" in movements.columns
        else 0,
        "schools_served": int(
            out_movements["Destination_School_ID"]
            .replace("", pd.NA)
            .dropna()
            .nunique()
        ),
        "pending_requisitions": count_pending_requisitions(requisitions),
        "total_warehouses": int(len(warehouses)),
        "total_schools": int(len(schools)),
        "total_categories": int(
            stock_balances["Category"].replace("", pd.NA).dropna().nunique()
        ),
    }


def group_quantity_records(
    dataframe: pd.DataFrame,
    group_column: str,
    quantity_column: str,
    label_key: str,
    limit: int | None = None,
    ascending: bool = False,
) -> list[dict[str, Any]]:
    """Aggregate quantity by a label and return chart-ready records."""
    if dataframe.empty or group_column not in dataframe.columns:
        return []

    grouped = (
        dataframe.groupby(group_column, dropna=False)[quantity_column]
        .sum()
        .reset_index()
        .sort_values(quantity_column, ascending=ascending)
    )

    if limit is not None:
        grouped = grouped.head(limit)

    return [
        {label_key: str(row[group_column]), "quantity": int(row[quantity_column])}
        for _, row in grouped.iterrows()
    ]


def build_charts(
    stock_balances: pd.DataFrame,
    enriched_movements: pd.DataFrame,
) -> dict[str, list[dict[str, Any]]]:
    """Build every chart dataset with all calculations completed server-side."""
    out_movements = enriched_movements[
        enriched_movements["Transaction_Type"] == "OUT"
    ].copy()
    in_movements = enriched_movements[
        enriched_movements["Transaction_Type"] == "IN"
    ].copy()
    out_movements["Out_Quantity"] = out_movements["Quantity"].abs()
    in_movements["In_Quantity"] = in_movements["Quantity"].abs()

    return {
        "inventory_by_category": group_quantity_records(
            stock_balances, "Category", "Current_Stock", "category"
        ),
        "distribution_by_lga": group_quantity_records(
            out_movements, "LGA", "Out_Quantity", "lga"
        ),
        "distribution_by_school_type": group_quantity_records(
            out_movements, "School_Type", "Out_Quantity", "school_type"
        ),
        "top_distributed_items": group_quantity_records(
            out_movements, "Item_Name", "Out_Quantity", "item", limit=10
        ),
        "top_schools": group_quantity_records(
            out_movements, "School_Name", "Out_Quantity", "school", limit=10
        ),
        "bottom_schools": group_quantity_records(
            out_movements,
            "School_Name",
            "Out_Quantity",
            "school",
            limit=10,
            ascending=True,
        ),
        "stock_source_analysis": group_quantity_records(
            in_movements, "Source", "In_Quantity", "source"
        ),
    }


def build_stock_levels_table(stock_balances: pd.DataFrame) -> list[dict[str, Any]]:
    """Build the stock levels table dataset."""
    rows = stock_balances.sort_values(["Category", "Item_Name"])
    return [
        {
            "Item_ID": row["Item_ID"],
            "Item_Name": row["Item_Name"],
            "Category": row["Category"],
            "Current_Stock": int(row["Current_Stock"]),
            "Reorder_Level": int(row["Reorder_Level"]),
        }
        for _, row in rows.iterrows()
    ]


def build_low_stock_alerts_table(stock_balances: pd.DataFrame) -> list[dict[str, Any]]:
    """Build rows for items at or below reorder level."""
    alerts = stock_balances[
        stock_balances["Current_Stock"] <= stock_balances["Reorder_Level"]
    ].sort_values(["Current_Stock", "Item_Name"])
    return build_stock_levels_table(alerts)


def build_recent_movements_table(
    enriched_movements: pd.DataFrame,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Build the most recent transaction summary table."""
    if enriched_movements.empty:
        return []

    movements = enriched_movements.copy()
    movements["_Transaction_Date"] = pd.to_datetime(
        movements["Transaction_Date"], errors="coerce", utc=True
    )

    summaries = (
        movements.groupby(
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
        .reset_index()
        .rename(columns={"Quantity": "Total_Items"})
    )
    dates = (
        movements.groupby("Transaction_ID", dropna=False)["_Transaction_Date"]
        .max()
        .reset_index()
    )
    summaries = summaries.merge(dates, how="left", on="Transaction_ID")
    summaries = summaries.sort_values(
        "_Transaction_Date", ascending=False, na_position="last"
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


def build_tables(
    stock_balances: pd.DataFrame,
    enriched_movements: pd.DataFrame,
) -> dict[str, list[dict[str, Any]]]:
    """Build all dashboard table datasets."""
    return {
        "stock_levels": build_stock_levels_table(stock_balances),
        "low_stock_alerts": build_low_stock_alerts_table(stock_balances),
        "recent_movements": build_recent_movements_table(enriched_movements),
    }


def build_dashboard_data(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Build the complete dashboard JSON payload from normalized worksheet data."""
    logging.info("Calculating dashboard metrics from normalized inventory model.")

    transactions = prepare_transactions(data.get("transactions", pd.DataFrame()))
    details = prepare_transaction_details(data.get("transaction_details", pd.DataFrame()))
    items = prepare_items(data.get("items", pd.DataFrame()))
    schools = prepare_schools(data.get("schools", pd.DataFrame()))
    warehouses = prepare_warehouses(data.get("warehouses", pd.DataFrame()))
    requisitions = prepare_requisitions(data.get("requisitions", pd.DataFrame()))

    movements = build_movements(transactions, details)
    stock_balances = build_stock_balances(items, movements)
    enriched_movements = enrich_movements(movements, items, schools, warehouses)

    dashboard_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": build_kpis(
            stock_balances, movements, schools, warehouses, requisitions
        ),
        "charts": build_charts(stock_balances, enriched_movements),
        "tables": build_tables(stock_balances, enriched_movements),
    }

    logging.info("Dashboard metrics calculated successfully.")
    return dashboard_data


def write_dashboard_data(data: dict[str, Any], output_path: Path = OUTPUT_PATH) -> None:
    """Write dashboard JSON data to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logging.info("Writing dashboard data to %s", output_path)

    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(data, output_file, indent=2)


def main() -> None:
    """Run dashboard data generation from the command line."""
    try:
        dashboard_data = build_dashboard_data(read_all_data())
        write_dashboard_data(dashboard_data)
        logging.info("Process completed successfully.")
    except Exception as exc:
        logging.exception("Failed to calculate dashboard metrics: %s", exc)
        raise


if __name__ == "__main__":
    main()
