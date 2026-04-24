// ---------- SAMPLE DATA (from CONTEXT) ----------
const sampleLocations = [
  {
    locationId: "us-tx-001",
    name: "HealthCore Austin Central",
    city: "Austin",
    stateOrCountry: "TX",
    country: "US",
    phone: "(512) 340-8800",
    averageConsultationFee: {
      primary_care: 180,
      chronic_disease: 220,
      preventive: 150,
      specialist: 320,
      womens_health: 240,
      paediatric: 175,
      mental_health: 200,
    },
  },
  {
    locationId: "us-fl-001",
    name: "HealthCore Miami",
    city: "Miami",
    stateOrCountry: "FL",
    country: "US",
    phone: "(305) 510-7700",
    averageConsultationFee: {
      primary_care: 195,
      chronic_disease: 235,
      preventive: 160,
      specialist: 340,
      womens_health: 255,
      paediatric: 185,
      mental_health: 215,
    },
  },
  {
    locationId: "us-ga-001",
    name: "HealthCore Atlanta",
    city: "Atlanta",
    stateOrCountry: "GA",
    country: "US",
    phone: "(404) 330-9900",
    averageConsultationFee: {
      primary_care: 170,
      chronic_disease: 210,
      preventive: 145,
      specialist: 310,
      womens_health: 230,
      paediatric: 165,
      mental_health: 190,
    },
  },
];

const sampleClaims = [
  {
    claimId: "CLM-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-10",
    claimAmount: 180,
    status: "approved",
    resubmitted: false,
  },
  {
    claimId: "CLM-000002",
    patientId: "HC-B7K442",
    locationId: "us-fl-001",
    serviceType: "specialist",
    payerName: "Aetna",
    payerId: "AET002",
    submissionDate: "2025-03-11",
    claimAmount: 340,
    status: "denied",
    denialReason: "missing_authorisation",
    resubmitted: false,
  },
  {
    claimId: "CLM-000003",
    patientId: "HC-C2M881",
    locationId: "us-ga-001",
    serviceType: "chronic_disease",
    payerName: "Medicare",
    payerId: "MED003",
    submissionDate: "2025-03-12",
    claimAmount: 210,
    status: "approved",
    resubmitted: false,
  },
  {
    claimId: "CLM-000004",
    patientId: "HC-D9P553",
    locationId: "us-tx-001",
    serviceType: "preventive",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-13",
    claimAmount: 150,
    status: "denied",
    denialReason: "coding_error",
    resubmitted: true,
  },
  {
    claimId: "CLM-000005",
    patientId: "HC-E4Q117",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    payerName: "Cigna",
    payerId: "CIG004",
    submissionDate: "2025-03-14",
    claimAmount: 215,
    status: "pending",
    resubmitted: false,
  },
];

const sampleAppointments = [
  {
    appointmentId: "APT-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    scheduledDate: "2025-03-10",
    scheduledTime: "09:00",
    status: "completed",
    confirmedAt: "2025-03-09T14:00:00Z",
  },
  {
    appointmentId: "APT-000002",
    patientId: "HC-F6R228",
    locationId: "us-fl-001",
    serviceType: "specialist",
    scheduledDate: "2025-03-11",
    scheduledTime: "11:30",
    status: "no_show",
    noShowReason: "Patient did not call to cancel",
  },
  {
    appointmentId: "APT-000003",
    patientId: "HC-G1S774",
    locationId: "us-tx-001",
    serviceType: "chronic_disease",
    scheduledDate: "2025-03-12",
    scheduledTime: "14:00",
    status: "no_show",
    noShowReason: "Unreachable before appointment",
  },
  {
    appointmentId: "APT-000004",
    patientId: "HC-H8T390",
    locationId: "us-ga-001",
    serviceType: "preventive",
    scheduledDate: "2025-03-13",
    scheduledTime: "10:00",
    status: "completed",
    confirmedAt: "2025-03-12T09:30:00Z",
  },
  {
    appointmentId: "APT-000005",
    patientId: "HC-I5U661",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    scheduledDate: "2025-03-14",
    scheduledTime: "16:00",
    status: "no_show",
    noShowReason: "Transportation issue reported",
  },
];

