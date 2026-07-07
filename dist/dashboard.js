// Compiled dashboard.js for browser use
import { Claim, Appointment, Clinician, Location } from './types/models.js';
import * as collections from './utils/collections.js';
import * as search from './utils/search.js';
import * as transformations from './utils/transformations.js';
import * as validations from './utils/validations.js';

// ...rest of the code copied from src/dashboard.js, but with .js imports

// --- Sample Data ---
const sampleClaims = [
  {
    claimId: 'C001', patientId: 'P001', locationId: 'L001', serviceType: 'primary_care', payerName: 'Aetna', payerId: 'PAY001', submissionDate: '2024-04-01', claimAmount: 120, status: 'approved', resubmitted: false
  },
  {
    claimId: 'C002', patientId: 'P002', locationId: 'L002', serviceType: 'chronic_disease', payerName: 'United', payerId: 'PAY002', submissionDate: '2024-04-02', claimAmount: 200, status: 'denied', denialReason: 'coding_error', resubmitted: true
  }
];

const sampleAppointments = [
  {
    appointmentId: 'A001', patientId: 'P001', locationId: 'L001', serviceType: 'primary_care', scheduledDate: '2024-04-10', scheduledTime: '09:00', status: 'completed'
  },
  {
    appointmentId: 'A002', patientId: 'P002', locationId: 'L002', serviceType: 'chronic_disease', scheduledDate: '2024-04-11', scheduledTime: '10:00', status: 'no_show', noShowReason: 'transportation'
  }
];

const sampleClinicians = [
  {
    clinicianId: 'CL001', firstName: 'Alice', lastName: 'Smith', role: 'physician', locationId: 'L001', licenceState: 'NY', licenceExpiryDate: '2025-12-31', cmeHoursRequired: 50, cmeHoursLogged: 40, cmeYearStartDate: '2024-01-01'
  },
  {
    clinicianId: 'CL002', firstName: 'Bob', lastName: 'Jones', role: 'nurse', locationId: 'L002', licenceState: 'NJ', licenceExpiryDate: '2024-09-30', cmeHoursRequired: 30, cmeHoursLogged: 30, cmeYearStartDate: '2024-01-01'
  }
];

const sampleLocations = [
  {
    locationId: 'L001', name: 'HealthCore NY', city: 'New York', stateOrCountry: 'NY', country: 'US', phone: '555-1234', averageConsultationFee: { primary_care: 120, chronic_disease: 200, preventive: 100, specialist: 250, womens_health: 180, paediatric: 160, mental_health: 220 }
  },
  {
    locationId: 'L002', name: 'HealthCore NJ', city: 'Jersey City', stateOrCountry: 'NJ', country: 'US', phone: '555-5678', averageConsultationFee: { primary_care: 110, chronic_disease: 190, preventive: 90, specialist: 240, womens_health: 170, paediatric: 150, mental_health: 210 }
  }
];

// ...rest of the UI rendering code as in src/dashboard.js

window.renderSampleDataUI = function renderSampleDataUI() { /* ... */ };
window.renderAnalyticsUI = function renderAnalyticsUI() { /* ... */ };
window.renderValidationUI = function renderValidationUI() { /* ... */ };

window.renderSampleDataUI();
window.renderAnalyticsUI();
window.renderValidationUI();
