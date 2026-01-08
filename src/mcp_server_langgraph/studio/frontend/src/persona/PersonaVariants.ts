/**
 * PersonaVariants - Phase 2
 *
 * Defines the 8 sub-persona variants with their
 * configurations, permissions, and default views.
 */
import type { Persona } from "./PersonaSwitcher";
import type { WorkspacePreset } from "./WorkspacePresets";

// =============================================================================
// Persona Definitions (8 variants)
// =============================================================================

export const PERSONA_VARIANTS: Persona[] = [
  // Admin personas
  {
    id: "admin",
    name: "Admin",
    role: "admin",
    description: "Full system access and control",
    icon: "shield",
    color: "red",
  },
  {
    id: "security-admin",
    name: "Security Admin",
    role: "admin",
    description: "Security-focused administration with FedRAMP/SOC-2 focus",
    icon: "shield-alert",
    color: "orange",
    parentId: "admin",
  },
  {
    id: "auditor",
    name: "Auditor",
    role: "admin",
    description: "Audit logs, compliance, and reports access",
    icon: "clipboard-check",
    color: "yellow",
    parentId: "admin",
  },

  // Developer personas
  {
    id: "alice-builder",
    name: "Alice Builder",
    role: "developer",
    description: "Workflow development with Chat, Flows, MCP, Agents",
    icon: "code",
    color: "blue",
  },
  {
    id: "alice-analyst",
    name: "Alice Analyst",
    role: "developer",
    description: "Data analysis with Chat, Traces, Costs, Metrics",
    icon: "bar-chart",
    color: "purple",
    parentId: "alice-builder",
  },
  {
    id: "alice-devops",
    name: "Alice DevOps",
    role: "developer",
    description: "Deployments with Chat, MCP, Connections, Traces",
    icon: "server",
    color: "cyan",
    parentId: "alice-builder",
  },
  {
    id: "compliance-officer",
    name: "Compliance Officer",
    role: "developer",
    description: "Audit, HIPAA/GDPR/SOC-2 compliance views",
    icon: "clipboard-check",
    color: "teal",
    parentId: "alice-builder",
  },

  // User personas
  {
    id: "bob",
    name: "Bob",
    role: "user",
    description: "Standard user access to Chat, Projects, Shared Flows",
    icon: "user",
    color: "green",
  },
];

// =============================================================================
// Persona → OpenFGA Tuple Mapping
// =============================================================================

export interface OpenFGATuple {
  user: string;
  relation: string;
  object: string;
}

export const PERSONA_OPENFGA_MAPPINGS: Record<string, OpenFGATuple[]> = {
  admin: [{ user: "user:X", relation: "admin", object: "system:global" }],
  "security-admin": [
    { user: "user:X", relation: "admin", object: "system:global" },
    { user: "user:X", relation: "member", object: "role:security" },
  ],
  auditor: [
    { user: "user:X", relation: "viewer", object: "system:global" },
    { user: "user:X", relation: "member", object: "role:audit" },
  ],
  "alice-builder": [
    { user: "user:X", relation: "developer", object: "system:global" },
  ],
  "alice-analyst": [
    { user: "user:X", relation: "developer", object: "system:global" },
    { user: "user:X", relation: "member", object: "role:analyst" },
  ],
  "alice-devops": [
    { user: "user:X", relation: "developer", object: "system:global" },
    { user: "user:X", relation: "member", object: "role:devops" },
  ],
  "compliance-officer": [
    { user: "user:X", relation: "developer", object: "system:global" },
    { user: "user:X", relation: "member", object: "role:compliance" },
  ],
  bob: [{ user: "user:X", relation: "user", object: "system:global" }],
};

// =============================================================================
// Persona → Visible Modules Mapping
// =============================================================================

/**
 * ModuleId - All possible module IDs that can appear in navigation.
 *
 * These IDs must match the NAV_ITEMS and BOTTOM_ITEMS in ActivityBar.tsx.
 * Use normalized IDs: 'workflows' (not 'flows'), 'cost' (not 'costs').
 */
export type ModuleId =
  // Core Work
  | "projects"
  | "chat"
  | "workflows"
  // AI & Data
  | "agents"
  | "mcp"
  | "vectors"
  | "connections"
  | "files"
  // Observability
  | "traces"
  | "observability"
  | "cost"
  // Admin
  | "admin"
  | "audit"
  | "compliance"
  // Bottom items
  | "help"
  | "settings";

/**
 * PERSONA_VISIBLE_MODULES - Client-side fallback for visible modules.
 *
 * NOTE: The server (user.py PERSONA_VISIBLE_MODULES) is the source of truth.
 * This is only used as a fallback when server data is unavailable.
 * Uses normalized IDs: 'workflows' (not 'flows'), 'cost' (not 'costs').
 */
