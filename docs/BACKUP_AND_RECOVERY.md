# Backup and Recovery

## Scheduled Backups

The `Scheduled Google Sheets Backup` GitHub Actions workflow runs daily and can also be started manually from the Actions tab.

Required secret:

- `GOOGLE_CREDENTIALS`: the Google service account JSON used by the application.

The workflow runs:

```bash
python -m scripts.backup_google_sheets
```

It exports each configured worksheet to CSV and JSON under `backups/YYYYMMDD_HHMMSS/`, adds a `backup_manifest.json`, and uploads the `backups/` directory as a workflow artifact.

## Recovery

1. Open the latest successful `Scheduled Google Sheets Backup` workflow run.
2. Download the `google-sheets-backup` artifact.
3. Inspect `backup_manifest.json` to confirm the backup timestamp, spreadsheet name, worksheets, and row counts.
4. Restore the needed worksheet CSV files into Google Sheets manually or through an approved import process.

Backups may contain operational data, so they are ignored by git and should not be committed.
