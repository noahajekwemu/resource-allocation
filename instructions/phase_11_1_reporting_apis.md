Phase 11.1 – Add reporting APIs and CSV exports.

Goal:
Add secure reporting endpoints for stock, requisitions, fulfillment, audit trail, and executive summary.

Files to update/create:
- scripts/report_utils.py
- scripts/form_api.py
- tests/test_report_utils.py
- tests/test_role_permissions.py
- requirements.txt if needed

Requirements:

1. Create scripts/report_utils.py.

2. Build reporting functions using existing Google Sheets worksheets:
- Items
- Schools
- Warehouses
- Transactions
- Transaction_Details
- Requisitions
- Requisition_Details
- Users
- Audit_Log

3. Add report functions:

A. get_executive_summary()
Return:
- total_items
- total_schools
- total_warehouses
- total_requisitions
- approved_requisitions
- rejected_requisitions
- fulfilled_requisitions
- partially_fulfilled_requisitions
- pending_requisitions
- total_stock_received
- total_stock_issued
- fulfillment_rate_percent
- low_stock_items if available
- generated_at

B. get_stock_report()
Return rows with:
- Item_ID
- Item_Name
- Category
- Warehouse_ID
- Warehouse_Name
- Quantity_Received
- Quantity_Issued
- Current_Stock

C. get_requisition_report()
Return rows with:
- Requisition_ID
- School_ID
- School_Name
- Requested_By
- Status
- Created_At
- Approved_By
- Approved_At
- Total_Requested
- Total_Approved
- Total_Fulfilled
- Fulfillment_Percent

D. get_fulfillment_report()
Return rows with:
- Requisition_ID
- School_ID
- School_Name
- Item_ID
- Item_Name
- Quantity_Requested
- Quantity_Approved
- Quantity_Fulfilled
- Outstanding_Quantity
- Status

E. get_audit_report()
Return rows from Audit_Log with filters where practical.

4. Add CSV export utility:
records_to_csv_response(records, filename)

5. Add protected API endpoints in scripts/form_api.py:

GET /api/reports/executive-summary
GET /api/reports/stock
GET /api/reports/requisitions
GET /api/reports/fulfillment
GET /api/reports/audit

6. Each report endpoint should support:
?format=json
?format=csv

Default:
json

Example:
GET /api/reports/stock?format=csv

7. Role permissions:

Admin:
- all reports
- all CSV exports

Viewer:
- executive-summary
- stock
- requisitions
- fulfillment
- no audit report unless Admin

Approver:
- executive-summary
- requisitions
- fulfillment

Store_Officer:
- executive-summary
- stock
- fulfillment

School_User:
- requisitions and fulfillment only for own School_ID
- no stock report
- no audit report

8. Protect audit report:
Only Admin can access:
/api/reports/audit

9. Do not expose Password_Hash in any report.

10. Add audit logging for report exports:
- EXPORT_REPORT
Include report name and format.

11. Add tests for:
- executive summary structure
- stock report structure
- requisition report structure
- CSV generation
- Admin can access all reports
- Viewer cannot access audit report
- School_User cannot access stock report
- School_User reports are filtered by own School_ID
- Password_Hash is never exposed
- CSV export has text/csv content type

12. Preserve all existing routes and role checks.

13. Ensure python -m pytest passes.
