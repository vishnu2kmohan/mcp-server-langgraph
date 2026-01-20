/**
 * Schema Form Utilities
 *
 * Shared utilities for parsing JSON Schema to form fields.
 * Used by MCP tool invocation dialogs and inbound request modals.
 *
 * @example
 * ```tsx
 * import { parseSchemaToFields, getInputType } from '@/utils/schemaForm';
 *
 * const fields = parseSchemaToFields(tool.inputSchema);
 * fields.map(field => (
 *   <input
 *     type={getInputType(field.type)}
 *     required={field.required}
 *     defaultValue={field.defaultValue}
 *   />
 * ));
 * ```
 */

// =============================================================================
// Types
// =============================================================================

/**
 * JSON Schema property definition
 */
export interface JSONSchemaProperty {
  type?: string;
  description?: string;
  default?: unknown;
}

/**
 * JSON Schema structure (subset needed for form generation)
 */
export interface JSONSchema {
  properties?: Record<string, JSONSchemaProperty>;
  required?: string[];
}

/**
 * Parsed form field from JSON Schema
 */
export interface FormField {
  /** Field name (property key) */
  name: string;
  /** Field type (string, number, integer, boolean, etc.) */
  type: string;
  /** Field description for labels/hints */
  description?: string;
  /** Whether field is required */
  required: boolean;
  /** Default value from schema */
  defaultValue?: unknown;
}

// =============================================================================
// Functions
// =============================================================================

/**
 * Parse JSON Schema to extract form fields.
 *
 * Extracts properties from a JSON Schema and converts them to FormField
 * objects suitable for rendering form inputs.
 *
 * @param schema - JSON Schema object with properties
 * @returns Array of FormField objects
 */
export function parseSchemaToFields(schema: JSONSchema): FormField[] {
  if (!schema.properties) return [];

  const required = schema.required || [];

  return Object.entries(schema.properties).map(([name, prop]) => ({
    name,
    type: prop.type || "string",
    description: prop.description,
    required: required.includes(name),
    defaultValue: prop.default,
  }));
}

/**
 * Get HTML input type from JSON Schema type.
 *
 * Maps JSON Schema types to appropriate HTML input types.
 *
 * @param schemaType - JSON Schema type (string, number, integer, boolean, etc.)
 * @returns HTML input type attribute value
 */
export function getInputType(schemaType: string): string {
  switch (schemaType) {
    case "number":
    case "integer":
      return "number";
    case "boolean":
      return "checkbox";
    default:
      return "text";
  }
}
