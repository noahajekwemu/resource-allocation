Phase 10.3 – Google Sheets backup and recovery.

Goal:
Add a safe backup/export system for the Educational_Supplies_Logs Google Sheet.

Files to update/create:
- scripts/backup_google_sheets.py
- scripts/db_connector.py if needed
- .gitignore
- docs or README backup section if README exists
- tests/test_backup_google_sheets.py

Requirements:

1. Create script:
scripts/backup_google_sheets.py

2. Script should connect to the existing Google Sheet:
Educational_Supplies_Logs

Using existing db_connector authentication.

3. Export all relevant worksheets:
- Items
- Schools
- Warehouses
- Transactions
- Transaction_Details
- Requisitions
- Requisition_Details
- Users
- Audit_Log

4. Save backups under:
backups/

Create timestamped folder:
backups/YYYYMMDD_HHMMSS/

5. For each worksheet, export:
- CSV file
- JSON file

Example:
backups/20260621_120000/Items.csv
backups/20260621_120000/Items.json

6. Create backup manifest:
backup_manifest.json

Include:
- backup_timestamp
- spreadsheet_name
- worksheets_exported
- row_counts
- generated_by script name

7. Add backups/ to .gitignore.

Do not commit backup data to GitHub.

8. Add command-line usage:

python -m scripts.backup_google_sheets

9. Add basic restore guidance in a documentation file:
docs/BACKUP_AND_RECOVERY.md

Include:
- how to run backup
- where files are saved
- why backups should not be committed
- how to manually restore a worksheet from CSV into Google Sheets
- recommended backup frequency

10. Add tests where practical:
- backup folder path generation
- CSV/JSON export formatting using mocked worksheet data
- manifest generation

11. Do not modify production data during backup.

12. Ensure python -m pytest passes.
