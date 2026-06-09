from scripts.form_api import submit_receive_stock

result = submit_receive_stock(
    {
        "Warehouse_ID": "WH-001",
        "Source": "UBEC",
        "Remarks": "Initial stock",

        "Items": [
            {
                "Item_ID": "ITEM-001",
                "Quantity": 100
            },
            {
                "Item_ID": "ITEM-002",
                "Quantity": 50
            }
        ]
    }
)

print(result)