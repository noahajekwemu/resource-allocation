"""Read-only reporting helpers for API JSON and CSV exports."""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from flask import Response

try:
    from scripts import db_connector
except (ImportError, ModuleNotFoundError):
    import db_connector


REPORT_WORKSHEETS = {
    "items": db_connector.ITEMS_WORKSHEET,
    "schools": db_connector.SCHOOLS_WORKSHEET,
    "warehouses": db_connector.WAREHOUSES_WORKSHEET,
    "transactions": db_connector.TRANSACTIONS_WORKSHEET,
    "transaction_details": db_connector.TRANSACTION_DETAILS_WORKSHEET,
    "requisitions": db_connector.REQUISITIONS_WORKSHEET,
    "requisition_details": db_connector.REQUISITION_DETAILS_WORKSHEET,
    "audit_log": db_connector.AUDIT_LOG_WORKSHEET,
}


def _load(names: tuple[str, ...], data: dict[str, pd.DataFrame] | None) -> dict[str, pd.DataFrame]:
    if data is not None:
        return {name: data.get(name, pd.DataFrame()).copy() for name in names}
    return {
        name: db_connector.read_worksheet(
            db_connector.SPREADSHEET_NAME, REPORT_WORKSHEETS[name]
        )
        for name in names
    }


def _column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    normalized = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in frame.columns
    }
    for candidate in candidates:
        match = normalized.get(candidate.strip().lower().replace(" ", "_"))
        if match is not None:
            return match
    return None


def _canonical(frame: pd.DataFrame, fields: dict[str, list[str]]) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    for target, candidates in fields.items():
        source = _column(frame, candidates)
        result[target] = frame[source] if source else ""
    return result.fillna("")


def _number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.where(pd.notna(frame), "").to_dict(orient="records")