export const PERSONA_VISIBLE_MODULES: Record<string, ModuleId[]> = {
  // === ADMIN PERSONAS (full platform access) ===
  admin: [
    // Core Work
    "projects",
    "chat",
    "workflows",
    // AI & Data
    "agents",
    "mcp",
    "vectors",
    "files",
    // Observability
    "traces",
    "observability",
    "cost",
    // Admin
    "admin",
    "audit",
    "compliance",
    // Bottom items
    "settings",
    "help",
  ],
  "security-admin": [
    // Admin-focused access
    "admin",
    "audit",
    "compliance",
    "settings",
    "help",
  ],
  auditor: [
    // Audit-only access
    "audit",
    "compliance",
    "help",
  ],
  // === ALICE PERSONAS (developer variants) ===
  "alice-builder": [
    // Core Work
    "projects",
    "chat",
    "workflows",
    // AI & Data
    "agents",
    "mcp",
    "vectors",
    "files",
    // Observability
    "traces",
    "cost",
    // Bottom items
    "settings",
    "help",
  ],
  "alice-analyst": [
    // Core Work
    "projects",
    "chat",
    // Observability focus
    "traces",
    "observability",
    "cost",
    // Bottom items
    "settings",
    "help",
  ],
  "alice-devops": [
    // Core Work
    "projects",
    "chat",
    // Infrastructure focus
    "agents",
    "mcp",
    "connections",
    "traces",
    // Bottom items
    "settings",
    "help",
  ],
  // === BOB PERSONAS (end user) ===
  "compliance-officer": [
    // Compliance-focused access
    "audit",
    "compliance",
    "help",
  ],
  bob: [
    // Core Work only - limited access
    "projects",
    "chat",
    "workflows",
    "help",
  ],
};

// =============================================================================
// Persona → Default View Mapping
// =============================================================================

export const PERSONA_DEFAULT_VIEW: Record<string, string> = {
  // Base personas
  admin: "/studio/admin",
  developer: "/studio/workflows",
  user: "/studio/chat",
  // Sub-personas with specific default views
  "security-admin": "/studio/compliance",
  auditor: "/studio/audit",
  "alice-builder": "/studio/chat",
  "alice-analyst": "/studio/observability",
  "alice-devops": "/studio/connections",
  "compliance-officer": "/studio/compliance",
  bob: "/studio/chat",
};

// =============================================================================
// Default Workspace Presets per Persona
// =============================================================================

export const DEFAULT_PRESETS: WorkspacePreset[] = [
  {
    id: "default",
    name: "Default Layout",
    description: "Standard chat + canvas layout",
    layout: { sessionNav: 20, conversation: 40, canvas: 40 },
    icon: "layout",
  },
  {
    id: "focus-chat",
    name: "Focus Chat",
    description: "Expanded conversation panel",
    layout: { sessionNav: 15, conversation: 60, canvas: 25 },
    icon: "message-square",
  },
  {
    id: "focus-canvas",
    name: "Focus Canvas",
    description: "Expanded canvas panel",
    layout: { sessionNav: 15, conversation: 25, canvas: 60 },
    icon: "code",
  },
  {
    id: "minimal",
    name: "Minimal",
    description: "Collapsed navigation",
    layout: { sessionNav: 0, conversation: 50, canvas: 50 },
    icon: "minimize",
  },
];

export const PERSONA_DEFAULT_PRESET: Record<string, string> = {
  admin: "default",
  "security-admin": "default",
  auditor: "minimal",
  "alice-builder": "focus-canvas",
  "alice-analyst": "focus-chat",
  "alice-devops": "default",
  "compliance-officer": "minimal",
  bob: "focus-chat",
};

// =============================================================================
// Persona Theme Types
// =============================================================================

/**
 * Theme configuration for persona-specific styling.
 * Uses Tailwind CSS classes for consistent theming.
 */
export interface PersonaTheme {
  /** Background color class */
  bg: string;
  /** Text color class */
  text: string;
  /** Border color class */
  border: string;
  /** Badge/accent color class */
  badge: string;
  /** Hover state class */
  hover: string;
  /** Ring/focus state class */
  ring: string;
}

/**
 * Theme configurations mapped to persona colors.
 */