const sampleClinicians = [
  {
    clinicianId: "CLN-000001",
    firstName: "Marcus",
    lastName: "Reid",
    role: "physician",
    locationId: "us-tx-001",
    licenceState: "TX",
    licenceExpiryDate: "2026-06-30",
    cmeHoursRequired: 40,
    cmeHoursLogged: 28,
    cmeYearStartDate: "2025-01-01",
  },
  {
    clinicianId: "CLN-000002",
    firstName: "Sandra",
    lastName: "Flores",
    role: "nurse_practitioner",
    locationId: "us-fl-001",
    licenceState: "FL",
    licenceExpiryDate: "2025-05-15",
    cmeHoursRequired: 30,
    cmeHoursLogged: 6,
    cmeYearStartDate: "2025-01-01",
  },
  {
    clinicianId: "CLN-000003",
    firstName: "David",
    lastName: "Okafor",
    role: "physician",
    locationId: "us-ga-001",
    licenceState: "GA",
    licenceExpiryDate: "2027-01-01",
    cmeHoursRequired: 40,
    cmeHoursLogged: 40,
    cmeYearStartDate: "2025-01-01",
  },
];

// ---------- PURE UTILS / BUSINESS LOGIC ----------

// Filter claims by partial criteria
function filterClaims(claims, filters) {
  // Accepts optional normalize function for more forgiving search
  const normalize = arguments[2] || ((x) => x);
  return claims.filter((c) => {
    if (filters.locationId && normalize(c.locationId) !== filters.locationId) return false;
    if (filters.status && normalize(c.status) !== normalize(filters.status)) return false;
    if (filters.payerName && !normalize(c.payerName).includes(filters.payerName)) return false;
    if (filters.serviceType && normalize(c.serviceType) !== normalize(filters.serviceType)) return false;
    return true;
  });
}

// Sort claims by ID
function sortClaimsById(claims, direction) {
  const copy = [...claims];
  copy.sort((a, b) => {
    const cmp = a.claimId.localeCompare(b.claimId);
    return direction === "desc" ? -cmp : cmp;
  });
  return copy;
}

// Linear search claim
function findClaimById(claims, claimId) {
  return claims.find((c) => c.claimId.toLowerCase() === claimId.toLowerCase()) || null;
}

// Denial rate overall
function calculateDenialRate(claims) {
  if (!claims.length) throw new Error("No claims provided");
  const denied = claims.filter((c) => c.status === "denied").length;
  return Number(((denied / claims.length) * 100).toFixed(2));
}

// Denial rate by payer
function denialRateByPayer(claims) {
  const groups = {};
  claims.forEach((c) => {
    const key = c.payerName;
    if (!groups[key]) groups[key] = { total: 0, denied: 0 };
    groups[key].total++;
    if (c.status === "denied") groups[key].denied++;
  });
  const result = {};
  Object.entries(groups).forEach(([payer, g]) => {
    result[payer] = Number(((g.denied / g.total) * 100).toFixed(2));
  });
  return result;
}

// Denial rate by location
function denialRateByLocation(claims) {
  const groups = {};
  claims.forEach((c) => {
    const key = c.locationId;
    if (!groups[key]) groups[key] = { total: 0, denied: 0 };
    groups[key].total++;
    if (c.status === "denied") groups[key].denied++;
  });
  const result = {};
  Object.entries(groups).forEach(([loc, g]) => {
    result[loc] = Number(((g.denied / g.total) * 100).toFixed(2));
  });
  return result;
}

// No-show rate by location
function noShowRateByLocation(appointments) {
  const groups = {};
  appointments.forEach((a) => {
    const key = a.locationId;
    if (!groups[key]) groups[key] = { total: 0, noShow: 0 };
    groups[key].total++;
    if (a.status === "no_show") groups[key].noShow++;
  });
  const result = {};
  Object.entries(groups).forEach(([loc, g]) => {
    result[loc] = Number(((g.noShow / g.total) * 100).toFixed(2));
  });
  return result;
}

