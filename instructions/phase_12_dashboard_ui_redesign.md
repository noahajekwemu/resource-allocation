Phase 12 – Redesign public dashboard UI using SUBEB executive dashboard layout.

Goal:
Redesign the GitHub Pages dashboard to visually resemble the provided SUBEB sample dashboard screenshot while preserving the current resource allocation data, charts, and accountability metrics.

Files to update:
- dashboard/index.html
- dashboard/css/styles.css
- dashboard/js/dashboard.js
- dashboard/js/charts.js if needed

Important:
Do not edit docs/ directly.
GitHub Actions will copy dashboard/ to docs/.

Visual direction:
Use the first screenshot as design inspiration:
- White main canvas
- Benue SUBEB logo at top left
- Top KPI cards in light blue
- Dark navy/blue text
- Left vertical navigation menu with stacked buttons
- Main chart grid in the center
- Optional right filter panel
- Clean executive dashboard style
- Professional spacing
- Better chart visibility

Dashboard header:
- Show Benue SUBEB logo
- Title:
  Benue State Universal Basic Education Board
- Subtitle:
  Educational Resource Allocation & Accountability Dashboard
- Show last updated date/time

Top KPI cards:
Show these using existing dashboard/data.json where possible:
- Total Inventory Items
- Total Available Stock
- Inventory Accuracy
- Low Stock Items
- Out of Stock Items
- Pending Requisitions
- Approved Requisitions
- Fulfilled Requisitions
- Total Schools
- Total Warehouses

Left navigation menu:
Add stacked buttons:
- Summary
- Inventory
- Requisitions
- Distribution
- Reports
- Secure Portal
- Submit Requisition
- Receive Stock
- Issue Stock
- Approve Requests

External Render links:
Use:
https://resource-allocation-api.onrender.com

Secure Portal:
https://resource-allocation-api.onrender.com/login

Reports:
https://resource-allocation-api.onrender.com/forms/reports.html

Submit Requisition:
https://resource-allocation-api.onrender.com/forms/requisition_form.html

Receive Stock:
https://resource-allocation-api.onrender.com/forms/receive_stock.html

Issue Stock:
https://resource-allocation-api.onrender.com/forms/issue_stock.html

Approve Requests:
https://resource-allocation-api.onrender.com/forms/approve_requisition.html

Main chart layout:
Show charts in panels:
- Requisition Status Breakdown
- Requested vs Approved vs Fulfilled Quantities
- Top Requested Items
- Requests by LGA
- Stock Levels by Item
- Inventory Movement Trend if data is available
- Distribution by School/LGA if data is available

Right filter panel:
Create a visual filter panel similar to the screenshot:
- Zone
- LGA
- Status
- Item Category

If full filtering is complex, implement simple client-side filtering where practical.
If not practical, make it a visual panel prepared for future filtering.

Tables:
Keep:
- Recent Inventory Movements
- Recent Requisitions
- Fulfillment Summary

UX:
- No chart should show blank if there is data.
- If there is no data, show a neat message.
- Mobile responsive layout.
- Preserve Benue SUBEB colors.
- Keep footer.

API status:
Keep API status on public dashboard only.
Show:
- API Online
- API Offline

Do not break:
- loading from data.json
- Chart.js rendering
- GitHub Pages hosting
- Render links
- existing tests

Ensure python -m pytest passes.