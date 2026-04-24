"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.linearSearch = linearSearch;
exports.binarySearch = binarySearch;
// Search utilities for HealthCore
function linearSearch(array, predicate) {
    for (let i = 0; i < array.length; i++) {
        if (predicate(array[i]))
            return i;
    }
    return -1;
}
function binarySearch(array, key, value) {
    let left = 0;
    let right = array.length - 1;
    while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (array[mid][key] === value)
            return mid;
        if (array[mid][key] == null)
            return -1;
        if (array[mid][key] < value)
            left = mid + 1;
        else
            right = mid - 1;
    }
    return -1;
}
