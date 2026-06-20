from unittest.mock import patch

from scripts.form_api import get_available_stock


def test_get_available_stock_delegates_to_inventory_calculation():
    with patch("scripts.form_api.calculate_available_stock", return_value=80) as calculate:
        result = get_available_stock("ITEM-001")

    assert result == 80
    calculate.assert_called_once_with("ITEM-001")
