Fix dashboard/data.json invalid JSON caused by NaN values.

Problem:
The dashboard fails with browser console error:
Unexpected token 'N' ... "Date": NaN ... is not valid JSON

Cause:
scripts/calculate_metrics.py is writing NaN, Infinity, -Infinity, NaT, or pandas missing values into dashboard/data.json.

Requirements:

1. Update scripts/calculate_metrics.py.

2. Before writing dashboard/data.json, sanitize the full dashboard data object recursively.

3. Convert all invalid JSON values:
- float('nan') -> None
- pandas NaN -> None
- numpy NaN -> None
- Infinity -> None
- -Infinity -> None
- pandas NaT -> None
- numpy datetime NaT -> None

4. Convert datetime/date/timestamp values to strings.

5. Ensure json.dump uses:
allow_nan=False

This is important. If any NaN remains, json.dump should fail during script execution instead of creating invalid JSON.

6. Add a helper function such as:
sanitize_for_json(value)

It should handle:
- dict
- list
- tuple
- pandas Series/DataFrame records if needed
- int/float/string/bool/None
- datetime/date
- pandas Timestamp
- numpy scalar values

7. Apply sanitization to dashboard_data before writing.

8. Add tests in tests/test_calculate_metrics.py for:
- NaN becomes None
- Infinity becomes None
- pandas NaT becomes None
- nested dictionaries/lists are sanitized
- generated JSON can be parsed by json.loads
- json.dump uses allow_nan=False or equivalent behavior

9. Preserve existing dashboard metrics.

10. Ensure python -m pytest passes.