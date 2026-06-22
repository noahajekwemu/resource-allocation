Phase 11.5 – Add richer sample data for dashboard charts.

Goal:
Create a safe sample data seeding script that populates Google Sheets with enough realistic demo data for dashboard charts, requisition charts, fulfillment charts, and reports.

Files to create/update:
- scripts/seed_sample_data.py
- scripts/db_connector.py if needed
- scripts/calculate_metrics.py if needed
- tests/test_seed_sample_data.py if practical
- instructions/phase_11_5_seed_sample_data.md

Important safety rules:
1. Do not delete or overwrite Users.
2. Do not delete or overwrite Audit_Log.
3. Do not expose Password_Hash.
4. Do not change login users.
5. The script must be explicit. It should not run automatically during app startup.
6. Add a clear confirmation flag before writing data.

Command should be:

python -m scripts.seed_sample_data --append-demo

Optional dry run:

python -m scripts.seed_sample_data --dry-run

Worksheets to populate:

Items:
Create at least 12 items:
- Mathematics Textbook
- English Textbook
- Basic Science Textbook
- Social Studies Textbook
- Exercise Book
- Chalk Box
- Classroom Chair
- Classroom Desk
- Teacher Table
- Whiteboard
- School Bag
- First Aid Box

Schools:
Create at least 20 schools across LGAs:
- Makurdi
- Gboko
- Otukpo
- Katsina-Ala
- Vandeikya
- Kwande
- Guma
- Logo
- Oju
- Ogbadibo

Include realistic columns based on existing Schools worksheet.
Use School_ID values like SCH001, SCH002, etc.
Include School_Name, LGA, Zone, School_Type, Status where columns exist.

Warehouses:
Create at least 5 warehouses:
- Makurdi Central Store
- Gboko Zonal Store
- Otukpo Zonal Store
- Katsina-Ala Zonal Store
- Vandeikya Zonal Store

Transactions:
Create at least 25 transactions:
- IN transactions for stock received
- OUT transactions for stock issued to schools
Use dates across several weeks.
Use Transaction_ID values like TXN-2026-000101.
Use Warehouse_ID and School_ID references that exist.

Transaction_Details:
Create matching detail rows for every transaction.
Use realistic quantities.
Make sure some items have:
- healthy stock
- low stock
- out of stock
This will make inventory charts meaningful.

Requisitions:
Create at least 15 requisitions with different statuses:
- Pending
- Approved
- Rejected
- Partially Fulfilled
- Fulfilled

Requisition_Details:
Create detail rows with:
- Quantity_Requested
- Quantity_Approved
- Quantity_Fulfilled

Make sure at least:
- 5 requisitions are fulfilled
- 3 are partially fulfilled
- 3 are pending
- 2 are approved but not fulfilled
- 2 are rejected

Dashboard chart requirements:
After seeding, running:

python -m scripts.calculate_metrics

should produce dashboard/data.json with data for:
- requisition status breakdown
- requested vs approved vs fulfilled quantities
- top requested items
- requests by LGA
- recent requisitions
- fulfillment summary
- recent inventory movements
- stock levels
- low stock and out-of-stock items

Add print output showing:
- number of rows added per worksheet
- warning that Users and Audit_Log were not modified

Ensure python -m pytest passes.