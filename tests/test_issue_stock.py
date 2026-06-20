from unittest.mock import call, patch

from scripts.form_api import submit_issue_stock


def test_submit_issue_stock_validates_stock_and_writes_rows():
    payload = {
        "Warehouse_ID": "WH-001",
        "Destination_School_ID": "SCH-001",
        "items": [{"Item_ID": "ITEM-001", "Quantity": 20}],
    }

    with (
        patch("scripts.form_api.get_available_stock", return_value=25) as available_stock,
        patch("scripts.form_api._next_id", return_value="TXN-2026-000002"),
        patch(
            "scripts.form_api._next_detail_ids",
            return_value=["TD-2026-000003"],
        ),
        patch("scripts.form_api._append_dict_row") as append_dict_row,
    ):
        result = submit_issue_stock(payload)

    assert result == {
        "transaction_id": "TXN-2026-000002",
        "detail_ids": ["TD-2026-000003"],
        "line_items": 1,
        "status": "success",
    }
    available_stock.assert_called_once_with("ITEM-001")
    assert append_dict_row.call_args_list[0].args[0] == "Transactions"
    assert append_dict_row.call_args_list[0].args[1]["Transaction_Type"] == "OUT"
    assert append_dict_row.call_args_list[0].args[1]["Warehouse_ID"] == "WH-001"
    assert append_dict_row.call_args_list[0].args[1]["Destination_School_ID"] == "SCH-001"
    assert append_dict_row.call_args_list[1] == call(
        "Transaction_Details",
        {
            "Detail_ID": "TD-2026-000003",
            "Transaction_ID": "TXN-2026-000002",
            "Item_ID": "ITEM-001",
            "Quantity": 20,
            "Condition": "Good",
        },
    )
