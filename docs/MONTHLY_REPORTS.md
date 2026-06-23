# Monthly Reports

## Automated Report

The `Monthly Executive Report` GitHub Actions workflow runs on the first day of every month and can also be started manually from the Actions tab.

Required secret:

- `GOOGLE_CREDENTIALS`: the Google service account JSON used by the application.

The workflow runs:

```bash
python -m scripts.generate_monthly_report
```

By default, the report covers the previous completed month. Manual runs can provide `report_month` in `YYYY-MM` format.

## Output

Each run creates:

- `reports/monthly/YYYY-MM/executive_summary.json`
- `reports/monthly/YYYY-MM/executive_summary.csv`
- `reports/monthly/YYYY-MM/executive_summary.html`

The summary includes total stock received, total stock issued, requisitions by status, fulfillment rate, top requested items, low stock items, and `generated_at`.

Monthly report output is uploaded as a workflow artifact and ignored by git.
