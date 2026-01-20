/**
 * Form Error Messages
 *
 * Standardized, accessible error messages for form validation.
 * These messages are specific and actionable (WCAG 3.3.3 compliant).
 *
 * @example
 * import { ERROR_MESSAGES } from '@/utils/form-errors';
 *
 * const schema = z.object({
 *   email: z.string()
 *     .min(1, ERROR_MESSAGES.required('Email'))
 *     .email(ERROR_MESSAGES.email),
 * });
 */

// =============================================================================
// Error Message Generators
// =============================================================================

/**
 * Standard error messages for common validation scenarios.
 * All messages are:
 * - Specific: Tell the user exactly what's wrong
 * - Actionable: Suggest how to fix the problem
 * - Accessible: Use clear, simple language
 */
export const ERROR_MESSAGES = {
  /**
   * Required field error
   * @param field - Human-readable field name (e.g., "Email", "Password")
   */
  required: (field: string) => `${field} is required`,

  /**
   * Invalid email format
   */
  email: "Please enter a valid email address",

  /**
   * Minimum length not met
   * @param field - Human-readable field name
   * @param min - Minimum required length
   */
  minLength: (field: string, min: number) =>
    `${field} must be at least ${min} characters`,

  /**
   * Maximum length exceeded
   * @param field - Human-readable field name
   * @param max - Maximum allowed length
   */
  maxLength: (field: string, max: number) =>
    `${field} must be ${max} characters or less`,

  /**
   * Value outside allowed range
   * @param field - Human-readable field name
   * @param min - Minimum allowed value
   * @param max - Maximum allowed value
   */
  range: (field: string, min: number, max: number) =>
    `${field} must be between ${min} and ${max}`,

  /**
   * Pattern mismatch
   * @param field - Human-readable field name
   * @param hint - What the pattern expects (e.g., "must include a number")
   */
  pattern: (field: string, hint: string) => `${field} ${hint}`,

  /**
   * Fields don't match (e.g., password confirmation)
   * @param field1 - First field name
   * @param field2 - Second field name
   */
  match: (field1: string, field2: string) =>
    `${field1} must match ${field2}`,

  /**
   * Value already exists (uniqueness constraint)
   * @param field - Human-readable field name
   */
  unique: (field: string) =>
    `This ${field.toLowerCase()} is already taken`,

  /**
   * Invalid URL format
   */
  url: "Please enter a valid URL",

  /**
   * Invalid phone number format
   */
  phone: "Please enter a valid phone number",

  /**
   * Invalid date format
   */
  date: "Please enter a valid date",

  /**
   * Date in the past when future date required
   */
  futureDate: "Date must be in the future",

  /**
   * Date in the future when past date required
   */
  pastDate: "Date must be in the past",

  /**
   * Numeric value required
   */
  number: "Please enter a valid number",

  /**
   * Integer value required
   */
  integer: "Please enter a whole number",

  /**
   * Positive value required
   */
  positive: (field: string) => `${field} must be a positive number`,

  /**
   * File too large
   * @param maxSize - Maximum file size in human-readable format (e.g., "5MB")
   */
  fileSize: (maxSize: string) => `File size must be less than ${maxSize}`,

  /**
   * Invalid file type
   * @param allowedTypes - Comma-separated list of allowed types
   */
  fileType: (allowedTypes: string) =>
    `File type must be one of: ${allowedTypes}`,

  /**
   * Selection required (for dropdowns, radio groups)
   * @param field - Human-readable field name
   */
  select: (field: string) => `Please select a ${field.toLowerCase()}`,

  /**
   * Checkbox must be checked (for terms, agreements)
   */
  checkbox: (field: string) => `You must agree to the ${field.toLowerCase()}`,

  /**
   * Too many items selected
   * @param max - Maximum number of items allowed
   */
  maxItems: (max: number) => `You can select up to ${max} items`,

  /**
   * Too few items selected
   * @param min - Minimum number of items required
   */
  minItems: (min: number) =>
    `Please select at least ${min} item${min === 1 ? "" : "s"}`,
} as const;

// =============================================================================
// Password Validation Messages
// =============================================================================

/**
 * Password-specific error messages for common requirements.
 */
export const PASSWORD_ERRORS = {
  tooShort: ERROR_MESSAGES.minLength("Password", 8),
  noUppercase: ERROR_MESSAGES.pattern("Password", "must include an uppercase letter"),
  noLowercase: ERROR_MESSAGES.pattern("Password", "must include a lowercase letter"),
  noNumber: ERROR_MESSAGES.pattern("Password", "must include a number"),
  noSpecial: ERROR_MESSAGES.pattern("Password", "must include a special character (!@#$%^&*)"),
  common: "This password is too common. Please choose a stronger password.",
  compromised: "This password has been exposed in a data breach. Please choose a different password.",
} as const;

// =============================================================================
// Username Validation Messages
// =============================================================================

/**
 * Username-specific error messages.
 */
export const USERNAME_ERRORS = {
  tooShort: ERROR_MESSAGES.minLength("Username", 3),
  tooLong: ERROR_MESSAGES.maxLength("Username", 30),
  invalidChars: ERROR_MESSAGES.pattern("Username", "can only contain letters, numbers, and underscores"),
  startsWithNumber: ERROR_MESSAGES.pattern("Username", "must start with a letter"),
  reserved: "This username is not available",
  taken: ERROR_MESSAGES.unique("Username"),
} as const;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Formats a list of field errors into a human-readable summary.
 * Useful for screen reader announcements.
 *
 * @param errors - Record of field names to error messages
 * @returns Formatted error summary string
 *
 * @example
 * formatErrorSummary({ email: "Invalid email", password: "Too short" })
 * // Returns: "2 errors found: Email: Invalid email. Password: Too short."
 */
export function formatErrorSummary(errors: Record<string, string>): string {
  const entries = Object.entries(errors);
  if (entries.length === 0) return "";

  const count = entries.length;
  const errorList = entries
    .map(([field, message]) => `${capitalize(field)}: ${message}`)
    .join(". ");

  return `${count} error${count === 1 ? "" : "s"} found: ${errorList}.`;
}

/**
 * Capitalizes the first letter of a string.
 */
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Combines multiple error messages into a single string.
 * Useful when a field has multiple validation rules.
 *
 * @param messages - Array of error messages
 * @returns Combined error message
 *
 * @example
 * combineErrors(["Must be 8+ characters", "Must include a number"])
 * // Returns: "Must be 8+ characters. Must include a number."
 */
export function combineErrors(messages: string[]): string {
  return messages.filter(Boolean).join(". ");
}

// =============================================================================
// Type Exports
// =============================================================================

export type ErrorMessageKey = keyof typeof ERROR_MESSAGES;
export type PasswordErrorKey = keyof typeof PASSWORD_ERRORS;
export type UsernameErrorKey = keyof typeof USERNAME_ERRORS;
