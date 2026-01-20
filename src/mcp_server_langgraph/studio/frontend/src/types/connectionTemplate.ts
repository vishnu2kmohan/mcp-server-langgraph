/**
 * Connection Template Types
 *
 * Type definitions for MCP connection templates (ADR-0102).
 * Templates provide pre-configured settings for common MCP servers.
 *
 * Uses snake_case to match backend API responses.
 * RTK Query transforms to camelCase at runtime.
 */

import type { SnakeToCamelCaseDeep } from "../api/transforms";

// ==============================================================================
// Config Field Types
// ==============================================================================

/** Configuration field type for template setup forms */
export type ConfigFieldType = "text" | "password" | "url" | "textarea";

/** Configuration field definition for a template */
export interface ConfigField {
  name: string;
  label: string;
  type: ConfigFieldType;
  required: boolean;
  placeholder: string | null;
  description: string | null;
  default: string | null;
}

// ==============================================================================
// Template Types (snake_case - matches API)
// ==============================================================================

/** MCP connection template definition */
export interface ConnectionTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  auth_type: "none" | "api_key" | "oauth2";
  default_url: string;
  category: string;
  oauth2_scopes: string[];
  config_fields: ConfigField[];
  /** Keywords for intent matching in chat suggestions */
  keywords: string[];
  /** Popularity score 0-100 for sorting (higher = more popular) */
  popularity: number;
  /** Link to service documentation */
  documentation_url: string | null;
}

/** Template category */
export interface TemplateCategory {
  id: string;
  name: string;
  description: string;
}

// ==============================================================================
// Response Types (snake_case - matches API)
// ==============================================================================

/** Response for listing templates */
export interface TemplateListResponse {
  templates: ConnectionTemplate[];
}

/** Response for template suggestions */
export interface TemplateSuggestionsResponse {
  templates: ConnectionTemplate[];
  total: number;
}

/** Response for listing categories */
export interface CategoryListResponse {
  categories: TemplateCategory[];
}

// ==============================================================================
// CamelCase Type Aliases (for transformed RTK Query responses)
// ==============================================================================

/** ConfigField with camelCase keys (after RTK Query transformation) */
export type ConfigFieldCamelCase = SnakeToCamelCaseDeep<ConfigField>;

/** ConnectionTemplate with camelCase keys (after RTK Query transformation) */
export type ConnectionTemplateCamelCase =
  SnakeToCamelCaseDeep<ConnectionTemplate>;

/** TemplateCategory with camelCase keys (after RTK Query transformation) */
export type TemplateCategoryCamelCase = SnakeToCamelCaseDeep<TemplateCategory>;

/** TemplateListResponse with camelCase keys (after RTK Query transformation) */
export interface TemplateListResponseCamelCase {
  templates: ConnectionTemplateCamelCase[];
}

/** TemplateSuggestionsResponse with camelCase keys (after RTK Query transformation) */
export interface TemplateSuggestionsResponseCamelCase {
  templates: ConnectionTemplateCamelCase[];
  total: number;
}

/** CategoryListResponse with camelCase keys (after RTK Query transformation) */
export interface CategoryListResponseCamelCase {
  categories: TemplateCategoryCamelCase[];
}
