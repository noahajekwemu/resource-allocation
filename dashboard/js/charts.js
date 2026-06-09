const SubebCharts = (() => {
  const chartInstances = [];

  function cssColor(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function palette() {
    return [
      cssColor("--subeb-blue"),
      cssColor("--subeb-blue-dark"),
      cssColor("--subeb-blue-light")
    ];
  }

  function alertPalette() {
    return [
      cssColor("--subeb-red"),
      cssColor("--subeb-blue-dark"),
      cssColor("--subeb-blue")
    ];
  }

  function destroyCharts() {
    while (chartInstances.length) {
      chartInstances.pop().destroy();
    }
  }

  function chartOptions(indexAxis = "x") {
    const textColor = cssColor("--subeb-text");
    const gridColor = cssColor("--subeb-blue-light");

    return {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis,
      plugins: {
        legend: {
          labels: { color: textColor }
        },
        tooltip: {
          callbacks: {
            label(context) {
              const value = indexAxis === "y" ? context.parsed.x : context.parsed.y;
              return `${context.dataset.label}: ${value}`;
            }
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { color: textColor },
          grid: { color: gridColor }
        },
        y: {
          beginAtZero: true,
          ticks: { color: textColor },
          grid: { color: gridColor }
        }
      }
    };
  }

  function dataset(records, labelKey) {
    return {
      labels: (records || []).map((record) => record[labelKey] || "Unspecified"),
      values: (records || []).map((record) => record.quantity ?? 0)
    };
  }

  function renderBar(canvasId, records, labelKey, label, horizontal = false, alert = false) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;

    const data = dataset(records, labelKey);
    const colors = alert ? alertPalette() : palette();
    const indexAxis = horizontal ? "y" : "x";

    chartInstances.push(new Chart(canvas, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [{
          label,
          data: data.values,
          backgroundColor: colors[0],
          borderColor: colors[1],
          borderWidth: 1
        }]
      },
      options: chartOptions(indexAxis)
    }));
  }

  function renderDoughnut(canvasId, records, labelKey, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !window.Chart) return;

    const data = dataset(records, labelKey);
    const colors = palette();

    chartInstances.push(new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: data.labels,
        datasets: [{
          label,
          data: data.values,
          backgroundColor: data.labels.map((_, index) => colors[index % colors.length]),
          borderColor: cssColor("--subeb-white"),
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: cssColor("--subeb-text") }
          }
        }
      }
    }));
  }

  function render(charts) {
    destroyCharts();
    renderDoughnut("inventory-by-category", charts.inventory_by_category, "category", "Inventory");
    renderBar("distribution-by-lga", charts.distribution_by_lga, "lga", "Quantity");
    renderBar("distribution-by-school-type", charts.distribution_by_school_type, "school_type", "Quantity");
    renderBar("top-distributed-items", charts.top_distributed_items, "item", "Quantity", true);
    renderBar("top-schools", charts.top_schools, "school", "Quantity", true);
    renderBar("bottom-schools", charts.bottom_schools, "school", "Quantity", true, true);
    renderBar("stock-source-analysis", charts.stock_source_analysis, "source", "Quantity");
  }

  return { render };
})();
