"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.countBy = countBy;
exports.sumBy = sumBy;
exports.averageBy = averageBy;
function countBy(array, key) {
    return array.reduce((acc, item) => {
        const k = String(item[key]);
        acc[k] = (acc[k] || 0) + 1;
        return acc;
    }, {});
}
function sumBy(array, key) {
    return array.reduce((acc, item) => acc + (typeof item[key] === 'number' ? item[key] : 0), 0);
}
function averageBy(array, key) {
    const nums = array.map(item => (typeof item[key] === 'number' ? item[key] : 0));
    return nums.length === 0 ? 0 : nums.reduce((a, b) => a + b, 0) / nums.length;
}
