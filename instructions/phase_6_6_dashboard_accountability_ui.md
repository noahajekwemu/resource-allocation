Phase 6.6 – Dashboard Accountability UI Enhancement

Update the public Benue SUBEB dashboard to display the new accountability metrics from dashboard/data.json.

IMPORTANT:
Do not edit docs/ directly.
Only edit files inside dashboard/.
The GitHub Actions workflow will copy dashboard/ into docs/.

Files to update:

- dashboard/index.html
- dashboard/css/styles.css
- dashboard/js/dashboard.js
- dashboard/js/charts.js

DATA SOURCE:

Read:

dashboard/data.json

using fetch().

The dashboard/data.json may now contain sections such as:

{
  "generated_at": "",
  "kpis": {},
  "requisitions": {},
  "fulfillment": {},
  "charts": {},
  "tables": {},
  "schools": [],
  "lgas": [],
  "warehouses": [],
  "monthly_movements": []
}

The UI must gracefully handle missing fields or empty arrays.

BRANDING:

Maintain Benue SUBEB branding.

Use the existing logo:

dashboard/assets/Benue-SUBEB.jpg

Use this color palette:

:root {
  --subeb-blue: #1E9BEA;
  --subeb-blue-dark: #0B6FB8;
  --subeb-blue-light: #EAF6FF;
  --subeb-red: #C62828;
  --subeb-white: #FFFFFF;
  --subeb-text: #1F2937;
}

Do not introduce unrelated colors.

Use red only for alerts, rejected requests, damaged items, low stock, or exceptions.

DASHBOARD SECTIONS:

1. Header

Display:
- Benue SUBEB logo
- Benue State Universal Basic Education Board
- Educational Resource Allocation & Accountability Dashboard
- Last updated timestamp from generated_at

2. Executive KPI Cards

Render cards for:

Inventory:
- Total Inventory Items
- Total Available Stock
- Inventory Accuracy
- Low Stock Items
- Out of Stock Items
- Damaged Items

Requisitions:
- Total Requisitions
- Pending Requisitions
- Approved Requisitions
- Partially Fulfilled Requisitions
- Fulfilled Requisitions
- Rejected Requisitions

Fulfillment:
- Fulfillment Rate
- Average Fulfillment Days
- Schools Served
- Total Schools
- Total Warehouses

Use defensive lookups so the dashboard does not crash if a metric is missing.

3. Requisition Accountability Charts

Using Chart.js, render:

- Requisition Status Breakdown
- Requested vs Approved vs Fulfilled Quantities
- Top Requested Items
- Requests by LGA

Possible JSON locations may include:

data.charts.requisition_status_distribution
data.charts.requested_vs_approved_vs_fulfilled
data.charts.top_requested_items
data.charts.requests_by_lga

If a dataset is missing, show a user-friendly empty state.

4. Distribution Accountability Charts

Render:

- Distribution by LGA
- Distribution by School Type
- Top Schools
- Bottom Schools
- Top Distributed Items

Possible JSON locations may include:

data.charts.distribution_by_lga
data.charts.distribution_by_school_type
data.charts.top_schools
data.charts.bottom_schools
data.charts.top_distributed_items

5. Inventory Charts

Render:

- Inventory by Category
- Stock Source Analysis
- Monthly Stock Movements

Possible JSON locations may include:

data.charts.inventory_by_category
data.charts.stock_source_analysis
data.monthly_movements
data.charts.monthly_stock_movements

Monthly Stock Movements should support IN and OUT series.

6. Tables

Render tables for:

- Stock Levels
- Low Stock Alerts
- Recent Inventory Movements
- Recent Requisitions
- Fulfillment Summary

Possible JSON locations may include:

data.tables.stock_levels
data.tables.low_stock_alerts
data.tables.recent_movements
data.tables.recent_requisitions
data.tables.fulfillment_summary

TABLE REQUIREMENTS:

- Responsive on mobile
- Show "No records available" for empty data
- Avoid horizontal overflow where possible
- Format numbers with commas
- Format percentages with % symbol
- Format dates readably where possible

JAVASCRIPT REQUIREMENTS:

- Use vanilla JavaScript only.
- Use Chart.js only for charts.
- Do not use React, Vue, Angular, Bootstrap, Tailwind, or build tools.
- Do not perform business calculations in the browser.
- Only format and render values that already exist in data.json.
- Add helper functions:
  - getValue()
  - formatNumber()
  - formatPercent()
  - renderKpiCard()
  - renderTable()
  - renderEmptyState()
  - createBarChart()
  - createDoughnutChart()
  - createLineChart()

ERROR HANDLING:

Add:
- Loading indicator
- Error state if data.json cannot be loaded
- Empty state for missing chart/table datasets
- Console warnings for missing optional datasets
- No uncaught JavaScript errors

RESPONSIVE DESIGN:

The dashboard must work on:

- Desktop
- Tablet
- Mobile

Use CSS grid/flexbox.

DESIGN STYLE:

Professional government accountability portal.

Use:
- White cards
- Blue headers
- Subtle shadows
- Clear typography
- Strong visual hierarchy
- Accessible contrast
- Print-friendly layout

FOOTER:

Display:

Benue State Universal Basic Education Board
Educational Resource Allocation & Accountability System
Current year

TESTING:

After changes, verify that:

1. dashboard/index.html loads from a local web server.
2. dashboard/data.json is fetched successfully.
3. KPI cards render.
4. Charts render.
5. Tables render.
6. Missing datasets do not crash the page.
7. Browser console has no uncaught errors.

Provide complete updated file contents.