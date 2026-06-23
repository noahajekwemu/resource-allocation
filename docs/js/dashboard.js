const DATA_URL = "data.json";
const API_BASE_URL = "https://resource-allocation-api.onrender.com";
const API_STATUS_TIMEOUT_MS = 8000;

const EXECUTIVE_KPIS = [
  ["total_inventory_items", "Total Inventory Items"],
  ["total_available_stock", "Total Available Stock"],
  ["inventory_accuracy", "Inventory Accuracy", "percent"],
  ["low_stock_items", "Low Stock Items", "number", true],
  ["out_of_stock_items", "Out of Stock Items", "number", true],
  ["pending_requisitions", "Pending Requisitions", "number", true],
  ["approved_requisitions", "Approved Requisitions"],
  ["fulfilled_requisitions", "Fulfilled Requisitions"],
  ["total_schools", "Total Schools"],
  ["total_warehouses", "Total Warehouses"]
];

const TABLE_CONFIG = [
  {
    title: "Recent Inventory Movements", path: "recent_movements",
    columns: [["Transaction ID", ["Transaction_ID", "transaction_id"]], ["Date", ["Transaction_Date", "transaction_date", "date"], "date"], ["Type", ["Transaction_Type", "transaction_type", "type"]], ["School", ["School_Name", "school_name", "school"]], ["Warehouse", ["Warehouse_Name", "warehouse_name", "warehouse"]], ["Item", ["Item_Name", "item_name", "item"]], ["Total Items", ["Total_Items", "total_items", "quantity"], "number"]]
  },
  {
    title: "Recent Requisitions", path: "recent_requisitions",
    columns: [["Requisition ID", ["Requisition_ID", "requisition_id", "id"]], ["Date", ["Request_Date", "request_date", "date", "created_at"], "date"], ["School", ["School_Name", "school_name", "school"]], ["LGA", ["LGA", "lga"]], ["Status", ["Status", "status"]], ["Requested", ["Requested_Quantity", "requested_quantity", "quantity_requested"], "number"], ["Fulfilled", ["Fulfilled_Quantity", "fulfilled_quantity", "quantity_fulfilled"], "number"]]
  },
  {
    title: "Fulfillment Summary", path: "fulfillment_summary",
    columns: [["School / LGA", ["School_Name", "school_name", "school", "LGA", "lga"]], ["Requested", ["Requested_Quantity", "requested_quantity", "quantity_requested", "requested"], "number"], ["Approved", ["Approved_Quantity", "approved_quantity", "quantity_approved", "approved"], "number"], ["Fulfilled", ["Fulfilled_Quantity", "fulfilled_quantity", "quantity_fulfilled", "fulfilled"], "number"], ["Fulfillment Rate", ["Fulfillment_Rate", "fulfillment_rate", "rate"], "percent"]]
  }
];

