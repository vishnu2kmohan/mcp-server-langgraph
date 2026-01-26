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
  | "artifacts"
  | "skills"
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
  // Synced with backend user.py PERSONA_VISIBLE_MODULES
  admin: [
    // Core Work
    "projects",
    "chat",
    "workflows",
    // AI & Data
    "agents",
    "vectors",
    "connections",
    "artifacts",
    // Observability (includes traces tab)
    "observability",
    "cost",
    // Admin
    "admin",
    "skills",
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
    // Bottom items
    "help",
    "settings",
  ],
  // === ALICE PERSONAS (developer variants) ===
  // Synced with backend user.py PERSONA_VISIBLE_MODULES
  "alice-builder": [
    // Core Work
    "projects",
    "chat",
    "workflows",
    // AI & Data
    "agents",
    "vectors",
    "connections",
    "artifacts",
    // Observability (includes traces tab)
    "observability",
    "cost",
    // Bottom items
    "settings",
    "help",
  ],
  "alice-analyst": [
    // Core Work
    "projects",
    "chat",
    // Observability focus (includes traces tab)
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
    "connections",
    "observability",
    // Bottom items
    "settings",
    "help",
  ],
  // === BOB PERSONAS (end user) ===
  "compliance-officer": [
    // Compliance-focused access
    "audit",
    "compliance",
    // Bottom items
    "help",
    "settings",
  ],
  bob: [
    // Core Work only - limited access
    "projects",
    "chat",
    "workflows",
    // Observability (limited)
    "cost",
    // Bottom items
    "help",
    "settings",
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
    layout: { sessionNav: 10, conversation: 65, canvas: 25 },
    icon: "message-square",
  },
  {
    id: "focus-canvas",
    name: "Focus Canvas",
    description: "Expanded canvas panel",
    layout: { sessionNav: 10, conversation: 25, canvas: 65 },
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
    bg: "bg-error-1 dark:bg-error-12",
    text: "text-error-11 dark:text-error-9",
    border: "border-error-4 dark:border-error-11",
    badge: "bg-error-3 text-error-11 dark:bg-error-12 dark:text-error-4",
    hover: "hover:bg-error-3 dark:hover:bg-error-12",
    ring: "ring-error-7",
  },
  orange: {
    bg: "bg-grafana-1 dark:bg-grafana-12",
    text: "text-grafana-11 dark:text-grafana-4",
    border: "border-grafana-3 dark:border-grafana-11",
    badge:
      "bg-grafana-2 text-grafana-11 dark:bg-grafana-12 dark:text-grafana-3",
    hover: "hover:bg-grafana-2 dark:hover:bg-grafana-12",
    ring: "ring-grafana-9",
  },
  yellow: {
    bg: "bg-warning-3 dark:bg-warning-12",
    text: "text-warning-10 dark:text-warning-6",
    border: "border-warning-6 dark:border-warning-11",
    badge:
      "bg-warning-3 text-warning-11 dark:bg-warning-12 dark:text-warning-6",
    hover: "hover:bg-warning-3 dark:hover:bg-warning-12",
    ring: "ring-warning-7",
  },
  blue: {
    bg: "bg-primary-1 dark:bg-primary-12",
    text: "text-primary-11 dark:text-primary-5",
    border: "border-primary-4 dark:border-primary-11",
    badge:
      "bg-primary-3 text-primary-11 dark:bg-primary-12 dark:text-primary-4",
    hover: "hover:bg-primary-3 dark:hover:bg-primary-12",
    ring: "ring-primary-7",
  },
  purple: {
    bg: "bg-insight-1 dark:bg-insight-12",
    text: "text-insight-11 dark:text-insight-5",
    border: "border-insight-4 dark:border-insight-11",
    badge:
      "bg-insight-2 text-insight-11 dark:bg-insight-12 dark:text-insight-4",
    hover: "hover:bg-insight-2 dark:hover:bg-insight-12",
    ring: "ring-insight-7",
  },
  cyan: {
    bg: "bg-info-1 dark:bg-info-12",
    text: "text-info-10 dark:text-info-5",
    border: "border-info-4 dark:border-info-11",
    badge: "bg-info-3 text-info-11 dark:bg-info-12 dark:text-info-4",
    hover: "hover:bg-info-3 dark:hover:bg-info-12",
    ring: "ring-info-7",
  },
  teal: {
    bg: "bg-info-2 dark:bg-info-12",
    text: "text-info-11 dark:text-info-5",
    border: "border-info-4 dark:border-info-12",
    badge: "bg-info-3 text-info-12 dark:bg-info-12 dark:text-info-4",
    hover: "hover:bg-info-3 dark:hover:bg-info-12",
    ring: "ring-info-9",
  },
  green: {
    bg: "bg-success-1 dark:bg-success-12",
    text: "text-success-11 dark:text-success-5",
    border: "border-success-4 dark:border-success-11",
    badge:
      "bg-success-3 text-success-11 dark:bg-success-12 dark:text-success-4",
    hover: "hover:bg-success-3 dark:hover:bg-success-12",
    ring: "ring-success-7",
  },
};

const DEFAULT_THEME: PersonaTheme = {
  bg: "bg-neutral-1",
  text: "text-neutral-11",
  border: "border-neutral-5",
  badge:
    "bg-neutral-2 text-neutral-12",
  hover: "hover:bg-neutral-2",
  ring: "ring-neutral-8",
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
