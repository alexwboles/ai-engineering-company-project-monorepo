// TypeScript version of healthcore-dashboard.js
import { Claim, Appointment, Clinician, Location } from './types/models';
import * as collections from './utils/collections';
import * as search from './utils/search';
import * as transformations from './utils/transformations';
import * as validations from './utils/validations';

// Sample data (typed)
export const sampleLocations: Location[] = [
	// ... (copy your sampleLocations from healthcore-dashboard.js here, typed)
];
export const sampleClaims: Claim[] = [
	// ... (copy your sampleClaims from healthcore-dashboard.js here, typed)
];
export const sampleAppointments: Appointment[] = [
	// ... (copy your sampleAppointments from healthcore-dashboard.js here, typed)
];
export const sampleClinicians: Clinician[] = [
	// ... (copy your sampleClinicians from healthcore-dashboard.js here, typed)
];

// Export utility functions for use in dashboard logic
export { collections, search, transformations, validations };

// All business logic and UI wiring from healthcore-dashboard.js can now use these imports and types
