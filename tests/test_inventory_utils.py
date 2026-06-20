import unittest

import pandas as pd

from scripts.inventory_utils import calculate_available_stock


class InventoryUtilsTests(unittest.TestCase):
    def test_calculate_available_stock_subtracts_out_from_in(self):
        transactions = pd.DataFrame(
            [
                {"Transaction_ID": "TXN001", "Transaction_Type": "IN"},
                {"Transaction_ID": "TXN002", "Transaction_Type": "OUT"},
                {"Transaction_ID": "TXN003", "Transaction_Type": "IN"},
                {"Transaction_ID": "TXN004", "Transaction_Type": "OUT"},
            ]
        )
        transaction_details = pd.DataFrame(
            [
                {"Transaction_ID": "TXN001", "Item_ID": "ITEM-001", "Quantity": 20},
                {"Transaction_ID": "TXN002", "Item_ID": "ITEM-001", "Quantity": 7},
                {"Transaction_ID": "TXN003", "Item_ID": "ITEM-002", "Quantity": 100},
                {"Transaction_ID": "TXN004", "Item_ID": "ITEM-001", "Quantity": 3},
            ]
        )

        available_stock = calculate_available_stock(
            "ITEM-001",
            transactions=transactions,
            transaction_details=transaction_details,
        )

        self.assertEqual(available_stock, 10)

    def test_calculate_available_stock_ignores_non_in_out_transactions(self):
        transactions = pd.DataFrame(
            [
                {"Transaction_ID": "TXN001", "Transaction_Type": "IN"},
                {"Transaction_ID": "TXN002", "Transaction_Type": "ADJUSTMENT"},
            ]
        )
        transaction_details = pd.DataFrame(
            [
                {"Transaction_ID": "TXN001", "Item_ID": "ITEM-001", "Quantity": 5},
                {"Transaction_ID": "TXN002", "Item_ID": "ITEM-001", "Quantity": 50},
            ]
        )

        available_stock = calculate_available_stock(
            "ITEM-001",
            transactions=transactions,
            transaction_details=transaction_details,
        )

        self.assertEqual(available_stock, 5)


if __name__ == "__main__":
    unittest.main()