function getValue(source, path, fallback = null) {
  if (!source || path === undefined || path === null) return fallback;
  const paths = Array.isArray(path) ? path : [path];
  for (const candidate of paths) {
    const value = String(candidate).split(".").reduce((current, key) => current?.[key], source);
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return fallback;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "Not available";
  const numeric = Number(value);
  return Number.isFinite(numeric) ? new Intl.NumberFormat("en-NG", { maximumFractionDigits: 2 }).format(numeric) : String(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") return "Not available";
  return `${formatNumber(value)}%`;
}

function formatDate(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-NG", { dateStyle: "medium" }).format(date);
}

function formatDateTime(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-NG", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function renderKpiCard(container, label, value, type = "number", alert = false) {
  const card = document.createElement("article");
  card.className = `kpi-card${alert ? " kpi-card--alert" : ""}`;
  const heading = document.createElement("p");
  heading.className = "kpi-label";
  heading.textContent = label;
  const display = document.createElement("div");
  display.className = "kpi-value";
  display.textContent = type === "percent" ? formatPercent(value) : formatNumber(value);
  card.append(heading, display);
  container.appendChild(card);
}

function renderKpis(data) {
  const root = document.getElementById("kpi-groups");
  root.replaceChildren();
  const grid = document.createElement("div");
  grid.className = "kpi-grid";
  EXECUTIVE_KPIS.forEach(([key, label, type, alert]) => {
    renderKpiCard(grid, label, getValue(data.kpis, key), type, alert);
  });
  root.appendChild(grid);
}

function renderEmptyState(container, message = "No records available") {
  container.replaceChildren();
  const empty = document.createElement("div");
  empty.className = "empty-state";
  empty.textContent = message;
  container.appendChild(empty);
}

function formatTableValue(value, type) {
  if (type === "number") return formatNumber(value);
  if (type === "percent") return formatPercent(value);
  if (type === "date") return formatDate(value);
  return value === null || value === undefined || value === "" ? "Not available" : String(value);
}

function renderTable(container, title, columns, rows, options = {}) {
  const panel = document.createElement("article");
  panel.className = "table-panel";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const scroll = document.createElement("div");
  scroll.className = "table-scroll";
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach(([label]) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = label;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  const tbody = document.createElement("tbody");

  if (!Array.isArray(rows) || rows.length === 0) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = document.createElement("td");
    cell.colSpan = columns.length;
    cell.textContent = options.emptyMessage || "No records available";
    row.appendChild(cell);
    tbody.appendChild(row);
  } else {
    rows.forEach((record) => {
      const row = document.createElement("tr");
      columns.forEach(([label, keys, type]) => {
        const cell = document.createElement("td");
        cell.dataset.label = label;
        cell.textContent = formatTableValue(getValue(record, keys), type);
        if (type === "number" || type === "percent") cell.classList.add("numeric-cell");
        if (options.alert && (type === "number" || /status|stock/i.test(label))) cell.classList.add("alert-cell");
        row.appendChild(cell);
      });
      tbody.appendChild(row);
    });
  }

  table.append(thead, tbody);
  scroll.appendChild(table);
  panel.append(heading, scroll);
  container.appendChild(panel);
}

function renderTables(tables) {
  const container = document.getElementById("accountability-tables");
  container.replaceChildren();
  TABLE_CONFIG.forEach((config) => {
    const rows = getValue(tables, config.path, []);
    if (!Array.isArray(rows) || rows.length === 0) console.warn(`Optional table dataset missing or empty: tables.${config.path}`);
    renderTable(container, config.title, config.columns, rows, {
      alert: config.alert,
      emptyMessage: tables?.emptyMessage
    });
  });
}

let dashboardData = null;

function uniqueValues(values) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && String(value).trim()))]
    .map(String).sort((left, right) => left.localeCompare(right));
}

function populateSelect(id, values) {
  const select = document.getElementById(id);
  if (!select) return;
  const current = select.value;
  while (select.options.length > 1) select.remove(1);
  uniqueValues(values).forEach((value) => select.add(new Option(value, value)));
  if ([...select.options].some((option) => option.value === current)) select.value = current;
}

function configureFilters(data) {
  const filters = data.filters || {};
  populateSelect("filter-zone", filters.zones || []);
  populateSelect("filter-lga", filters.lgas || []);
  populateSelect("filter-warehouse", filters.warehouses || []);
  populateSelect("filter-school", filters.schools || []);
  populateSelect("filter-item", filters.items || []);
  populateSelect("filter-category", filters.categories || []);
  populateSelect("filter-status", filters.requisition_statuses || []);

  document.querySelectorAll("[data-filter]").forEach((select) => select.addEventListener("change", applyFilters));
  document.getElementById("clear-filters")?.addEventListener("click", () => {
    document.querySelectorAll("[data-filter]").forEach((select) => { select.value = ""; });
    applyFilters();
  });
}

function matches(record, keys, selected) {
  return !selected || String(getValue(record, keys, "")) === selected;
}

function selectedFilters() {
  return {
    zone: document.getElementById("filter-zone")?.value || "",
    lga: document.getElementById("filter-lga")?.value || "",
    warehouse: document.getElementById("filter-warehouse")?.value || "",
    school: document.getElementById("filter-school")?.value || "",
    item: document.getElementById("filter-item")?.value || "",
    category: document.getElementById("filter-category")?.value || "",
    status: document.getElementById("filter-status")?.value || ""
  };
}

function movementMatches(row, filters) {
  return matches(row, ["Zone", "zone"], filters.zone)
    && matches(row, ["LGA", "lga"], filters.lga)
    && matches(row, ["Warehouse_Name", "warehouse_name", "warehouse"], filters.warehouse)
    && matches(row, ["School_Name", "school_name", "school"], filters.school)
    && matches(row, ["Item_Name", "item_name", "item"], filters.item)
    && matches(row, ["Category", "category"], filters.category);
}