const PERSONA_THEMES: Record<string, PersonaTheme> = {
  red: {
    bg: "bg-error-50 dark:bg-error-950",
    text: "text-error-700 dark:text-error-300",
    border: "border-error-200 dark:border-error-800",
    badge: "bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200",
    hover: "hover:bg-error-100 dark:hover:bg-error-900",
    ring: "ring-error-500",
  },
  orange: {
    bg: "bg-grafana-50 dark:bg-grafana-950",
    text: "text-grafana-700 dark:text-grafana-300",
    border: "border-grafana-200 dark:border-grafana-800",
    badge:
      "bg-grafana-100 text-grafana-800 dark:bg-grafana-900 dark:text-grafana-200",
    hover: "hover:bg-grafana-100 dark:hover:bg-grafana-900",
    ring: "ring-grafana-500",
  },
  yellow: {
    bg: "bg-warning-50 dark:bg-warning-950",
    text: "text-warning-700 dark:text-warning-300",
    border: "border-warning-200 dark:border-warning-800",
    badge:
      "bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200",
    hover: "hover:bg-warning-100 dark:hover:bg-warning-900",
    ring: "ring-warning-500",
  },
  blue: {
    bg: "bg-primary-50 dark:bg-primary-950",
    text: "text-primary-700 dark:text-primary-300",
    border: "border-primary-200 dark:border-primary-800",
    badge:
      "bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200",
    hover: "hover:bg-primary-100 dark:hover:bg-primary-900",
    ring: "ring-primary-500",
  },
  purple: {
    bg: "bg-insight-50 dark:bg-insight-950",
    text: "text-insight-700 dark:text-insight-300",
    border: "border-insight-200 dark:border-insight-800",
    badge:
      "bg-insight-100 text-insight-800 dark:bg-insight-900 dark:text-insight-200",
    hover: "hover:bg-insight-100 dark:hover:bg-insight-900",
    ring: "ring-insight-500",
  },
  cyan: {
    bg: "bg-info-50 dark:bg-info-950",
    text: "text-info-700 dark:text-info-300",
    border: "border-info-200 dark:border-info-800",
    badge: "bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-200",
    hover: "hover:bg-info-100 dark:hover:bg-info-900",
    ring: "ring-info-500",
  },
  teal: {
    bg: "bg-teal-50 dark:bg-teal-950",
    text: "text-teal-700 dark:text-teal-300",
    border: "border-teal-200 dark:border-teal-800",
    badge: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200",
    hover: "hover:bg-teal-100 dark:hover:bg-teal-900",
    ring: "ring-teal-500",
  },
  green: {
    bg: "bg-success-50 dark:bg-success-950",
    text: "text-success-700 dark:text-success-300",
    border: "border-success-200 dark:border-success-800",
    badge:
      "bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200",
    hover: "hover:bg-success-100 dark:hover:bg-success-900",
    ring: "ring-success-500",
  },
};

const DEFAULT_THEME: PersonaTheme = {
  bg: "bg-gray-50 dark:bg-gray-950",
  text: "text-gray-700 dark:text-gray-300",
  border: "border-gray-200 dark:border-gray-800",
  badge: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
  hover: "hover:bg-gray-100 dark:hover:bg-gray-900",
  ring: "ring-gray-500",
};

/**
 * Get theme configuration for a persona.
 *
 * @param personaId - The persona ID to get theme for
 * @returns PersonaTheme with Tailwind classes
 */
export function getPersonaTheme(personaId: string): PersonaTheme {
  const persona = getPersonaById(personaId);
  if (!persona?.color) return DEFAULT_THEME;
  return PERSONA_THEMES[persona.color] ?? DEFAULT_THEME;
}

// =============================================================================
// Utility Functions
// =============================================================================

export function getPersonaById(id: string): Persona | undefined {
  return PERSONA_VARIANTS.find((p) => p.id === id);
}

export function getPersonasByRole(role: Persona["role"]): Persona[] {
  return PERSONA_VARIANTS.filter((p) => p.role === role);
}

export function getVisibleModules(personaId: string): ModuleId[] {
  return PERSONA_VISIBLE_MODULES[personaId] || [];
}

export function getDefaultView(personaId: string): string {
  return PERSONA_DEFAULT_VIEW[personaId] || "/studio/chat";
}

export function getDefaultPreset(personaId: string): WorkspacePreset {
  const presetId = PERSONA_DEFAULT_PRESET[personaId] || "default";
  const preset = DEFAULT_PRESETS.find((p) => p.id === presetId);
  if (preset) return preset;
  const fallback = DEFAULT_PRESETS[0];
  if (fallback) return fallback;
  // Fallback to a minimal preset if array is somehow empty
  return {
    id: "default",
    name: "Default",
    description: "",
    layout: { sessionNav: 20, conversation: 50, canvas: 30 },
    icon: "layout",
  };
}
