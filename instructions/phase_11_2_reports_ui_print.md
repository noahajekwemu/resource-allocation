Phase 11.2 – Add reports page and executive print view.

Goal:
Create a secure reports page served by Render with printable executive views and CSV export links.

Files to update/create:
- forms/reports.html
- forms/print_executive_summary.html
- forms/approve_requisition.html
- forms/receive_stock.html
- forms/issue_stock.html
- forms/requisition_form.html
- forms/user_management.html
- scripts/form_api.py
- dashboard/index.html
- dashboard/js/dashboard.js
- dashboard/css/styles.css
- tests/test_role_permissions.py

Requirements:

1. Create:
forms/reports.html

Page title:
Reports and Exports

2. Create:
forms/print_executive_summary.html

Page title:
Executive Summary Report

3. Protect pages:

/forms/reports.html
Allowed roles:
- Admin
- Viewer
- Approver
- Store_Officer
- School_User

/forms/print_executive_summary.html
Allowed roles:
- Admin
- Viewer
- Approver
- Store_Officer

School_User should receive 403 for executive print page.

4. Add Reports link to the public dashboard navigation:

Reports:
https://resource-allocation-api.onrender.com/forms/reports.html

5. Add Reports link to all secured form page navigation:
- Dashboard
- Reports
- Logout

6. reports.html should show report cards:

- Executive Summary
- Stock Report
- Requisition Report
- Fulfillment Report
- Audit Report

7. Each card should have:
- View JSON
- Download CSV
- Print View where applicable

8. Hide or disable cards the current role cannot use.

If role detection is not available client-side, show links but rely on backend 403 protection.

9. reports.html should fetch:
/api/reports/executive-summary

and display:
- total schools
- total warehouses
- total requisitions
- pending requisitions
- approved requisitions
- fulfilled requisitions
- total stock received
- total stock issued
- fulfillment rate

10. print_executive_summary.html should:
- Fetch /api/reports/executive-summary
- Render a clean printable report
- Include title:
  Benue SUBEB Resource Allocation System
  Executive Summary Report
- Include generated date
- Include KPI table
- Include summary sections
- Include Print button using window.print()

11. Add print CSS:
- White background
- Hide navigation/buttons when printing
- Professional spacing
- Page-friendly layout

12. Keep Benue SUBEB branding.

13. Do not expose Password_Hash.

14. Do not edit docs/ directly.

15. Preserve dashboard data loading from data.json.

16. Ensure python -m pytest passes.
