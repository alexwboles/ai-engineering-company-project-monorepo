import { sampleAppointments, sampleClaims, sampleClinicians, sampleLocations } from "../../../apps/healthcore-backend/sample-data";
import {
  calculateDenialRate,
  calculateNoShowCost,
  denialRateByPayer,
  generateCMEReport,
} from "../../../apps/healthcore-backend/src/utils/transformations";

export type BackofficeSnapshot = {
  claimDenialRate: number;
  denialRateByPayer: Record<string, number>;
  noShowCostByLocation: Array<{
    locationId: string;
    locationName: string;
    weeklyCost: number;
  }>;
  cmeSummary: Array<{
    clinicianId: string;
    fullName: string;
    status: string;
    percentComplete: number;
    hoursRemaining: number;
  }>;
};

export function buildOperationalSnapshot(asOfDate: string): BackofficeSnapshot {
  const claimDenialRate = calculateDenialRate(sampleClaims);
  const payerRates = denialRateByPayer(sampleClaims);

  const noShowCostByLocation = sampleLocations.map((location) => ({
    locationId: location.locationId,
    locationName: location.name,
    weeklyCost: calculateNoShowCost(sampleAppointments, location, asOfDate),
  }));

  const cmeSummary = generateCMEReport(sampleClinicians, asOfDate).map((row) => ({
    clinicianId: row.clinicianId,
    fullName: row.fullName,
    status: row.complianceStatus,
    percentComplete: row.percentComplete,
    hoursRemaining: row.hoursRemaining,
  }));

  return {
    claimDenialRate,
    denialRateByPayer: payerRates,
    noShowCostByLocation,
    cmeSummary,
  };
}
