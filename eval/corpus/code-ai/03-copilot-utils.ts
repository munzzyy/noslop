/**
 * A collection of utility functions for common data operations.
 */

/**
 * Capitalizes the first letter of a string.
 * @param str - The string to capitalize.
 * @returns The capitalized string.
 */
export function capitalize(str: string): string {
  // Return the string with the first letter capitalized
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Checks if a value is null or undefined.
 * @param value - The value to check.
 * @returns True if the value is null or undefined.
 */
export function isNullOrUndefined(value: unknown): boolean {
  return value === null || value === undefined;
}

/**
 * Formats a date as a YYYY-MM-DD string.
 * @param date - The date to format.
 * @returns The formatted date string.
 */
export function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  // Combine the parts into the final string
  return `${year}-${month}-${day}`;
}

/**
 * Splits an array into chunks of the specified size.
 * @param array - The array to split.
 * @param size - The size of each chunk.
 * @returns An array of chunks.
 */
export function chunkArray<T>(array: T[], size: number): T[][] {
  const result: T[][] = [];
  // Iterate over the array in steps of the chunk size
  for (let i = 0; i < array.length; i += size) {
    // Slice the current chunk and add it to the result
    result.push(array.slice(i, i + size));
  }
  return result;
}

/**
 * Debounces a function call.
 * @param fn - The function to debounce.
 * @param delay - The delay in milliseconds.
 * @returns The debounced function.
 */
export function debounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    // Clear the previous timeout
    clearTimeout(timeoutId);
    // Set a new timeout to call the function after the delay
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Generates a random ID string.
 * @returns A random ID string.
 */
export function generateId(): string {
  // Generate a random string using Math.random
  return Math.random().toString(36).substring(2, 15);
}
