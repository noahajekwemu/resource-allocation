# Backup and Recovery

The backup utility creates a read-only export of the `Educational_Supplies_Logs`
Google Sheet. It does not update or delete production data.

## Create a backup

From the repository root, configure the same Google credentials used by the API,
then run:

```powershell
python -m scripts.backup_google_sheets
```

The command creates `backups/YYYYMMDD_HHMMSS/`. Each configured worksheet is
stored as both CSV and JSON, alongside `backup_manifest.json`. The manifest lists
the spreadsheet, timestamp, exported worksheets, and row counts.

## Protect backup data

Backups can contain user password hashes, audit records, and operational data.
The `backups/` directory is ignored by Git and must not be committed to GitHub.
Copy completed backups to access-controlled, encrypted storage and apply an
appropriate retention policy.

## Restore a worksheet manually

1. Confirm the backup manifest identifies the expected spreadsheet and worksheet.
2. Open the target Google Sheet and make a fresh backup before changing anything.
3. Open or create the worksheet that needs recovery.
4. In Google Sheets, select **File > Import > Upload** and choose the worksheet's
   CSV file from the timestamped backup directory.
5. Select **Replace current sheet** only after confirming the target worksheet.
6. Verify headers, row count, IDs, formulas, and several representative records.
7. Test the application workflow that uses the restored worksheet.

Restore one worksheet at a time. The JSON files are intended for independent
verification or scripted recovery preparation; this project does not perform
automatic production restores.

## Recommended frequency

Run a backup daily and before schema changes, bulk imports, user administration,
or other high-impact maintenance. Keep multiple dated copies so an unnoticed data
issue does not overwrite the only usable recovery point.