function requisitionMatches(row, filters) {
  return matches(row, ["Zone", "zone"], filters.zone)
    && matches(row, ["LGA", "lga"], filters.lga)
    && matches(row, ["School_Name", "school_name", "school"], filters.school)
    && matches(row, ["Item_Name", "item_name", "item"], filters.item)
    && matches(row, ["Category", "category"], filters.category)
    && matches(row, ["Status", "status"], filters.status);
}

function stockMatches(row, filters) {
  return matches(row, ["Item_Name", "item_name", "item"], filters.item)
    && matches(row, ["Category", "category"], filters.category);
}

function sumRows(rows, keys) {
  return rows.reduce((total, row) => total + Number(getValue(row, keys, 0) || 0), 0);
}

function groupRows(rows, labelKeys, valueKeys, outputLabel, outputValue = "quantity", limit = null) {
  const grouped = new Map();
  rows.forEach((row) => {
    const label = String(getValue(row, labelKeys, "Unspecified") || "Unspecified");
    grouped.set(label, (grouped.get(label) || 0) + Number(getValue(row, valueKeys, 0) || 0));
  });
  const result = [...grouped.entries()]
    .map(([label, value]) => ({ [outputLabel]: label, [outputValue]: value }))
    .sort((left, right) => Number(right[outputValue]) - Number(left[outputValue]) || String(left[outputLabel]).localeCompare(String(right[outputLabel])));
  return limit ? result.slice(0, limit) : result;
}

function buildStatusDistribution(rows) {
  return groupRows(rows, ["Status", "status"], ["_count"], "status").map((row) => ({
    status: row.status,
    quantity: rows.filter((item) => String(getValue(item, ["Status", "status"], "")) === row.status).length
  }));
}

function buildRequestedComparison(rows) {
  const grouped = new Map();
  rows.forEach((row) => {
    const item = String(getValue(row, ["Item_Name", "item_name", "item"], "Unspecified"));
    const current = grouped.get(item) || { item, requested: 0, approved: 0, fulfilled: 0 };
    current.requested += Number(getValue(row, ["Quantity_Requested", "requested"], 0) || 0);
    current.approved += Number(getValue(row, ["Quantity_Approved", "approved"], 0) || 0);
    current.fulfilled += Number(getValue(row, ["Quantity_Fulfilled", "fulfilled"], 0) || 0);
    grouped.set(item, current);
  });
  return [...grouped.values()].sort((left, right) => right.requested - left.requested || left.item.localeCompare(right.item));
}

function buildInventoryByCategory(rows) {
  return groupRows(rows, ["Category", "category"], ["Current_Stock", "current_stock"], "category");
}

function buildMonthlyMovements(rows) {
  const grouped = new Map();
  rows.forEach((row) => {
    const rawDate = getValue(row, ["Transaction_Date", "transaction_date", "date"], "");
    const month = rawDate ? String(rawDate).slice(0, 7) : "Unspecified";
    const current = grouped.get(month) || { month, in_quantity: 0, out_quantity: 0 };
    const quantity = Math.abs(Number(getValue(row, ["Total_Items", "total_items", "quantity"], 0) || 0));
    if (String(getValue(row, ["Transaction_Type", "transaction_type"], "")).toUpperCase() === "IN") current.in_quantity += quantity;
    if (String(getValue(row, ["Transaction_Type", "transaction_type"], "")).toUpperCase() === "OUT") current.out_quantity += quantity;
    grouped.set(month, current);
  });
  return [...grouped.values()].sort((left, right) => left.month.localeCompare(right.month));
}

function distinctCount(rows, keys) {
  return new Set(rows.map((row) => getValue(row, keys, "")).filter(Boolean).map(String)).size;
}

