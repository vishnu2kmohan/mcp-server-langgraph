/**
 * Skills Types
 *
 * Type definitions for the Skills Marketplace feature.
 * Includes types for skills, marketplaces, and API request/response shapes.
 *
 * @see SkillsPage.tsx - Main consumer of these types
 * @see api/index.ts - RTK Query endpoints using these types
 */

// =============================================================================
// Marketplace Types
// =============================================================================

/** Supported marketplace types */
export type MarketplaceType = "github" | "oci" | "registry";

/** Marketplace configuration information */
export interface MarketplaceInfo {
  /** Unique marketplace identifier */
  name: string;
  /** Marketplace URI (GitHub URL, OCI registry, or REST API URL) */
  uri: string;
  /** Type of marketplace */
  type: MarketplaceType;
  /** Whether skills from this marketplace are trusted */
  trusted: boolean;
  /** Whether to automatically sync skills from this marketplace */
  autoSync: boolean;
  /** Whether skills require admin approval before use */
  requiresApproval: boolean;
}

// =============================================================================
// Skill Types
// =============================================================================

/** Metadata for a skill in the marketplace */
export interface SkillMetadata {
  /** Unique skill name */
  name: string;
  /** Human-readable description */
  description: string;
  /** Semantic version string (e.g., "1.0.0") */
  version: string;
  /** Optional author name */
  author?: string;
  /** Tags for categorization and filtering */
  tags: string[];
  /** Source marketplace name */
  source?: string;
}

/** Information about an available skill update */
export interface SkillUpdate {
  /** Name of the skill with an update */
  skillName: string;
  /** Currently installed version */
  currentVersion: string;
  /** Available new version */
  newVersion: string;
  /** Source marketplace */
  marketplace: string;
  /** Optional changelog/release notes */
  changelog?: string;
}

// =============================================================================
// API Request Types
// =============================================================================

/** Parameters for listing marketplace skills */
export interface ListMarketplaceSkillsParams {
  /** Search query to filter skills by name/description */
  search?: string;
  /** Marketplace to query (default: "anthropic") */
  marketplace?: string;
  /** Tags to filter by */
  tags?: string[];
  /** Maximum number of results */
  limit?: number;
  /** Minimum semantic similarity score for search (0-1) */
  min_score?: number;
}

/** Parameters for installing a skill */
export interface InstallSkillParams {
  /** Name of the skill to install */
  skillName: string;
  /** Marketplace to install from (default: "anthropic") */
  marketplace?: string;
  /** Specific version to install (default: latest) */
  version?: string;
}

// =============================================================================
// API Response Types
// =============================================================================

/** Response from listing marketplace skills */
export interface ListMarketplaceSkillsResponse {
  /** Array of skill metadata */
  skills: SkillMetadata[];
  /** Total number of matching skills */
  total: number;
  /** Marketplace that was queried */
  marketplace: string;
  /** Whether the result was served from cache */
  cached: boolean;
}

/** Response from listing installed skills */
export interface ListInstalledSkillsResponse {
  /** Array of installed skill names */
  skills: string[];
  /** Total count of installed skills */
  count: number;
}

/** Result of a single skill update */
export interface SkillUpdateResult {
  /** Name of the skill that was updated */
  skillName: string;
  /** Whether the update succeeded */
  success: boolean;
  /** Error message if update failed */
  error?: string;
  /** New version if update succeeded */
  newVersion?: string;
}

/** Response from applying skill updates */
export interface ApplySkillUpdatesResponse {
  /** Number of updates successfully applied */
  applied: number;
  /** Results for each skill update attempt */
  results: SkillUpdateResult[];
}

// =============================================================================
// UI State Types
// =============================================================================

/** Active tab in the Skills page */
export type SkillsTab = "browse" | "installed" | "updates";

/** Installation status for a skill */
export type InstallationStatus = "idle" | "installing" | "installed" | "error";

/** Filter state for the skills browser */
export interface SkillsFilterState {
  /** Search query */
  searchQuery: string;
  /** Selected tags */
  selectedTags: string[];
  /** Selected marketplace */
  marketplace: string;
}
