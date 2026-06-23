"""Explicitly seed realistic, non-sensitive demo data in Google Sheets."""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from typing import Any

from scripts.db_connector import (
    ITEMS_WORKSHEET,
    REQUISITION_DETAILS_WORKSHEET,
    REQUISITIONS_WORKSHEET,
    SCHOOLS_WORKSHEET,
    SPREADSHEET_NAME,
    TRANSACTION_DETAILS_WORKSHEET,
    TRANSACTIONS_WORKSHEET,
    WAREHOUSES_WORKSHEET,
)


SEED_ORDER = (
    ITEMS_WORKSHEET,
    SCHOOLS_WORKSHEET,
    WAREHOUSES_WORKSHEET,
    REQUISITIONS_WORKSHEET,
    REQUISITION_DETAILS_WORKSHEET,
    TRANSACTIONS_WORKSHEET,
    TRANSACTION_DETAILS_WORKSHEET,
)
ID_COLUMNS = {
    ITEMS_WORKSHEET: "Item_ID",
    SCHOOLS_WORKSHEET: "School_ID",
    WAREHOUSES_WORKSHEET: "Warehouse_ID",
    REQUISITIONS_WORKSHEET: "Requisition_ID",
    REQUISITION_DETAILS_WORKSHEET: "Req_Detail_ID",
    TRANSACTIONS_WORKSHEET: "Transaction_ID",
    TRANSACTION_DETAILS_WORKSHEET: "Detail_ID",
}


