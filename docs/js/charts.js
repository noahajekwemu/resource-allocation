const SubebCharts = (() => {
  const chartInstances = [];

  function cssColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function colors(includeAlert = false) {
    const standard = [cssColor("--subeb-blue"), cssColor("--subeb-blue-dark"), cssColor("--subeb-blue-light")];
    return includeAlert ? [cssColor("--subeb-red"), ...standard] : standard;
  }

  function destroyCharts() {
    while (chartInstances.length) chartInstances.pop().destroy();
  }

  function renderEmptyState(canvasId, message = "No chart data available") {
    const canvas = document.getElementById(canvasId);
    const frame = canvas?.closest(".chart-frame");
    if (!frame) return;
    canvas.hidden = true;
    let empty = frame.querySelector(".empty-state");
    if (!empty) {
      empty = document.createElement("div");
      empty.className = "empty-state";
      frame.appendChild(empty);
    }
    empty.textContent = message;
  }

  function prepareCanvas(canvasId, dataset) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) {
      if (!window.Chart) console.warn("Chart.js is unavailable; charts cannot be rendered.");
      return null;
    }
    const hasData = Array.isArray(dataset?.labels) && dataset.labels.length > 0 && dataset.series.some((series) => Array.isArray(series.data) && series.data.length > 0);
    if (!hasData) {
      console.warn(`Optional chart dataset missing or empty: ${canvasId}`);
      renderEmptyState(canvasId);
      return null;
    }
    canvas.hidden = false;
    canvas.closest(".chart-frame")?.querySelector(".empty-state")?.remove();
    return canvas;
  }

  function chartOptions(indexAxis = "x") {
    const text = cssColor("--subeb-text");
    const grid = cssColor("--subeb-blue-light");
    return {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis,
      plugins: {
        legend: { position: "bottom", labels: { color: text } },
        tooltip: { callbacks: { label: (context) => `${context.dataset.label}: ${new Intl.NumberFormat("en-NG").format(context.raw ?? 0)}` } }
      },
      scales: {
        x: { beginAtZero: true, ticks: { color: text }, grid: { color: grid } },
        y: { beginAtZero: true, ticks: { color: text }, grid: { color: grid } }
      }
    };
  }

  function createBarChart(canvasId, dataset, horizontal = false, alert = false) {
    const canvas = prepareCanvas(canvasId, dataset);
    if (!canvas) return null;
    const palette = colors(alert);
    const chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: dataset.labels,
        datasets: dataset.series.map((series, index) => ({
          label: series.label,
          data: series.data,
          backgroundColor: palette[index % palette.length],
          borderColor: index === 0 && alert ? cssColor("--subeb-red") : cssColor("--subeb-blue-dark"),
          borderWidth: 1
        }))
      },
      options: chartOptions(horizontal ? "y" : "x")
    });
    chartInstances.push(chart);
    return chart;
  }

  function createDoughnutChart(canvasId, dataset, alert = false) {
    const canvas = prepareCanvas(canvasId, dataset);
    if (!canvas) return null;
    const palette = colors(alert);
    const chart = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: dataset.labels,
        datasets: [{
          label: dataset.series[0].label,
          data: dataset.series[0].data,
          backgroundColor: dataset.labels.map((_, index) => palette[index % palette.length]),
          borderColor: cssColor("--subeb-white"),
          borderWidth: 2
        }]
      },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom", labels: { color: cssColor("--subeb-text") } } } }
    });
    chartInstances.push(chart);
    return chart;
  }

  function createLineChart(canvasId, dataset) {
    const canvas = prepareCanvas(canvasId, dataset);
    if (!canvas) return null;
    const palette = colors();
    const chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: dataset.labels,
        datasets: dataset.series.map((series, index) => ({
          label: series.label,
          data: series.data,
          borderColor: palette[index % palette.length],
          backgroundColor: palette[index % palette.length],
          tension: 0.25,
          fill: false
        }))
      },
      options: chartOptions()
    });
    chartInstances.push(chart);
    return chart;
  }

  function valueFrom(record, keys, fallback = 0) {
    for (const key of keys) {
      const value = record?.[key];
      if (value !== undefined && value !== null) return value;
    }
    return fallback;
  }

  function normalize(dataset, labelKeys, valueKeys = ["quantity", "value", "count"], seriesLabel = "Quantity") {
    if (!dataset) return { labels: [], series: [] };
    if (Array.isArray(dataset.labels) && Array.isArray(dataset.datasets)) {
      return { labels: dataset.labels, series: dataset.datasets.map((item) => ({ label: item.label || seriesLabel, data: item.data || [] })) };
    }
    if (!Array.isArray(dataset)) return { labels: [], series: [] };
    return {
      labels: dataset.map((record) => String(valueFrom(record, labelKeys, "Unspecified"))),
      series: [{ label: seriesLabel, data: dataset.map((record) => valueFrom(record, valueKeys, 0)) }]
    };
  }

  function normalizeComparison(dataset) {
    if (dataset && Array.isArray(dataset.labels) && Array.isArray(dataset.datasets)) return normalize(dataset, []);
    if (!Array.isArray(dataset)) return { labels: [], series: [] };
    return {
      labels: dataset.map((record) => String(valueFrom(record, ["item", "label", "name", "period"], "Total"))),
      series: [
        { label: "Requested", data: dataset.map((record) => valueFrom(record, ["requested", "requested_quantity", "quantity_requested"])) },
        { label: "Approved", data: dataset.map((record) => valueFrom(record, ["approved", "approved_quantity", "quantity_approved"])) },
        { label: "Fulfilled", data: dataset.map((record) => valueFrom(record, ["fulfilled", "fulfilled_quantity", "quantity_fulfilled"])) }
      ]
    };
  }

  function normalizeMovements(dataset) {
    if (!Array.isArray(dataset)) return normalize(dataset, []);
    return {
      labels: dataset.map((record) => String(valueFrom(record, ["month", "period", "date"], "Unspecified"))),
      series: [
        { label: "IN", data: dataset.map((record) => valueFrom(record, ["in_quantity", "in", "stock_in"])) },
        { label: "OUT", data: dataset.map((record) => valueFrom(record, ["out_quantity", "out", "stock_out"])) }
      ]
    };
  }

  function render(data) {
    destroyCharts();
    const charts = data?.charts || {};
    createDoughnutChart("requisition-status", normalize(charts.requisition_status_distribution, ["status", "label"], ["quantity", "count", "value"], "Requisitions"), true);
    createBarChart("requisition-quantities", normalizeComparison(charts.requested_vs_approved_vs_fulfilled));
    createBarChart("top-requested-items", normalize(charts.top_requested_items, ["item", "item_name", "label"]), true);
    createBarChart("requests-by-lga", normalize(charts.requests_by_lga, ["lga", "label"]));
    createBarChart("distribution-by-lga", normalize(charts.distribution_by_lga, ["lga", "label"]));
    createBarChart("distribution-by-school-type", normalize(charts.distribution_by_school_type, ["school_type", "label"]));
    createBarChart("top-schools", normalize(charts.top_schools, ["school", "school_name", "label"]), true);
    createBarChart("bottom-schools", normalize(charts.bottom_schools, ["school", "school_name", "label"]), true, true);
    createBarChart("top-distributed-items", normalize(charts.top_distributed_items, ["item", "item_name", "label"]), true);
    createDoughnutChart("inventory-by-category", normalize(charts.inventory_by_category, ["category", "label"], ["quantity", "value", "count"], "Inventory"));
    createBarChart("stock-source-analysis", normalize(charts.stock_source_analysis, ["source", "label"]));
    createLineChart("monthly-stock-movements", normalizeMovements(data?.monthly_movements || charts.monthly_stock_movements || data?.monthly_stock_movements));
  }

  return { render, renderEmptyState, createBarChart, createDoughnutChart, createLineChart };
})();
