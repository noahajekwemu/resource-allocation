Phase 14 – Advanced dashboard filters for delivery.

Goal:
Add working dashboard filters by LGA, Zone, Warehouse, School, Item, Category, and Requisition Status.

Files to update:
- dashboard/index.html
- dashboard/css/styles.css
- dashboard/js/dashboard.js
- dashboard/js/charts.js
- scripts/calculate_metrics.py
- tests/test_calculate_metrics.py

Requirements:

1. dashboard/data.json must include:
filters.lgas
filters.zones
filters.warehouses
filters.schools
filters.items
filters.categories
filters.requisition_statuses

2. Each relevant data row should include as many of these fields as available:
LGA
Zone
Warehouse_ID
Warehouse_Name
School_ID
School_Name
Item_ID
Item_Name
Category
Status

3. Add a filter panel on the dashboard similar to the SUBEB sample:
- Zone
- LGA
- Warehouse
- School
- Item
- Category
- Requisition Status
- Reset Filters

4. Filtering should update:
- KPI cards where practical
- Requisition charts
- Stock charts
- Recent Inventory Movements
- Recent Requisitions
- Fulfillment Summary

5. If a filter returns no data, show:
No data for selected filters

6. Filters must not break dashboard rendering.

7. Preserve:
- API Online badge
- Render links
- Last Updated
- existing KPI cards
- Chart.js charts
- loading from data.json
- GitHub Pages compatibility

8. Do not edit docs/ directly.

9. Add/update tests for filter arrays in calculate_metrics.py.

10. Ensure python -m pytest passes.