// apps/healthcore-backend/test-runner.ts

import {
  filterClaims,
  sortClaimsById,
  filterAppointmentsByStatus,
  sortAppointmentsByDate,
  groupClaimsBy,
  findClaimById,
  findClinicianById,
  binarySearchClaimById,
  calculateDenialRate,
  denialRateByPayer,
  denialRateByLocation,
  flagHighDenialPayers,
  calculateNoShowCost,
  noShowRateByLocation,
  flagHighNoShowLocations,
  generateCMEReport,
  getCliniciansAtRisk,
  getCliniciansWithExpiringLicences,
  validateClaim,
  validateClinician,
} from "./src/index.js";

import {
  sampleClaims,
  sampleAppointments,
  sampleClinicians,
  sampleLocations,
} from "./sample-data.js";

console.log("=== HealthCore Backend Test Runner ===\n");

// 1. Filtering
console.log("Filter Claims (payer = BlueCross):");
console.log(filterClaims(sampleClaims, { payerName: "BlueCross" }), "\n");

// 2. Sorting
console.log("Sort Claims by ID (ASC):");
console.log(sortClaimsById(sampleClaims, "asc"), "\n");

// 3. Searching
console.log("Find Claim by ID (CLM-000004):");
console.log(findClaimById(sampleClaims, "CLM-000004"), "\n");

// 4. Binary Search
const sorted = sortClaimsById(sampleClaims, "asc");
console.log("Binary Search for CLM-000003:");
console.log(binarySearchClaimById(sorted, "CLM-000003"), "\n");

// 5. Denial Rates
console.log("Denial Rate by Payer:");
console.log(denialRateByPayer(sampleClaims), "\n");

// 6. High Denial Payers
console.log("High Denial Payers (>8%):");
console.log(flagHighDenialPayers(sampleClaims), "\n");

// 7. No-Show Cost
console.log("No-Show Cost (us-fl-001, week ending 2025-03-14):");
const loc = sampleLocations.find((l) => l.locationId === "us-fl-001");
console.log(calculateNoShowCost(sampleAppointments, loc!, "2025-03-14"), "\n");

// 8. No-Show Rates
console.log("No-Show Rate by Location:");
console.log(noShowRateByLocation(sampleAppointments), "\n");

// 9. High No-Show Locations
console.log("High No-Show Locations (>20%):");
console.log(flagHighNoShowLocations(sampleAppointments), "\n");

// 10. CME Report
console.log("CME Report (as of 2025-03-15):");
console.log(generateCMEReport(sampleClinicians, "2025-03-15"), "\n");

// 11. Clinicians at Risk
console.log("Clinicians at Risk:");
console.log(getCliniciansAtRisk(sampleClinicians, "2025-03-15"), "\n");

// 12. Expiring Licences
console.log("Clinicians with licences expiring within 90 days:");
console.log(getCliniciansWithExpiringLicences(sampleClinicians, "2025-03-15", 90), "\n");

// 13. Validations
console.log("Validate Claim (sampleClaims[1]):");
console.log(validateClaim(sampleClaims[1], sampleLocations.map((l) => l.locationId)), "\n");

console.log("Validate Clinician (sampleClinicians[1]):");
console.log(validateClinician(sampleClinicians[1]), "\n");

console.log("=== Test Runner Complete ===");
