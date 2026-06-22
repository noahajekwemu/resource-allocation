Phase 13.1 – Real data import from Excel/CSV.

Goal:
Create a safe import engine for loading real SUBEB data from Excel or CSV files into the Google Sheets database.

Files to create/update:
- scripts/import_data.py
- scripts/import_utils.py
- scripts/db_connector.py if needed
- scripts/backup_google_sheets.py if needed
- import_templates/Items.csv
- import_templates/Schools.csv
- import_templates/Warehouses.csv
- import_templates/Transactions.csv
- import_templates/Transaction_Details.csv
- import_templates/Requisitions.csv
- import_templates/Requisition_Details.csv
- docs/DATA_IMPORT_GUIDE.md
- tests/test_import_utils.py
- tests/test_import_data.py
- requirements.txt if needed

Important safety rules:
1. Never modify Users through this importer.
2. Never overwrite Audit_Log.
3. Never expose Password_Hash.
4. Always support dry-run mode.
5. Do not write to Google Sheets unless --commit is provided.
6. Before commit import, recommend backup.
7. Validate data before writing anything.
8. If validation fails, do not write partial data.

Supported file types:
- .csv
- .xlsx

Import command examples:

Dry run:
python -m scripts.import_data --file path/to/import.xlsx --sheet Items --dry-run

Commit:
python -m scripts.import_data --file path/to/import.xlsx --sheet Items --commit

CSV example:
python -m scripts.import_data --file path/to/Schools.csv --sheet Schools --dry-run

Supported target sheets:
- Items
- Schools
- Warehouses
- Transactions
- Transaction_Details
- Requisitions
- Requisition_Details

Required columns:

Items:
Item_ID
Item_Name
Category

Schools:
School_ID
School_Name
LGA
Zone
School_Type
Status

Warehouses:
Warehouse_ID
Warehouse_Name
LGA
Zone
Status

Transactions:
Transaction_ID
Date
Type
Warehouse_ID
School_ID
Source
Requisition_ID
Remarks

Transaction_Details:
Transaction_ID
Item_ID
Quantity
Condition

Requisitions:
Requisition_ID
Date
School_ID
Requested_By
Status
Approved_By
Approved_At
Remarks

Requisition_Details:
Requisition_ID
Item_ID
Quantity_Requested
Quantity_Approved
Quantity_Fulfilled

Validation requirements:
1. Required columns must exist.
2. IDs must not be blank.
3. Duplicate IDs in import file must be rejected.
4. Duplicate existing IDs in Google Sheets should be handled by mode:
   --mode append: reject duplicates
   --mode upsert: update matching rows and append new rows
5. Numeric columns must be valid integers:
   Quantity
   Quantity_Requested
   Quantity_Approved
   Quantity_Fulfilled
6. Quantity values cannot be negative.
7. Date fields must be parseable.
8. Transaction Type must be:
   IN
   OUT
9. Requisition Status must be one of:
   Pending
   Approved
   Rejected
   Partially Fulfilled
   Fulfilled
10. Foreign key validation:
   Transaction_Details.Transaction_ID must exist in Transactions or import batch.
   Transaction_Details.Item_ID must exist in Items or import batch.
   Transactions.Warehouse_ID must exist in Warehouses or import batch.
   Transactions.School_ID must exist in Schools or import batch, except IN transactions where School_ID may be blank.
   Requisitions.School_ID must exist in Schools or import batch.
   Requisition_Details.Requisition_ID must exist in Requisitions or import batch.
   Requisition_Details.Item_ID must exist in Items or import batch.

Import report:
After dry-run or commit, print:
- target sheet
- file path
- mode
- total rows read
- valid rows
- invalid rows
- rows to append
- rows to update
- validation errors
- commit status

Create output folder:
import_reports/

Write timestamped report:
import_reports/import_report_YYYYMMDD_HHMMSS.json

Add import_reports/ to .gitignore.

Audit logging:
If import is committed, write Audit_Log action:
IMPORT_DATA

Include:
- target sheet
- imported row count
- mode
- file name
- success/failure

Templates:
Create import_templates/*.csv files with correct headers and 2 sample rows each.

Documentation:
Create docs/DATA_IMPORT_GUIDE.md with:
- how to prepare Excel/CSV files
- required columns
- dry-run command
- commit command
- append vs upsert
- backup before import
- common validation errors
- how to regenerate dashboard after import

Tests:
Add tests for:
- CSV loading
- XLSX loading if practical
- missing required columns
- duplicate IDs
- invalid quantity
- invalid status
- foreign key validation
- dry-run does not write
- append duplicate rejection
- upsert behavior
- import report generation

Ensure python -m pytest passes.