def _movement_data(data: dict[str, pd.DataFrame] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = _load(("items", "warehouses", "transactions", "transaction_details"), data)
    items = _canonical(source["items"], {
        "Item_ID": ["Item_ID", "Item ID"],
        "Item_Name": ["Item_Name", "Item Name"],
        "Category": ["Category"],
        "Reorder_Level": ["Reorder_Level", "Reorder Level", "Minimum_Stock"],
    })
    warehouses = _canonical(source["warehouses"], {
        "Warehouse_ID": ["Warehouse_ID", "Warehouse ID"],
        "Warehouse_Name": ["Warehouse_Name", "Warehouse Name", "Name"],
    })
    transactions = _canonical(source["transactions"], {
        "Transaction_ID": ["Transaction_ID", "Transaction ID"],
        "Transaction_Type": ["Transaction_Type", "Transaction Type", "Type"],
        "Warehouse_ID": ["Warehouse_ID", "Warehouse ID"],
    })
    details = _canonical(source["transaction_details"], {
        "Transaction_ID": ["Transaction_ID", "Transaction ID"],
        "Item_ID": ["Item_ID", "Item ID"],
        "Quantity": ["Quantity", "Qty"],
    })
    movements = details.merge(transactions, on="Transaction_ID", how="left")
    movements["Quantity"] = _number(movements["Quantity"])
    movements["Transaction_Type"] = movements["Transaction_Type"].astype(str).str.upper().str.strip()
    return items, warehouses, movements


def get_stock_report(data: dict[str, pd.DataFrame] | None = None) -> list[dict[str, Any]]:
    items, warehouses, movements = _movement_data(data)
    movements["Quantity_Received"] = movements["Quantity"].where(
        movements["Transaction_Type"].eq("IN"), 0
    )
    movements["Quantity_Issued"] = movements["Quantity"].where(
        movements["Transaction_Type"].eq("OUT"), 0
    )
    grouped = movements.groupby(
        ["Item_ID", "Warehouse_ID"], as_index=False, dropna=False
    )[["Quantity_Received", "Quantity_Issued"]].sum()
    report = items[["Item_ID", "Item_Name", "Category"]].merge(
        grouped, on="Item_ID", how="left"
    ).merge(warehouses, on="Warehouse_ID", how="left")
    for column in ("Quantity_Received", "Quantity_Issued"):
        report[column] = _number(report[column]).round().astype(int)
    report["Current_Stock"] = report["Quantity_Received"] - report["Quantity_Issued"]
    report["Warehouse_ID"] = report["Warehouse_ID"].fillna("")
    report["Warehouse_Name"] = report["Warehouse_Name"].fillna("")
    return _records(report[[
        "Item_ID", "Item_Name", "Category", "Warehouse_ID", "Warehouse_Name",
        "Quantity_Received", "Quantity_Issued", "Current_Stock",
    ]])


def _requisition_sources(data: dict[str, pd.DataFrame] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = _load(("requisitions", "requisition_details", "schools", "items"), data)
    requisitions = _canonical(source["requisitions"], {
        "Requisition_ID": ["Requisition_ID", "Requisition ID"],
        "School_ID": ["School_ID", "School ID"],
        "Requested_By": ["Requested_By", "Requested By"],
        "Status": ["Status"],
        "Created_At": ["Created_At", "Created At", "Request_Date", "Request Date"],
        "Approved_By": ["Approved_By", "Approved By"],
        "Approved_At": ["Approved_At", "Approved At", "Approval_Date", "Approval Date"],
    })
    details = _canonical(source["requisition_details"], {
        "Requisition_ID": ["Requisition_ID", "Requisition ID"],
        "Item_ID": ["Item_ID", "Item ID"],
        "Quantity_Requested": ["Quantity_Requested", "Quantity Requested"],
        "Quantity_Approved": ["Quantity_Approved", "Quantity Approved"],
        "Quantity_Fulfilled": ["Quantity_Fulfilled", "Quantity Fulfilled"],
    })
    schools = _canonical(source["schools"], {
        "School_ID": ["School_ID", "School ID"],
        "School_Name": ["School_Name", "School Name", "School"],
    })
    items = _canonical(source["items"], {
        "Item_ID": ["Item_ID", "Item ID"],
        "Item_Name": ["Item_Name", "Item Name"],
    })
    for column in ("Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"):
        details[column] = _number(details[column])
    return requisitions, details, schools, items


def get_requisition_report(
    school_id: str | None = None,
    data: dict[str, pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    requisitions, details, schools, _items = _requisition_sources(data)
    if school_id is not None:
        requisitions = requisitions[
            requisitions["School_ID"].astype(str).str.strip() == str(school_id).strip()
        ]
    totals = details.groupby("Requisition_ID", as_index=False)[[
        "Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"
    ]].sum().rename(columns={
        "Quantity_Requested": "Total_Requested",
        "Quantity_Approved": "Total_Approved",
        "Quantity_Fulfilled": "Total_Fulfilled",
    })
    report = requisitions.merge(schools, on="School_ID", how="left").merge(
        totals, on="Requisition_ID", how="left"
    )
    for column in ("Total_Requested", "Total_Approved", "Total_Fulfilled"):
        report[column] = _number(report[column]).round().astype(int)
    report["Fulfillment_Percent"] = (
        report["Total_Fulfilled"].div(report["Total_Approved"].where(report["Total_Approved"].ne(0))) * 100
    ).fillna(0).round(2)
    report["School_Name"] = report["School_Name"].fillna("")
    return _records(report[[
        "Requisition_ID", "School_ID", "School_Name", "Requested_By", "Status",
        "Created_At", "Approved_By", "Approved_At", "Total_Requested",
        "Total_Approved", "Total_Fulfilled", "Fulfillment_Percent",
    ]])


def get_fulfillment_report(
    school_id: str | None = None,
    data: dict[str, pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    requisitions, details, schools, items = _requisition_sources(data)
    if school_id is not None:
        requisitions = requisitions[
            requisitions["School_ID"].astype(str).str.strip() == str(school_id).strip()
        ]
    report = details.merge(
        requisitions[["Requisition_ID", "School_ID", "Status"]],
        on="Requisition_ID", how="inner",
    ).merge(schools, on="School_ID", how="left").merge(items, on="Item_ID", how="left")
    report["Outstanding_Quantity"] = (
        report["Quantity_Approved"] - report["Quantity_Fulfilled"]
    ).clip(lower=0).round().astype(int)
    for column in ("Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled"):
        report[column] = _number(report[column]).round().astype(int)
    return _records(report[[
        "Requisition_ID", "School_ID", "School_Name", "Item_ID", "Item_Name",
        "Quantity_Requested", "Quantity_Approved", "Quantity_Fulfilled",
        "Outstanding_Quantity", "Status",
    ]])


def get_executive_summary(data: dict[str, pd.DataFrame] | None = None) -> dict[str, Any]:
    source = _load((
        "items", "schools", "warehouses", "requisitions", "requisition_details",
        "transactions", "transaction_details",
    ), data)
    requisitions = _canonical(source["requisitions"], {"Status": ["Status"]})
    statuses = requisitions["Status"].astype(str).str.strip().str.lower()
    stock_rows = get_stock_report(source)
    total_received = sum(int(row["Quantity_Received"]) for row in stock_rows)
    total_issued = sum(int(row["Quantity_Issued"]) for row in stock_rows)
    details = _canonical(source["requisition_details"], {
        "Approved": ["Quantity_Approved", "Quantity Approved"],
        "Fulfilled": ["Quantity_Fulfilled", "Quantity Fulfilled"],
    })
    approved = float(_number(details["Approved"]).sum())
    fulfilled = float(_number(details["Fulfilled"]).sum())
    items = _canonical(source["items"], {
        "Item_ID": ["Item_ID", "Item ID"],
        "Reorder_Level": ["Reorder_Level", "Reorder Level", "Minimum_Stock"],
    })
    current_by_item = {}
    for row in stock_rows:
        current_by_item[row["Item_ID"]] = current_by_item.get(row["Item_ID"], 0) + int(row["Current_Stock"])
    low_stock = sum(
        current_by_item.get(str(row["Item_ID"]), 0) <= float(row["Reorder_Level"] or 0)
        for row in items.to_dict(orient="records")
    )
    return {
        "total_items": int(len(source["items"])),
        "total_schools": int(len(source["schools"])),
        "total_warehouses": int(len(source["warehouses"])),
        "total_requisitions": int(len(source["requisitions"])),
        "approved_requisitions": int(statuses.eq("approved").sum()),
        "rejected_requisitions": int(statuses.eq("rejected").sum()),
        "fulfilled_requisitions": int(statuses.eq("fulfilled").sum()),
        "partially_fulfilled_requisitions": int(statuses.eq("partially fulfilled").sum()),
        "pending_requisitions": int(statuses.eq("pending").sum()),
        "total_stock_received": total_received,
        "total_stock_issued": total_issued,
        "fulfillment_rate_percent": round((fulfilled / approved * 100) if approved else 0, 2),
        "low_stock_items": int(low_stock),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_audit_report(
    action: str | None = None,
    user_id: str | None = None,
    data: dict[str, pd.DataFrame] | None = None,
) -> list[dict[str, Any]]:
    audit = _load(("audit_log",), data)["audit_log"].fillna("")
    if action and (column := _column(audit, ["Action"])):
        audit = audit[audit[column].astype(str).str.casefold() == action.casefold()]
    if user_id and (column := _column(audit, ["User_ID", "User ID"])):
        audit = audit[audit[column].astype(str).str.strip() == user_id.strip()]
    hidden = {"password", "password_hash"}
    safe_columns = [
        column for column in audit.columns
        if str(column).strip().lower().replace(" ", "_") not in hidden
    ]
    records = _records(audit[safe_columns])
    state_fields = {"before_state", "after_state"}
    for record in records:
        for key, value in record.items():
            normalized_key = str(key).strip().lower().replace(" ", "_")
            if normalized_key not in state_fields or not isinstance(value, str):
                continue
            try:
                state = json.loads(value)
            except (TypeError, ValueError):
                continue
            record[key] = json.dumps(_redact_password_fields(state), separators=(",", ":"))
    return records


def _redact_password_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_password_fields(item)
            for key, item in value.items()
            if str(key).strip().lower().replace(" ", "_")
            not in {"password", "password_hash"}
        }
    if isinstance(value, list):
        return [_redact_password_fields(item) for item in value]
    return value


def records_to_csv_response(records: list[dict[str, Any]], filename: str) -> Response:
    fieldnames = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    if fieldnames:
        writer.writeheader()
        writer.writerows(records)
    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
