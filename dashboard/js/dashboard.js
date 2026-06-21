const DATA_URL = "data.json";
const API_BASE_URL = "https://resource-allocation-api.onrender.com";
const API_STATUS_TIMEOUT_MS = 8000;

const KPI_GROUPS = [
  {
    title: "Inventory",
    cards: [
      ["total_inventory_items", "Total Inventory Items"],
      ["total_available_stock", "Total Available Stock"],
      ["inventory_accuracy", "Inventory Accuracy", "percent"],
      ["low_stock_items", "Low Stock Items", "number", true],
      ["out_of_stock_items", "Out of Stock Items", "number", true],
      ["damaged_items", "Damaged Items", "number", true]
    ]
  },
  {
    title: "Requisitions",
    cards: [
      ["total_requisitions", "Total Requisitions"],
      ["pending_requisitions", "Pending Requisitions", "number", true],
      ["approved_requisitions", "Approved Requisitions"],
      ["partially_fulfilled_requisitions", "Partially Fulfilled Requisitions"],
      ["fulfilled_requisitions", "Fulfilled Requisitions"],
      ["rejected_requisitions", "Rejected Requisitions", "number", true]
    ]
  },
  {
    title: "Fulfillment",
    cards: [
      ["fulfillment_rate", "Fulfillment Rate", "percent"],
      ["average_fulfillment_days", "Average Fulfillment Days"],
      ["schools_served", "Schools Served"],
      ["total_schools", "Total Schools"],
      ["total_warehouses", "Total Warehouses"]
    ]
  }
];

const TABLE_CONFIG = [
  {
    title: "Stock Levels", path: "stock_levels", alertFields: ["Current_Stock"],
    columns: [["Item ID", ["Item_ID", "item_id"]], ["Item Name", ["Item_Name", "item_name"]], ["Category", ["Category", "category"]], ["Current Stock", ["Current_Stock", "current_stock"], "number"], ["Reorder Level", ["Reorder_Level", "reorder_level"], "number"]]
  },
  {
    title: "Low Stock Alerts", path: "low_stock_alerts", alert: true,
    columns: [["Item ID", ["Item_ID", "item_id"]], ["Item Name", ["Item_Name", "item_name"]], ["Category", ["Category", "category"]], ["Current Stock", ["Current_Stock", "current_stock"], "number"], ["Reorder Level", ["Reorder_Level", "reorder_level"], "number"]]
  },
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
  KPI_GROUPS.forEach((groupConfig) => {
    const section = document.createElement("section");
    section.className = "kpi-group";
    const heading = document.createElement("h3");
    heading.textContent = groupConfig.title;
    const grid = document.createElement("div");
    grid.className = "kpi-grid";
    const sources = [data.kpis, data[groupConfig.title.toLowerCase()]];
    groupConfig.cards.forEach(([key, label, type, alert]) => {
      const value = getValue(sources[0], key, getValue(sources[1], key));
      renderKpiCard(grid, label, value, type, alert);
    });
    section.append(heading, grid);
    root.appendChild(section);
  });
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

function setState(state) {
  document.getElementById("loading-state").hidden = state !== "loading";
  document.getElementById("error-state").hidden = state !== "error";
  document.getElementById("dashboard-content").hidden = state !== "ready";
}

function configureApiNavigation() {
  document.querySelectorAll("[data-api-path]").forEach((link) => {
    link.href = `${API_BASE_URL}${link.dataset.apiPath}`;
  });
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
    document.getElementById("last-updated").textContent = formatDateTime(data.generated_at);
    renderKpis(data);
    SubebCharts.render(data);
    renderTables(data.tables || {});
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

