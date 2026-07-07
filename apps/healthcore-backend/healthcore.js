// ---------------- SAMPLE DATA ----------------
const sampleClaims = [
  { claimId: "CLM-000001", payerName: "BlueCross", status: "denied", amount: 1200 },
  { claimId: "CLM-000002", payerName: "Aetna", status: "paid", amount: 900 },
  { claimId: "CLM-000003", payerName: "BlueCross", status: "paid", amount: 700 },
  { claimId: "CLM-000004", payerName: "UnitedHealth", status: "denied", amount: 1500 }
];

const sampleAppointments = [
  { appointmentId: "APT-001", locationId: "us-fl-001", status: "no-show", date: "2025-03-10" },
  { appointmentId: "APT-002", locationId: "us-fl-001", status: "completed", date: "2025-03-11" },
  { appointmentId: "APT-003", locationId: "us-fl-001", status: "no-show", date: "2025-03-12" }
];

const sampleClinicians = [
  { clinicianId: "CLN-001", cmeHours: 18, requiredCME: 20, licenseExpiry: "2025-04-01" },
  { clinicianId: "CLN-002", cmeHours: 25, requiredCME: 20, licenseExpiry: "2025-09-01" }
];

const sampleLocations = [
  { locationId: "us-fl-001", noShowCost: 200 }
];

// ---------------- FUNCTIONS ----------------

// Filtering
function filterClaims(claims, criteria) {
  return claims.filter(c =>
    Object.entries(criteria).every(([k, v]) => c[k] === v)
  );
}

// Sorting
function sortClaimsById(claims, direction = "asc") {
  return [...claims].sort((a, b) =>
    direction === "asc"
      ? a.claimId.localeCompare(b.claimId)
      : b.claimId.localeCompare(a.claimId)
  );
}

// Searching
function findClaimById(claims, id) {
  return claims.find(c => c.claimId === id) || null;
}

// Denial rate
function denialRateByPayer(claims) {
  const groups = {};
  claims.forEach(c => {
    if (!groups[c.payerName]) groups[c.payerName] = { total: 0, denied: 0 };
    groups[c.payerName].total++;
    if (c.status === "denied") groups[c.payerName].denied++;
  });

  return Object.fromEntries(
    Object.entries(groups).map(([payer, g]) => [
      payer,
      g.denied / g.total
    ])
  );
}

// No-show cost
function calculateNoShowCost(appointments, location, weekEnding) {
  const week = appointments.filter(a =>
    a.locationId === location.locationId &&
    a.status === "no-show"
  );
  return week.length * location.noShowCost;
}

// CME
function generateCMEReport(clinicians, today) {
  return clinicians.map(c => ({
    clinicianId: c.clinicianId,
    cmeComplete: c.cmeHours >= c.requiredCME,
    hoursRemaining: Math.max(0, c.requiredCME - c.cmeHours)
  }));
}

// Expose globally
window.HealthCore = {
  sampleClaims,
  sampleAppointments,
  sampleClinicians,
  sampleLocations,
  filterClaims,
  sortClaimsById,
  findClaimById,
  denialRateByPayer,
  calculateNoShowCost,
  generateCMEReport
};