function recomputeKpis(baseKpis, stockRows, movementRows, requisitionRows, fulfillmentRows) {
  const kpis = { ...baseKpis };
  const totalItems = stockRows.length;
  const totalStock = sumRows(stockRows, ["Current_Stock", "current_stock"]);
  const negativeStock = stockRows.filter((row) => Number(getValue(row, ["Current_Stock", "current_stock"], 0)) < 0).length;
  const totalRequisitions = distinctCount(requisitionRows, ["Requisition_ID", "requisition_id"]);
  const statusRows = requisitionRows.length ? requisitionRows : [];
  const approved = sumRows(fulfillmentRows, ["Approved_Quantity", "approved"]);
  const fulfilled = sumRows(fulfillmentRows, ["Fulfilled_Quantity", "fulfilled"]);
  kpis.total_items = totalItems;
  kpis.total_inventory_items = totalItems;
  kpis.total_stock_units = totalStock;
  kpis.total_available_stock = Math.max(totalStock, 0);
  kpis.low_stock_items = stockRows.filter((row) => Number(getValue(row, ["Current_Stock"], 0)) <= Number(getValue(row, ["Minimum_Stock", "Reorder_Level"], 0))).length;
  kpis.out_of_stock_items = stockRows.filter((row) => Number(getValue(row, ["Current_Stock"], 0)) <= 0).length;
  kpis.inventory_accuracy = totalItems ? Math.round(((totalItems - negativeStock) / totalItems) * 10000) / 100 : 100;
  kpis.total_requisitions = totalRequisitions;
  kpis.pending_requisitions = distinctCount(statusRows.filter((row) => String(getValue(row, ["Status"], "")).toUpperCase() === "PENDING"), ["Requisition_ID"]);
  kpis.approved_requisitions = distinctCount(statusRows.filter((row) => String(getValue(row, ["Status"], "")).toUpperCase() === "APPROVED"), ["Requisition_ID"]);
  kpis.fulfilled_requisitions = distinctCount(statusRows.filter((row) => String(getValue(row, ["Status"], "")).toUpperCase() === "FULFILLED"), ["Requisition_ID"]);
  kpis.partially_fulfilled_requisitions = distinctCount(statusRows.filter((row) => String(getValue(row, ["Status"], "")).toUpperCase() === "PARTIALLY FULFILLED"), ["Requisition_ID"]);
  kpis.rejected_requisitions = distinctCount(statusRows.filter((row) => String(getValue(row, ["Status"], "")).toUpperCase() === "REJECTED"), ["Requisition_ID"]);
  kpis.fulfillment_rate = approved > 0 ? Math.round((Math.min(fulfilled, approved) / approved) * 10000) / 100 : 0;
  kpis.schools_served = distinctCount(movementRows.filter((row) => String(getValue(row, ["Transaction_Type"], "")).toUpperCase() === "OUT"), ["School_ID", "School_Name"]);
  kpis.total_schools = distinctCount([...movementRows, ...requisitionRows, ...fulfillmentRows], ["School_ID", "School_Name"]);
  kpis.total_warehouses = distinctCount(movementRows, ["Warehouse_ID", "Warehouse_Name"]);
  kpis.total_categories = distinctCount(stockRows, ["Category"]);
  return kpis;
}

