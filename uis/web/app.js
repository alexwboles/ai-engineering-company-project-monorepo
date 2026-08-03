const API_BASE_URL =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : "http://api:8000";

const analyzeBtn = document.getElementById("analyze-btn");
const exportBtn = document.getElementById("export-btn");
const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");
const statusMessage = document.getElementById("status-message");
const resultsSection = document.getElementById("results-section");

const summaryGrid = document.getElementById("summary-grid");
const categoryList = document.getElementById("category-list");
const statusList = document.getElementById("status-list");
const invalidList = document.getElementById("invalid-list");

let selectedFile = null;

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
}

function createMetric(label, value) {
  const card = document.createElement("article");
  card.className = "metric";
  card.innerHTML = `<p class="label">${label}</p><p class="value">${value}</p>`;
  return card;
}

function renderKeyValueList(element, data) {
  element.innerHTML = "";
  const entries = Object.entries(data || {});
  if (entries.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No data";
    element.appendChild(li);
    return;
  }

  entries.sort(([a], [b]) => a.localeCompare(b));
  for (const [key, value] of entries) {
    const li = document.createElement("li");
    li.textContent = `${key}: ${value}`;
    element.appendChild(li);
  }
}

function renderResults(payload) {
  const summary = payload.summary;
  summaryGrid.innerHTML = "";
  summaryGrid.append(
    createMetric("Total processed", summary.total_records),
    createMetric("Valid", summary.valid_records),
    createMetric("Invalid", summary.invalid_records),
    createMetric(
      "Avg satisfaction (closed)",
      summary.average_satisfaction_closed == null
        ? "N/A"
        : Number(summary.average_satisfaction_closed).toFixed(4)
    )
  );

  renderKeyValueList(categoryList, summary.category_breakdown);
  renderKeyValueList(statusList, summary.status_breakdown);
  renderKeyValueList(invalidList, summary.invalid_by_reason);

  resultsSection.classList.remove("hidden");

  if (summary.invalid_records > 0) {
    setStatus(
      `Analysis complete. File contains ${summary.invalid_records} invalid records across ${Object.keys(summary.invalid_by_reason).length} error type(s).`
    );
  } else {
    setStatus("Analysis complete. No invalid records found.");
  }
}

async function handleAnalyze() {
  if (!selectedFile) {
    setStatus("Please select a CSV file first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("file", selectedFile);

  setStatus("Uploading and analyzing...");
  try {
    const response = await fetch(`${API_BASE_URL}/api/incidents/analyze`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to analyze file.");
    }

    renderResults(payload);
  } catch (error) {
    setStatus(`Error: ${error.message}`, true);
  }
}

function handleFileSelect(file) {
  selectedFile = file;
  setStatus(`Selected file: ${file.name}`);
}

analyzeBtn.addEventListener("click", handleAnalyze);

exportBtn.addEventListener("click", () => {
  window.location.href = `${API_BASE_URL}/api/incidents/results/export`;
});

fileInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) handleFileSelect(file);
});

dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("dragover");
  const file = event.dataTransfer?.files?.[0];
  if (file) {
    fileInput.files = event.dataTransfer.files;
    handleFileSelect(file);
  }
});
