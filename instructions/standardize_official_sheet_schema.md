Standardize code to the official Google Sheets schema.

Official schema:

Items:
Item_ID
Item_Name
Category
Unit
Minimum_Stock
Status

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
Transaction_Date
Transaction_Type
Warehouse_ID
Destination_School_ID
Source
Requisition_ID
Remarks

Transaction_Details:
Detail_ID
Transaction_ID
Item_ID
Quantity
Condition

Requisitions:
Requisition_ID
School_ID
Request_Date
Requested_By
Status
Approved_By
Approval_Date
Remarks

Requisition_Details:
Req_Detail_ID
Requisition_ID
Item_ID
Quantity_Requested
Quantity_Approved
Quantity_Fulfilled

Users:
User_ID
Full_Name
Email
Role
School_ID
Password_Hash
Active
Created_At

Audit_Log:
Audit_ID
Timestamp
User_ID
User_Email
Role
Action
Entity_Type
Entity_ID
Before_State
After_State
IPAddress
Status
Remarks

Goal:
Update the application to use this official schema consistently while preserving backward compatibility with older sheet headers where practical.

Files to update:
- scripts/calculate_metrics.py
- scripts/form_api.py
- scripts/inventory_utils.py
- scripts/requisition_utils.py if present
- scripts/report_utils.py if present
- scripts/import_utils.py if present
- scripts/import_data.py if present
- scripts/seed_sample_data.py if present
- tests/test_calculate_metrics.py
- tests/test_requisition_validation.py
- tests/test_requisition_fulfillment.py
- tests/test_report_utils.py if present
- tests/test_import_utils.py if present
- tests/test_seed_sample_data.py if present

Requirements:

1. Use the official schema names as the primary column names.

2. For Transactions, use:
Transaction_Date
Transaction_Type
Destination_School_ID

Do not require generic names:
Date
Type
School_ID

3. For Requisitions, use:
Request_Date
Approval_Date
Requested_By

Do not require generic names:
Date
Approved_At

4. Transaction model:
Use the header-detail model as the official model:
- Transactions stores transaction header data.
- Transaction_Details stores Item_ID, Quantity, Condition.

5. Backward compatibility:
If old flat Transactions rows still contain Item_ID and Quantity directly, calculate_metrics.py should still read them as a fallback when matching Transaction_Details rows are missing.

6. Dashboard metrics must generate data from the official schema.

7. dashboard/data.json must always include these top-level sections:
inventory
requisitions
distribution
accountability
stock_levels
requisition_status_breakdown
requested_vs_approved_vs_fulfilled
top_requested_items
requests_by_lga
recent_inventory_movements
recent_requisitions
fulfillment_summary
last_updated

8. If optional columns are missing or blank, do not crash.
Optional columns include:
Unit
Minimum_Stock
Status
Zone
School_Type
Warehouse LGA
Warehouse Zone
Condition
Requested_By

9. For low-stock calculations:
Use Items.Minimum_Stock when available.
If Minimum_Stock is missing or blank, use a default threshold of 10.

10. Form API write behavior:
- Receive stock should create one row in Transactions and one or more rows in Transaction_Details.
- Issue stock should create one row in Transactions and one or more rows in Transaction_Details.
- Requisition submission should write to Requisitions and Requisition_Details using official columns.
- Approval should update Requisitions.Approved_By and Requisitions.Approval_Date.
- Fulfillment should update Requisition_Details.Quantity_Fulfilled.

11. Reports:
Reports should use the official schema names.

12. Import system:
Import templates and validation should use the official schema names.

13. Audit_Log:
Do not change audit schema.
Do not expose Password_Hash.

14. Add or update tests for:
- official Transactions schema
- official Transaction_Details schema
- official Requisitions schema
- official Requisition_Details schema
- flat transaction fallback
- missing optional fields
- low-stock threshold from Minimum_Stock
- dashboard data sections always present

15. Ensure python -m pytest passes.