function applyFilters() {
  if (!dashboardData) return;
  const filters = selectedFilters();
  const sourceCharts = dashboardData.charts || {};
  const sourceTables = dashboardData.tables || {};
  const stockRows = (sourceTables.stock_levels || []).filter((row) => stockMatches(row, filters));
  const movementRows = (sourceTables.recent_movements || []).filter((row) => movementMatches(row, filters));
  const requisitionRows = (sourceTables.requisition_items || []).filter((row) => requisitionMatches(row, filters));
  const recentRequisitions = (sourceTables.recent_requisitions || []).filter((row) =>
    matches(row, ["Zone", "zone"], filters.zone)
    && matches(row, ["LGA", "lga"], filters.lga)
    && matches(row, ["School_Name", "school_name", "school"], filters.school)
    && matches(row, ["Status", "status"], filters.status)
  );
  const fulfillmentRows = (sourceTables.fulfillment_summary || []).filter((row) =>
    matches(row, ["Zone", "zone"], filters.zone)
    && matches(row, ["LGA", "lga"], filters.lga)
    && matches(row, ["School_Name", "school_name", "school"], filters.school)
  );
  const requestedComparison = buildRequestedComparison(requisitionRows);
  const topRequestedItems = requestedComparison.slice(0, 10).map((row) => ({ item: row.item, quantity: row.requested }));
  const outflows = movementRows.filter((row) => String(getValue(row, ["Transaction_Type"], "")).toUpperCase() === "OUT");
  const inflows = movementRows.filter((row) => String(getValue(row, ["Transaction_Type"], "")).toUpperCase() === "IN");
  const schoolDistribution = groupRows(outflows, ["School_Name", "school"], ["Total_Items", "quantity"], "school");
  const hasMatches = stockRows.length || movementRows.length || requisitionRows.length || recentRequisitions.length || fulfillmentRows.length;
  const filtered = {
    ...dashboardData,
    kpis: recomputeKpis(dashboardData.kpis || {}, stockRows, movementRows, recentRequisitions, fulfillmentRows),
    charts: {
      ...sourceCharts,
      requisition_status_distribution: buildStatusDistribution(recentRequisitions),
      requested_vs_approved_vs_fulfilled: requestedComparison,
      top_requested_items: topRequestedItems,
      requests_by_lga: groupRows(requisitionRows, ["LGA", "lga"], ["Quantity_Requested", "requested"], "lga"),
      inventory_by_category: buildInventoryByCategory(stockRows),
      distribution_by_lga: groupRows(outflows, ["LGA", "lga"], ["Total_Items", "quantity"], "lga"),
      distribution_by_school_type: groupRows(outflows, ["School_Type", "school_type"], ["Total_Items", "quantity"], "school_type"),
      top_distributed_items: groupRows(outflows, ["Item_Name", "item"], ["Total_Items", "quantity"], "item", 10),
      top_schools: schoolDistribution.slice(0, 10),
      bottom_schools: [...schoolDistribution].sort((left, right) => left.quantity - right.quantity || left.school.localeCompare(right.school)).slice(0, 10),
      stock_source_analysis: groupRows(inflows, ["Source", "source"], ["Total_Items", "quantity"], "source"),
      monthly_stock_movements: buildMonthlyMovements(movementRows)
    },
    tables: {
      ...sourceTables,
      stock_levels: stockRows,
      recent_movements: movementRows,
      recent_requisitions: recentRequisitions,
      fulfillment_summary: fulfillmentRows,
      emptyMessage: hasMatches ? "No records available" : "No data for selected filters"
    }
  };
  renderKpis(filtered);
  SubebCharts.render(filtered);
  renderTables(filtered.tables);
  const active = Object.values(filters).filter(Boolean);
  document.getElementById("filter-note").textContent = active.length
    ? hasMatches ? `Filtered by: ${active.join(", ")}.` : "No data for selected filters"
    : "Showing all available records.";
}

function setState(state) {
  document.getElementById("loading-state").hidden = state !== "loading";
  document.getElementById("error-state").hidden = state !== "error";
  document.getElementById("dashboard-content").hidden = state !== "ready";
}

function configureApiNavigation() {
  document.querySelectorAll("[data-api-path]").forEach((link) => {
    link.href = `${API_BASE_URL}${link.dataset.apiPath}`;
  });
  const userManagementLink = document.querySelector(".admin-nav-link");
  if (userManagementLink) userManagementLink.title = "Admin access required";
  const reportsLink = document.querySelector(".secure-nav-link");
  if (reportsLink) reportsLink.title = "Secure login required";
}

async function checkApiStatus() {
  const indicator = document.getElementById("api-status");
  if (!indicator) return;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), API_STATUS_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
      signal: controller.signal
    });
    if (!response.ok) throw new Error(`Health check returned ${response.status}`);
    const result = await response.json();
    if (result.status !== "ok") throw new Error("Health check returned an unexpected response");
    indicator.textContent = "API Online";
    indicator.className = "api-status api-status--online";
  } catch (error) {
    console.warn("API health check failed:", error);
    indicator.textContent = "API Offline";
    indicator.className = "api-status api-status--offline";
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function loadDashboard() {
  setState("loading");
  document.getElementById("footer-year").textContent = new Date().getFullYear();
  try {
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`Dashboard data request failed with status ${response.status}`);
    const data = await response.json();
    dashboardData = data;
    document.getElementById("last-updated").textContent = formatDateTime(data.generated_at);
    renderKpis(data);
    SubebCharts.render(data);
    renderTables(data.tables || {});
    configureFilters(data);
    setState("ready");
  } catch (error) {
    console.error("Unable to load the accountability dashboard:", error);
    document.getElementById("last-updated").textContent = "Not available";
    setState("error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  configureApiNavigation();
  checkApiStatus();
  loadDashboard();
});