// Calculate no-show cost for 7 days ending on weekEndingDate
function calculateNoShowCost(appointments, location, weekEndingDate) {
  if (!location) return 0;
  const end = new Date(weekEndingDate + "T00:00:00");
  const start = new Date(end);
  start.setDate(end.getDate() - 6);

  const inRange = appointments.filter((a) => {
    if (a.locationId !== location.locationId) return false;
    if (a.status !== "no_show") return false;
    const d = new Date(a.scheduledDate + "T00:00:00");
    return d >= start && d <= end;
  });

  const total = inRange.reduce((sum, a) => {
    const fee = location.averageConsultationFee[a.serviceType] || 0;
    return sum + fee;
  }, 0);

  return Number(total.toFixed(2));
}

// CME report
function generateCMEReport(clinicians, asOfDate) {
  const asOf = new Date(asOfDate + "T00:00:00");
  return clinicians.map((c) => {
    const fullName = `${c.firstName} ${c.lastName}`;
    const hoursRequired = c.cmeHoursRequired;
    const hoursLogged = c.cmeHoursLogged;
    const hoursRemaining = Math.max(0, hoursRequired - hoursLogged);
    const percentComplete =
      hoursRequired === 0 ? 100 : Number(((hoursLogged / hoursRequired) * 100).toFixed(1));

    const cycleStart = new Date(c.cmeYearStartDate + "T00:00:00");
    const cycleEnd = new Date(c.cmeYearStartDate + "T00:00:00");
    cycleEnd.setFullYear(cycleEnd.getFullYear() + 1);

    const totalCycleDays = Math.round((cycleEnd - cycleStart) / (1000 * 60 * 60 * 24));
    const elapsedDays = Math.max(0, Math.min(
      totalCycleDays,
      Math.round((asOf - cycleStart) / (1000 * 60 * 60 * 24))
    ));
    const cyclePacePercent = totalCycleDays === 0
      ? 100
      : Number(((elapsedDays / totalCycleDays) * 100).toFixed(1));

    const daysRemainingInCycle = Math.max(
      0,
      Math.round((cycleEnd - asOf) / (1000 * 60 * 60 * 24))
    );

    const licenceExpiry = new Date(c.licenceExpiryDate + "T00:00:00");
    const licenceDaysRemaining = Math.round(
      (licenceExpiry - asOf) / (1000 * 60 * 60 * 24)
    );

    let complianceStatus;
    if (hoursLogged >= hoursRequired) {
      complianceStatus = "complete";
    } else if (asOf > cycleEnd) {
      complianceStatus = "overdue";
    } else {
      const behind = cyclePacePercent - percentComplete;
      complianceStatus = behind > 15 ? "at_risk" : "on_track";
    }

    return {
      clinicianId: c.clinicianId,
      fullName,
      role: c.role,
      locationId: c.locationId,
      hoursRequired,
      hoursLogged,
      hoursRemaining,
      percentComplete,
      daysRemainingInCycle,
      complianceStatus,
      licenceExpiryDate: c.licenceExpiryDate,
      licenceDaysRemaining,
    };
  });
}

function getCliniciansAtRisk(clinicians, asOfDate) {
  const report = generateCMEReport(clinicians, asOfDate);
  return report.filter((r) => r.complianceStatus === "at_risk" || r.complianceStatus === "overdue");
}

function getCliniciansWithExpiringLicences(clinicians, asOfDate, daysThreshold) {
  const report = generateCMEReport(clinicians, asOfDate);
  return report.filter((r) => r.licenceDaysRemaining >= 0 && r.licenceDaysRemaining <= daysThreshold);
}

// ---------- DASHBOARD WIRING ----------

function $(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const el = $(id);
  if (el) el.textContent = value;
}

function formatPercent(n) {
  return `${n.toFixed(2)}%`;
}

function formatCurrency(n) {
  return `$${n.toFixed(2)}`;
}

// Tabs
function initTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");

  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.getAttribute("data-tab");
      buttons.forEach((b) =>
        b.classList.toggle("bg-slate-800", b === btn)
      );
      panels.forEach((p) =>
        p.classList.toggle("hidden", p.id !== `tab-${tab}`)
      );
    });
  });
}

