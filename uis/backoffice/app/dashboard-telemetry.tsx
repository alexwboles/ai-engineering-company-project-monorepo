"use client";

import { useEffect } from "react";
import { sampleAppointments, sampleClaims, sampleClinicians, sampleLocations } from "../../../apps/healthcore-backend/sample-data";
import { calculateNoShowCost, generateCMEReport, noShowRateByLocation } from "../../../apps/healthcore-backend/src/utils/transformations";
import { validateClaim } from "../../../apps/healthcore-backend/src/utils/validations";
import { track } from "@/lib/telemetry";

type DashboardTelemetryProps = {
  asOfDate: string;
};

function getLeadTimeHours(appointmentDate: string, confirmedAt?: string): number | undefined {
  if (!confirmedAt) {
    return undefined;
  }

  const scheduled = new Date(`${appointmentDate}T00:00:00Z`).getTime();
  const confirmed = new Date(confirmedAt).getTime();
  if (!Number.isFinite(scheduled) || !Number.isFinite(confirmed)) {
    return undefined;
  }

  return Number(((scheduled - confirmed) / (1000 * 60 * 60)).toFixed(2));
}

function getDaysSinceSubmission(asOfDate: string, submissionDate: string): number {
  const end = new Date(`${asOfDate}T00:00:00Z`).getTime();
  const start = new Date(`${submissionDate}T00:00:00Z`).getTime();
  return Number(((end - start) / (1000 * 60 * 60 * 24)).toFixed(2));
}

function getCycleYear(value: string): number {
  const year = new Date(value).getFullYear();
  return Number.isFinite(year) ? year : new Date().getFullYear();
}

export function DashboardTelemetry({ asOfDate }: DashboardTelemetryProps) {
  useEffect(() => {
    if (window.sessionStorage.getItem("healthcore_dashboard_telemetry_seeded") === "1") {
      return;
    }

    window.sessionStorage.setItem("healthcore_dashboard_telemetry_seeded", "1");

    const knownLocationIds = sampleLocations.map((location) => location.locationId);

    for (const claim of sampleClaims) {
      track("claim_submitted", {
        claimId: claim.claimId,
        locationId: claim.locationId,
        payerId: claim.payerId,
        payerName: claim.payerName,
        serviceType: claim.serviceType,
        claimAmount: claim.claimAmount,
        resubmitted: claim.resubmitted,
        submissionChannel: "backoffice_snapshot",
      });

      if (claim.status === "denied" && claim.denialReason) {
        track("claim_denied", {
          claimId: claim.claimId,
          locationId: claim.locationId,
          payerId: claim.payerId,
          denialReason: claim.denialReason,
          resubmitted: claim.resubmitted,
          claimAmount: claim.claimAmount,
          daysSinceSubmission: getDaysSinceSubmission(asOfDate, claim.submissionDate),
          appealEligible: claim.denialReason !== "duplicate_claim",
        });
      }

      const validation = validateClaim(claim, knownLocationIds);
      if (!validation.valid) {
        track("claim_validation_failed", {
          claimId: claim.claimId,
          locationId: claim.locationId,
          validationErrors: validation.errors,
          invalidFields: validation.errors.map((error) => error.split(" ")[0] ?? "unknown"),
          source: "dashboard_snapshot",
          severity: validation.errors.some((error) => error.includes("future")) ? "high" : "medium",
        });
      }
    }

    for (const appointment of sampleAppointments) {
      track("appointment_scheduled", {
        appointmentId: appointment.appointmentId,
        locationId: appointment.locationId,
        serviceType: appointment.serviceType,
        scheduledDate: appointment.scheduledDate,
        scheduledTime: appointment.scheduledTime,
        channel: "manual_entry",
        leadTimeHours: getLeadTimeHours(appointment.scheduledDate, appointment.confirmedAt),
      });

      if (appointment.status === "completed") {
        track("appointment_completed", {
          appointmentId: appointment.appointmentId,
          locationId: appointment.locationId,
          serviceType: appointment.serviceType,
          staffedByRole: "clinical_staff",
        });
      }

      if (appointment.status === "no_show") {
        track("appointment_no_show_marked", {
          appointmentId: appointment.appointmentId,
          locationId: appointment.locationId,
          serviceType: appointment.serviceType,
          noShowReasonCode: appointment.noShowReason ? "reported_no_show" : undefined,
          reminderCount: appointment.noShowReason ? 2 : 1,
          rescheduled: false,
        });
      }
    }

    for (const clinician of sampleClinicians) {
      track("clinician_cme_logged", {
        clinicianId: clinician.clinicianId,
        role: clinician.role,
        cmeHoursLogged: clinician.cmeHoursLogged,
        cmeHoursRequired: clinician.cmeHoursRequired,
        source: "dashboard_snapshot",
        cycleYear: getCycleYear(clinician.cmeYearStartDate),
      });
    }

    const cmeReport = generateCMEReport(sampleClinicians, asOfDate);
    for (const row of cmeReport) {
      track("clinician_compliance_calculated", {
        clinicianId: row.clinicianId,
        role: row.role,
        cmeHoursLogged: row.hoursLogged,
        cmeHoursRequired: row.hoursRequired,
        complianceStatus: row.complianceStatus,
        hoursRemaining: row.hoursRemaining,
        daysUntilLicenceExpiry: row.licenceDaysRemaining,
      });
    }

    const claimsByPayerAndLocation = new Map<string, { payerId: string; payerName: string; locationId: string; totalClaims: number; deniedClaims: number }>();
    for (const claim of sampleClaims) {
      const key = `${claim.payerId}|${claim.locationId}`;
      const current = claimsByPayerAndLocation.get(key) ?? {
        payerId: claim.payerId,
        payerName: claim.payerName,
        locationId: claim.locationId,
        totalClaims: 0,
        deniedClaims: 0,
      };
      current.totalClaims += 1;
      current.deniedClaims += claim.status === "denied" ? 1 : 0;
      claimsByPayerAndLocation.set(key, current);
    }

    for (const row of claimsByPayerAndLocation.values()) {
      track("billing_denial_rate_calculated", {
        payerId: row.payerId,
        payerName: row.payerName,
        locationId: row.locationId,
        periodStart: "2025-03-08",
        periodEnd: asOfDate,
        totalClaims: row.totalClaims,
        deniedClaims: row.deniedClaims,
        denialRate: Number(((row.deniedClaims / row.totalClaims) * 100).toFixed(2)),
      });
    }

    for (const location of sampleLocations) {
      const locationAppointments = sampleAppointments.filter((appointment) => appointment.locationId === location.locationId);
      const noShowCount = locationAppointments.filter((appointment) => appointment.status === "no_show").length;
      const scheduledAppointments = locationAppointments.length;
      const noShowRate = noShowRateByLocation(locationAppointments)[location.locationId] ?? 0;

      track("no_show_impact_calculated", {
        locationId: location.locationId,
        periodStart: "2025-03-08",
        periodEnd: asOfDate,
        scheduledAppointments,
        noShowCount,
        noShowRate,
        estimatedLostRevenue: calculateNoShowCost(sampleAppointments, location, asOfDate),
      });
    }
  }, [asOfDate]);

  return null;
}
