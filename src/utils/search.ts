// Search functions for HealthCore collections

// Linear search: returns index of first match or -1
export function linearSearch<T>(array: T[], predicate: (item: T) => boolean): number {
  for (let i = 0; i < array.length; i++) {
    if (predicate(array[i])) return i;
  }
  return -1;
}

// Binary search: assumes array is sorted by the key
export function binarySearch<T>(array: T[], key: keyof T, value: T[keyof T]): number {
  let left = 0;
  let right = array.length - 1;
  while (left <= right) {
    const mid = Math.floor((left + right) / 2);
    if (array[mid][key] === value) return mid;
    if (array[mid][key] == null) return -1;
    if (array[mid][key] < value) left = mid + 1;
    else right = mid - 1;
  }
  return -1;
}
