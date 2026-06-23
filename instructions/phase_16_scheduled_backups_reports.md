Phase 16 – Scheduled backups and monthly report automation.

Goal:
Automate Google Sheets backups and monthly executive report generation using GitHub Actions.

Files to create/update:
- .github/workflows/scheduled_backup.yml
- .github/workflows/monthly_report.yml
- scripts/backup_google_sheets.py
- scripts/generate_monthly_report.py
- scripts/report_utils.py
- docs/BACKUP_AND_RECOVERY.md
- docs/MONTHLY_REPORTS.md
- tests/test_backup_google_sheets.py
- tests/test_report_utils.py
- tests/test_monthly_report.py
- .gitignore
- requirements.txt if needed

Requirements:

1. Create scheduled backup workflow:
.github/workflows/scheduled_backup.yml

It should:
- run daily
- support manual workflow_dispatch
- install requirements
- use GOOGLE_CREDENTIALS GitHub secret
- run python -m scripts.backup_google_sheets
- upload backups as workflow artifact

2. Create monthly report workflow:
.github/workflows/monthly_report.yml

It should:
- run on the first day of every month
- support manual workflow_dispatch
- install requirements
- use GOOGLE_CREDENTIALS GitHub secret
- run python -m scripts.generate_monthly_report
- upload monthly report as workflow artifact

3. Create scripts/generate_monthly_report.py.

It should generate:
- reports/monthly/YYYY-MM/executive_summary.json
- reports/monthly/YYYY-MM/executive_summary.csv
- reports/monthly/YYYY-MM/executive_summary.html

Report should include:
- total stock received
- total stock issued
- requisitions by status
- fulfillment rate
- top requested items
- low stock items
- generated_at

4. Ensure backups/ and reports/monthly/ are in .gitignore.

5. Do not commit generated backup/report output.

6. Do not expose credentials in logs.

7. Update docs:
- BACKUP_AND_RECOVERY.md
- MONTHLY_REPORTS.md

8. Add tests where practical.

9. Ensure python -m pytest passes.