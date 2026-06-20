Fix pytest test collection errors.

Problem:
tests/test_receive_stock.py executes submit_receive_stock at import time and causes pytest collection failure:
ValueError: At least one item row is required.

Requirements:
1. Refactor tests/test_receive_stock.py so it contains proper pytest functions.
2. Do not call submit_receive_stock at module import time.
3. Either:
   - convert it to a valid pytest test with a complete payload containing items, or
   - mark it as an integration test using pytest.mark.integration.
4. Apply the same cleanup to:
   - tests/test_issue_stock.py
   - tests/test_stock.py
   - tests/test_deburg.py
5. No test should write to Google Sheets unless explicitly marked integration.
6. Unit tests should use mocks where possible.
7. Ensure python -m pytest can collect all tests without errors.