def build_sample_data() -> dict[str, list[dict[str, Any]]]:
    item_names = (
        "Mathematics Textbook", "English Textbook", "Basic Science Textbook",
        "Social Studies Textbook", "Exercise Book", "Chalk Box",
        "Classroom Chair", "Classroom Desk", "Teacher Table", "Whiteboard",
        "School Bag", "First Aid Box",
    )
    categories = (
        "Textbooks", "Textbooks", "Textbooks", "Textbooks", "Stationery",
        "Stationery", "Furniture", "Furniture", "Furniture", "Teaching Aids",
        "Student Supplies", "Health and Safety",
    )
    reorder_levels = (30, 30, 25, 25, 50, 15, 20, 20, 8, 8, 10, 10)
    items = [
        {
            "Item_ID": f"ITEM{index:03d}", "Item_Name": name,
            "Category": categories[index - 1], "Unit": "Unit",
            "Minimum_Stock": reorder_levels[index - 1], "Status": "Active",
        }
        for index, name in enumerate(item_names, 1)
    ]

    lgas = (
        "Makurdi", "Gboko", "Otukpo", "Katsina-Ala", "Vandeikya",
        "Kwande", "Guma", "Logo", "Oju", "Ogbadibo",
    )
    schools = []
    for index in range(1, 21):
        lga = lgas[(index - 1) % len(lgas)]
        schools.append({
            "School_ID": f"SCH{index:03d}",
            "School_Name": f"{lga} Demonstration {'Primary' if index % 2 else 'Secondary'} School {((index - 1) // 10) + 1}",
            "LGA": lga, "Zone": f"Zone {((index - 1) % 5) + 1}",
            "School_Type": "Primary" if index % 2 else "Secondary",
            "Status": "Active",
        })

    warehouse_names = (
        "Makurdi Central Store", "Gboko Zonal Store", "Otukpo Zonal Store",
        "Katsina-Ala Zonal Store", "Vandeikya Zonal Store",
    )
    warehouses = []
    for index, name in enumerate(warehouse_names, 1):
        lga = name.split()[0]
        warehouses.append({
            "Warehouse_ID": f"WH{index:03d}",
            "Warehouse_Name": name,
            "LGA": lga,
            "Zone": f"Zone {index}",
            "Status": "Active",
        })

    statuses = (
        ["Fulfilled"] * 5 + ["Partially Fulfilled"] * 3 + ["Pending"] * 3
        + ["Approved"] * 2 + ["Rejected"] * 2
    )
    start = date(2026, 4, 1)
    requisitions = []
    requisition_details = []
    detail_number = 1
    for index, status in enumerate(statuses, 1):
        requested = 20 + index * 2
        if status == "Rejected":
            approved = fulfilled = 0
        elif status == "Pending":
            approved = fulfilled = 0
        elif status == "Approved":
            approved, fulfilled = requested - 2, 0
        elif status == "Partially Fulfilled":
            approved, fulfilled = requested - 2, requested // 2
        else:
            approved = fulfilled = requested - 2
        request_date = start + timedelta(days=(index - 1) * 2)
        requisitions.append({
            "Requisition_ID": f"REQ{index:03d}", "School_ID": f"SCH{index:03d}",
            "Request_Date": request_date.isoformat(), "Status": status,
            "Requested_By": f"School Officer {index}",
            "Approved_By": "Demo Approver" if status not in {"Pending", "Rejected"} else "",
            "Approval_Date": (request_date + timedelta(days=1)).isoformat()
            if status not in {"Pending", "Rejected"} else "",
            "Remarks": "Term supplies",
        })
        for offset in range(2):
            item_id = f"ITEM{((index + offset - 1) % 12) + 1:03d}"
            requisition_details.append({
                "Req_Detail_ID": f"RD{detail_number:03d}",
                "Requisition_ID": f"REQ{index:03d}", "Item_ID": item_id,
                "Quantity_Requested": requested + offset * 5,
                "Quantity_Approved": approved + (offset * 5 if approved else 0),
                "Quantity_Fulfilled": fulfilled + (offset * 5 if fulfilled else 0),
            })
            detail_number += 1

    transactions = []
    transaction_details = []
    transaction_detail_number = 501
    inbound_quantities = (160, 150, 140, 130, 220, 80, 100, 100, 50, 45, 30, 24)
    for transaction_index in range(5):
        transaction_id = f"TXN-2026-{101 + transaction_index:06d}"
        transactions.append({
            "Transaction_ID": transaction_id,
            "Transaction_Date": (start - timedelta(days=14 - transaction_index * 3)).isoformat(),
            "Transaction_Type": "IN", "Warehouse_ID": f"WH{transaction_index + 1:03d}",
            "Destination_School_ID": "", "Requisition_ID": "",
            "Source": "SUBEB Annual Procurement", "Status": "Completed",
            "Remarks": "Demo stock receipt",
        })
        for item_index in range(transaction_index, 12, 5):
            transaction_details.append({
                "Detail_ID": f"TD-2026-{transaction_detail_number:06d}",
                "Transaction_ID": transaction_id, "Item_ID": f"ITEM{item_index + 1:03d}",
                "Quantity": inbound_quantities[item_index], "Condition": "GOOD",
            })
            transaction_detail_number += 1

    for offset in range(20):
        transaction_id = f"TXN-2026-{106 + offset:06d}"
        requisition_id = f"REQ{(offset % 8) + 1:03d}" if offset < 8 else ""
        transactions.append({
            "Transaction_ID": transaction_id,
            "Transaction_Date": (start + timedelta(days=offset * 2)).isoformat(),
            "Transaction_Type": "OUT", "Warehouse_ID": f"WH{(offset % 5) + 1:03d}",
            "Destination_School_ID": f"SCH{(offset % 20) + 1:03d}",
            "Requisition_ID": requisition_id, "Source": "",
            "Status": "Completed", "Remarks": "Demo school issue",
        })
        for item_offset in range(2):
            item_number = ((offset * 2 + item_offset) % 12) + 1
            quantity = 8
            if item_number == 12:
                quantity = 8
            transaction_details.append({
                "Detail_ID": f"TD-2026-{transaction_detail_number:06d}",
                "Transaction_ID": transaction_id, "Item_ID": f"ITEM{item_number:03d}",
                "Quantity": quantity, "Condition": "GOOD",
            })
            transaction_detail_number += 1

    return {
        ITEMS_WORKSHEET: items, SCHOOLS_WORKSHEET: schools,
        WAREHOUSES_WORKSHEET: warehouses, REQUISITIONS_WORKSHEET: requisitions,
        REQUISITION_DETAILS_WORKSHEET: requisition_details,
        TRANSACTIONS_WORKSHEET: transactions,
        TRANSACTION_DETAILS_WORKSHEET: transaction_details,
    }


def append_demo_data(data: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    from scripts.db_connector import append_records, find_column, read_worksheet

    counts = {}
    for worksheet_name in SEED_ORDER:
        records = data[worksheet_name]
        existing = read_worksheet(SPREADSHEET_NAME, worksheet_name)
        id_column = ID_COLUMNS[worksheet_name]
        existing_id_column = find_column(existing, [id_column], required=False)
        existing_ids = (
            set(existing[existing_id_column].fillna("").astype(str).str.strip())
            if existing_id_column else set()
        )
        new_records = [row for row in records if str(row[id_column]) not in existing_ids]
        counts[worksheet_name] = append_records(
            SPREADSHEET_NAME, worksheet_name, new_records
        )
    return counts


def print_summary(counts: dict[str, int], dry_run: bool) -> None:
    action = "Would add" if dry_run else "Added"
    for worksheet_name in SEED_ORDER:
        print(f"{action} {counts.get(worksheet_name, 0)} rows to {worksheet_name}")
    print("WARNING: Users and Audit_Log were not modified.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--append-demo", action="store_true", help="append missing demo rows")
    mode.add_argument("--dry-run", action="store_true", help="preview without connecting or writing")
    args = parser.parse_args(argv)
    data = build_sample_data()
    counts = (
        {name: len(rows) for name, rows in data.items()}
        if args.dry_run else append_demo_data(data)
    )
    print_summary(counts, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
