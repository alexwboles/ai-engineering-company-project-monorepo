"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.filterBy = filterBy;
exports.sortBy = sortBy;
exports.countBy = countBy;
exports.validatePatient = validatePatient;
// Filter by predicate
function filterBy(array, predicate) {
    return array.filter(predicate);
}
// Sort by key
function sortBy(array, key, ascending = true) {
    return [...array].sort((a, b) => {
        if (a[key] === b[key])
            return 0;
        if (a[key] == null)
            return 1;
        if (b[key] == null)
            return -1;
        if (a[key] < b[key])
            return ascending ? -1 : 1;
        return ascending ? 1 : -1;
    });
}
// Count by key
function countBy(array, key) {
    return array.reduce((acc, item) => {
        const k = String(item[key]);
        acc[k] = (acc[k] || 0) + 1;
        return acc;
    }, {});
}
// Validate patient object
function validatePatient(patient) {
    const errors = [];
    if (!patient.id)
        errors.push('Missing patient id');
    if (!patient.name)
        errors.push('Missing patient name');
    if (!patient.country)
        errors.push('Missing patient country');
    if (!patient.clinicId)
        errors.push('Missing clinicId');
    if (!patient.dateOfBirth)
        errors.push('Missing date of birth');
    if (!patient.language)
        errors.push('Missing language');
    return errors;
}
// Additional utilities for assignment goals will be added in utils/