// Overview
function renderOverview() {
  let overallDenial = 0;
  try {
    overallDenial = calculateDenialRate(sampleClaims);
  } catch {
    overallDenial = 0;
  }
  setText("overview-denial-rate", formatPercent(overallDenial));

  const noshowRates = noShowRateByLocation(sampleAppointments);
  const allAppts = sampleAppointments.length;
  const totalNoShows = sampleAppointments.filter((a) => a.status === "no_show").length;
  const overallNoShow = allAppts === 0 ? 0 : Number(((totalNoShows / allAppts) * 100).toFixed(2));
  setText("overview-noshow-rate", formatPercent(overallNoShow));

  const atRisk = getCliniciansAtRisk(sampleClinicians, "2025-03-15");
  setText("overview-cme-risk", `${atRisk.length}`);

  // Render denial rate by payer as a table
  const denialByPayer = denialRateByPayer(sampleClaims);
  let denialTable = '<table class="min-w-full text-xs"><thead><tr><th class="px-2 py-1 text-left">Payer</th><th class="px-2 py-1 text-right">Denial Rate</th></tr></thead><tbody>';
  for (const payer in denialByPayer) {
    denialTable += `<tr><td class="border px-2 py-1">${payer}</td><td class="border px-2 py-1 text-right">${denialByPayer[payer].toFixed(2)}%</td></tr>`;
  }
  denialTable += '</tbody></table>';
  $("overview-denial-by-payer").innerHTML = denialTable;

  // Render no-show rate by location as a table
  let noshowTable = '<table class="min-w-full text-xs"><thead><tr><th class="px-2 py-1 text-left">Location</th><th class="px-2 py-1 text-right">No‑Show Rate</th></tr></thead><tbody>';
  for (const loc in noshowRates) {
    noshowTable += `<tr><td class="border px-2 py-1">${loc}</td><td class="border px-2 py-1 text-right">${noshowRates[loc].toFixed(2)}%</td></tr>`;
  }
  noshowTable += '</tbody></table>';
  $("overview-noshow-by-location").innerHTML = noshowTable;
}

