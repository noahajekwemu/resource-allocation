from scripts.form_api import submit_issue_stock

result = submit_issue_stock(
    {
        "Warehouse_ID": "WH-001",
        "Destination_School_ID": "SCH-001",

        "items": [
            {
                "Item_ID": "ITEM-001",
                "Quantity": 20
            }
        ]
    }
)

print(result)