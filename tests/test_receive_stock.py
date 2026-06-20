from unittest.mock import call, patch

from scripts.form_api import submit_receive_stock


def test_submit_receive_stock_writes_header_and_item_rows():
    payload = {
        "Warehouse_ID": "WH-001",
        "Source": "UBEC",
        "Remarks": "Initial stock",
        "Transaction_Date": "2026-06-20T10:00:00+00:00",
        "items": [
            {"Item_ID": "ITEM-001", "Quantity": 100},
            {"Item_ID": "ITEM-002", "Quantity": 50},
        ],
    }

    with (
        patch("scripts.form_api._next_id", return_value="TXN-2026-000001"),
        patch(
            "scripts.form_api._next_detail_ids",
            return_value=["TD-2026-000001", "TD-2026-000002"],
        ),
        patch("scripts.form_api._append_dict_row") as append_dict_row,
    ):
        result = submit_receive_stock(payload)

    assert result == {
        "transaction_id": "TXN-2026-000001",
        "detail_ids": ["TD-2026-000001", "TD-2026-000002"],
        "line_items": 2,
        "status": "success",
    }
    assert append_dict_row.call_args_list == [
        call(
            "Transactions",
            {
                "Transaction_ID": "TXN-2026-000001",
                "Transaction_Date": "2026-06-20T10:00:00+00:00",
                "Transaction_Type": "IN",
                "Warehouse_ID": "WH-001",
                "Destination_School_ID": "",
                "Requisition_ID": "",
                "Source": "UBEC",
                "Status": "Completed",
                "Remarks": "Initial stock",
            },
        ),
        call(
            "Transaction_Details",
            {
                "Detail_ID": "TD-2026-000001",
                "Transaction_ID": "TXN-2026-000001",
                "Item_ID": "ITEM-001",
                "Quantity": 100,
                "Condition": "Good",
            },
        ),
        call(
            "Transaction_Details",
            {
                "Detail_ID": "TD-2026-000002",
                "Transaction_ID": "TXN-2026-000001",
                "Item_ID": "ITEM-002",
                "Quantity": 50,
                "Condition": "Good",
            },
        ),
    ]