// Claims tab
function renderClaimsTable(claims) {
  const tbody = $("claims-table-body");
  tbody.innerHTML = "";
  claims.forEach((c) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2">${c.claimId}</td>
      <td class="px-3 py-2">${c.payerName}</td>
      <td class="px-3 py-2">${c.locationId}</td>
      <td class="px-3 py-2">${c.serviceType}</td>
      <td class="px-3 py-2">${c.status}</td>
      <td class="px-3 py-2 text-right">${formatCurrency(c.claimAmount)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function initClaimsTab() {
  const payerInput = $("claims-filter-payer");
  const locInput = $("claims-filter-location");
  const statusSelect = $("claims-filter-status");
  const serviceSelect = $("claims-filter-service");
  const searchIdInput = $("claims-search-id");
  const sortSelect = $("claims-sort-direction");

  function normalize(str) {
    return (str || "").toLowerCase().replace(/\s+/g, " ").trim();
  }

  function apply() {
    const filters = {
      payerName: normalize(payerInput.value) || undefined,
      locationId: normalize(locInput.value) || undefined,
      status: statusSelect.value || undefined,
      serviceType: serviceSelect.value || undefined,
    };
    let result = filterClaims(sampleClaims, filters, normalize);
    const searchId = normalize(searchIdInput.value);
    if (searchId) {
      result = result.filter(c => normalize(c.claimId).includes(searchId));
    }
    result = sortClaimsById(result, sortSelect.value || "asc");
    renderClaimsTable(result);
  }

  // Live search as you type
  payerInput.addEventListener("input", apply);
  locInput.addEventListener("input", apply);
  statusSelect.addEventListener("change", apply);
  serviceSelect.addEventListener("change", apply);
  searchIdInput.addEventListener("input", apply);
  sortSelect.addEventListener("change", apply);
  $("claims-apply").addEventListener("click", apply);
  $("claims-reset").addEventListener("click", () => {
    payerInput.value = "";
    locInput.value = "";
    statusSelect.value = "";
    serviceSelect.value = "";
    searchIdInput.value = "";
    sortSelect.value = "asc";
    renderClaimsTable(sortClaimsById(sampleClaims, "asc"));
  });

  renderClaimsTable(sortClaimsById(sampleClaims, "asc"));
}

// Appointments tab
function renderAppointmentsTable(appts) {
  const tbody = $("appt-table-body");
  tbody.innerHTML = "";
  appts.forEach((a) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-2 py-1">${a.appointmentId}</td>
      <td class="px-2 py-1">${a.locationId}</td>
      <td class="px-2 py-1">${a.serviceType}</td>
      <td class="px-2 py-1">${a.status}</td>
      <td class="px-2 py-1">${a.scheduledDate}</td>
    `;
    tbody.appendChild(tr);
  });
}

function initAppointmentsTab() {
  const locInput = $("appt-filter-location");
  const statusSelect = $("appt-filter-status");
  const weekInput = $("appt-week-ending");

  function apply() {
    let result = [...sampleAppointments];
    const loc = locInput.value.trim();
    if (loc) result = result.filter((a) => a.locationId.toLowerCase() === loc.toLowerCase());
    const status = statusSelect.value;
    if (status) result = result.filter((a) => a.status.toLowerCase() === status.toLowerCase());

    renderAppointmentsTable(result);

    const rates = noShowRateByLocation(sampleAppointments);
    $("appt-noshow-by-location").textContent = JSON.stringify(rates, null, 2);

    const locationObj = sampleLocations.find((l) => l.locationId === (loc || result[0]?.locationId));
    if (locationObj && weekInput.value) {
      const cost = calculateNoShowCost(sampleAppointments, locationObj, weekInput.value);
      setText("appt-noshow-cost", formatCurrency(cost));
    } else {
      setText("appt-noshow-cost", "–");
    }
  }

  $("appt-apply").addEventListener("click", apply);
  $("appt-reset").addEventListener("click", () => {
    locInput.value = "";
    statusSelect.value = "";
    weekInput.value = "2025-03-14";
    renderAppointmentsTable(sampleAppointments);
    $("appt-noshow-by-location").textContent = JSON.stringify(
      noShowRateByLocation(sampleAppointments),
      null,
      2
    );
    setText("appt-noshow-cost", "–");
  });

  renderAppointmentsTable(sampleAppointments);
  $("appt-noshow-by-location").textContent = JSON.stringify(
    noShowRateByLocation(sampleAppointments),
    null,
    2
  );
}

// Clinicians tab
function renderCmeTable(report, statusFilter) {
  const tbody = $("cme-table-body");
  tbody.innerHTML = "";
  report
    .filter((r) => !statusFilter || r.complianceStatus === statusFilter)
    .forEach((r) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="px-2 py-1">${r.fullName}</td>
        <td class="px-2 py-1">${r.role}</td>
        <td class="px-2 py-1 text-right">${r.hoursLogged}/${r.hoursRequired}</td>
        <td class="px-2 py-1 text-right">${r.percentComplete.toFixed(1)}%</td>
        <td class="px-2 py-1">${r.complianceStatus}</td>
      `;
      tbody.appendChild(tr);
    });
}

function initCliniciansTab() {
  const asOfInput = $("cme-as-of");
  const statusSelect = $("cme-filter-status");
  const licenceThresholdInput = $("cme-licence-threshold");

  function apply() {
    const asOf = asOfInput.value || "2025-03-15";
    const report = generateCMEReport(sampleClinicians, asOf);
    renderCmeTable(report, statusSelect.value || "");

    const atRisk = getCliniciansAtRisk(sampleClinicians, asOf);
    $("cme-at-risk").textContent = JSON.stringify(atRisk, null, 2);

    const threshold = Number(licenceThresholdInput.value || "90");
    const expiring = getCliniciansWithExpiringLicences(sampleClinicians, asOf, threshold);
    $("cme-licence-expiring").textContent = JSON.stringify(expiring, null, 2);
  }

  $("cme-apply").addEventListener("click", apply);
  apply();
}

// ---------- INIT ----------
window.addEventListener("DOMContentLoaded", () => {
  initTabs();
  renderOverview();
  initClaimsTab();
  initAppointmentsTab();
  initCliniciansTab();
});

