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
    columns: [["Transaction ID", ["Transaction_ID", "transaction_id"]], ["Date", ["Transaction_Date", "transaction_date", "date"], "date"], ["Type", ["Transaction_Type", "transaction_type", "type"]], ["School", ["School_Name", "school_name", "school"]], ["Warehouse", ["Warehouse_Name", "warehouse_name", "warehouse"]], ["Total Items", ["Total_Items", "total_items", "quantity"], "number"]]
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
    cell.textContent = "No records available";
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
    renderTable(container, config.title, config.columns, rows, { alert: config.alert });
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
  const charts = data.charts || {};
  const tables = data.tables || {};
  populateSelect("filter-zone", [
    ...(tables.recent_requisitions || []).map((row) => getValue(row, ["Zone", "zone"])),
    ...(tables.fulfillment_summary || []).map((row) => getValue(row, ["Zone", "zone"]))
  ]);
  populateSelect("filter-lga", [
    ...(charts.requests_by_lga || []).map((row) => getValue(row, ["lga", "LGA"])),
    ...(charts.distribution_by_lga || []).map((row) => getValue(row, ["lga", "LGA"]))
  ]);
  populateSelect("filter-status", (charts.requisition_status_distribution || []).map((row) => getValue(row, ["status", "Status"])));
  populateSelect("filter-category", (tables.stock_levels || []).map((row) => getValue(row, ["Category", "category"])));

  document.querySelectorAll("[data-filter]").forEach((select) => select.addEventListener("change", applyFilters));
  document.getElementById("clear-filters")?.addEventListener("click", () => {
    document.querySelectorAll("[data-filter]").forEach((select) => { select.value = ""; });
    applyFilters();
  });
}

function matches(record, keys, selected) {
  return !selected || String(getValue(record, keys, "")) === selected;
}

function applyFilters() {
  if (!dashboardData) return;
  const lga = document.getElementById("filter-lga")?.value || "";
  const status = document.getElementById("filter-status")?.value || "";
  const category = document.getElementById("filter-category")?.value || "";
  const zone = document.getElementById("filter-zone")?.value || "";
  const sourceCharts = dashboardData.charts || {};
  const sourceTables = dashboardData.tables || {};
  const filtered = {
    ...dashboardData,
    charts: {
      ...sourceCharts,
      requisition_status_distribution: (sourceCharts.requisition_status_distribution || []).filter((row) => matches(row, ["status", "Status"], status)),
      requests_by_lga: (sourceCharts.requests_by_lga || []).filter((row) => matches(row, ["lga", "LGA"], lga)),
      distribution_by_lga: (sourceCharts.distribution_by_lga || []).filter((row) => matches(row, ["lga", "LGA"], lga)),
      inventory_by_category: (sourceCharts.inventory_by_category || []).filter((row) => matches(row, ["category", "Category"], category))
    },
    tables: {
      ...sourceTables,
      stock_levels: (sourceTables.stock_levels || []).filter((row) => matches(row, ["Category", "category"], category)),
      recent_requisitions: (sourceTables.recent_requisitions || []).filter((row) =>
        matches(row, ["LGA", "lga"], lga) && matches(row, ["Status", "status"], status) && matches(row, ["Zone", "zone"], zone)),
      fulfillment_summary: (sourceTables.fulfillment_summary || []).filter((row) =>
        matches(row, ["LGA", "lga"], lga) && matches(row, ["Zone", "zone"], zone))
    }
  };
  SubebCharts.render(filtered);
  renderTables(filtered.tables);
  const active = [zone, lga, status, category].filter(Boolean);
  document.getElementById("filter-note").textContent = active.length
    ? `Filtered by: ${active.join(", ")}.`
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

