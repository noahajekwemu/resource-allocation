const DATA_URL = "data.json";

const KPI_CONFIG = [
  ["total_inventory_items", "Total Inventory Items"],
  ["total_available_stock", "Total Available Stock"],
  ["inventory_accuracy", "Inventory Accuracy", "percent"],
  ["schools_served", "Schools Served"],
  ["pending_requisitions", "Pending Requisitions", "alert"],
  ["low_stock_items", "Low Stock Items", "alert"],
  ["total_warehouses", "Warehouses"],
  ["damaged_items", "Damaged Items", "alert"]
];

function formatNumber(value) {
  return new Intl.NumberFormat("en-NG").format(value ?? 0);
}

function formatKpiValue(value, type) {
  if (type === "percent") return `${formatNumber(value)}%`;
  return formatNumber(value);
}

function formatDateTime(value) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-NG", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function setState(state) {
  document.getElementById("loading-state").hidden = state !== "loading";
  document.getElementById("error-state").hidden = state !== "error";
  document.getElementById("dashboard-content").hidden = state !== "ready";
}

function renderKpis(kpis) {
  const grid = document.getElementById("kpi-grid");
  grid.innerHTML = "";

  KPI_CONFIG.forEach(([key, label, type]) => {
    const card = document.createElement("article");
    card.className = type === "alert" ? "kpi-card kpi-card--alert" : "kpi-card";
    card.innerHTML = `
      <p class="kpi-label">${label}</p>
      <div class="kpi-value">${formatKpiValue(kpis?.[key], type)}</div>
    `;
    grid.appendChild(card);
  });
}

function tableCell(value, className = "") {
  const cell = document.createElement("td");
  cell.textContent = value ?? "";
  if (className) cell.className = className;
  return cell;
}

function renderEmptyRow(tbody, colspan) {
  const row = document.createElement("tr");
  row.className = "empty-row";
  const cell = tableCell("No records available");
  cell.colSpan = colspan;
  row.appendChild(cell);
  tbody.appendChild(row);
}

function renderStockTable(tableId, rows, alert = false) {
  const tbody = document.getElementById(tableId);
  tbody.innerHTML = "";

  if (!rows || rows.length === 0) {
    renderEmptyRow(tbody, 5);
    return;
  }

  rows.forEach((record) => {
    const row = document.createElement("tr");
    row.appendChild(tableCell(record.Item_ID));
    row.appendChild(tableCell(record.Item_Name));
    row.appendChild(tableCell(record.Category));
    row.appendChild(tableCell(formatNumber(record.Current_Stock), alert ? "numeric-cell alert-cell" : "numeric-cell"));
    row.appendChild(tableCell(formatNumber(record.Reorder_Level), "numeric-cell"));
    tbody.appendChild(row);
  });
}

function renderMovementsTable(rows) {
  const tbody = document.getElementById("recent-movements-table");
  tbody.innerHTML = "";

  if (!rows || rows.length === 0) {
    renderEmptyRow(tbody, 6);
    return;
  }

  rows.forEach((record) => {
    const row = document.createElement("tr");
    row.appendChild(tableCell(record.Transaction_ID));
    row.appendChild(tableCell(formatDateTime(record.Transaction_Date)));
    row.appendChild(tableCell(record.Transaction_Type));
    row.appendChild(tableCell(record.School_Name));
    row.appendChild(tableCell(record.Warehouse_Name));
    row.appendChild(tableCell(formatNumber(record.Total_Items), "numeric-cell"));
    tbody.appendChild(row);
  });
}

function renderTables(tables) {
  renderStockTable("stock-levels-table", tables?.stock_levels);
  renderStockTable("low-stock-alerts-table", tables?.low_stock_alerts, true);
  renderMovementsTable(tables?.recent_movements);
}

async function loadDashboard() {
  setState("loading");
  document.getElementById("footer-year").textContent = new Date().getFullYear();

  try {
    const response = await fetch(DATA_URL);
    if (!response.ok) throw new Error("Unable to load dashboard data.");

    const data = await response.json();
    document.getElementById("last-updated").textContent = formatDateTime(data.generated_at);
    renderKpis(data.kpis || {});
    SubebCharts.render(data.charts || {});
    renderTables(data.tables || {});
    setState("ready");
  } catch (error) {
    document.getElementById("last-updated").textContent = "Not available";
    setState("error");
  }
}

document.addEventListener("DOMContentLoaded", loadDashboard);
