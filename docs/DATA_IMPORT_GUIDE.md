# SUBEB Data Import Guide

The importer validates CSV or Excel data before it changes Google Sheets. It cannot import into `Users` or `Audit_Log`, and it never reads or displays `Password_Hash`.

## Prepare the file

Use the files in `import_templates/` as starting points. CSV files contain one target sheet. Excel workbooks may include multiple supported tabs; companion tabs are used to validate foreign keys in the same import batch.

Keep identifiers stable and unique. Use whole, non-negative numbers for quantity fields and ISO dates such as `2026-06-22`. Do not rename required headers.

| Target | Required columns |
| --- | --- |
| Items | `Item_ID`, `Item_Name`, `Category` |
| Schools | `School_ID`, `School_Name`, `LGA`, `Zone`, `School_Type`, `Status` |
| Warehouses | `Warehouse_ID`, `Warehouse_Name`, `LGA`, `Zone`, `Status` |
| Transactions | `Transaction_ID`, `Date`, `Type`, `Warehouse_ID`, `School_ID`, `Source`, `Requisition_ID`, `Remarks` |
| Transaction_Details | `Transaction_ID`, `Item_ID`, `Quantity`, `Condition` |
| Requisitions | `Requisition_ID`, `Date`, `School_ID`, `Requested_By`, `Status`, `Approved_By`, `Approved_At`, `Remarks` |
| Requisition_Details | `Requisition_ID`, `Item_ID`, `Quantity_Requested`, `Quantity_Approved`, `Quantity_Fulfilled` |

`Transaction_Details` and `Requisition_Details` use the parent ID plus `Item_ID` as their logical unique key.

## Validate first

Always run a dry run. It reads current Google Sheets data for duplicate and foreign-key checks but makes no changes.

```powershell
python -m scripts.import_data --file import_templates\Items.csv --sheet Items --dry-run
python -m scripts.import_data --file C:\data\subeb.xlsx --sheet Schools --mode upsert --dry-run
```

The command prints totals, planned appends and updates, validation errors, and the path to a timestamped JSON report in `import_reports/`.

## Back up and commit

Create a production backup immediately before a valid import:

```powershell
python -m scripts.backup_google_sheets
```

Commit only after reviewing the dry-run report:

```powershell
python -m scripts.import_data --file C:\data\Schools.csv --sheet Schools --mode append --commit
```

`--mode append` rejects keys already in the target worksheet. `--mode upsert` updates matching keys and appends new keys. All validation finishes before target data is written. A committed attempt records the `IMPORT_DATA` action in `Audit_Log`; it does not overwrite audit history.

## Common validation errors

- **Missing required columns:** restore the exact header from the matching template.
- **Duplicate import key:** remove repeated IDs or repeated parent-ID/item-ID pairs.
- **Existing key cannot be appended:** use a new ID or deliberately select `--mode upsert`.
- **Invalid quantity:** provide a whole number of zero or greater.
- **Unknown ID:** import the referenced school, item, warehouse, transaction, or requisition first, or include its tab in the Excel workbook.
- **Invalid type or status:** transactions allow `IN` and `OUT`; requisitions allow `Pending`, `Approved`, `Rejected`, `Partially Fulfilled`, and `Fulfilled`.
- **Unparseable date:** use an unambiguous date such as `YYYY-MM-DD`.

## Refresh the dashboard

After all related imports are committed, regenerate the public dashboard data:

```powershell
python -m scripts.calculate_metrics
```

Review `dashboard/data.json`, then publish through the project’s normal GitHub Actions workflow. Do not manually copy dashboard files into `docs/`.
