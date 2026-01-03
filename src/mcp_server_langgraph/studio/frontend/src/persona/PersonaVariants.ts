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
  admin: "/studio/admin",
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
    bg: "bg-red-50 dark:bg-red-950",
    text: "text-red-700 dark:text-red-300",
    border: "border-red-200 dark:border-red-800",
    badge: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    hover: "hover:bg-red-100 dark:hover:bg-red-900",
    ring: "ring-red-500",
  },
  orange: {
    bg: "bg-orange-50 dark:bg-orange-950",
    text: "text-orange-700 dark:text-orange-300",
    border: "border-orange-200 dark:border-orange-800",
    badge:
      "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    hover: "hover:bg-orange-100 dark:hover:bg-orange-900",
    ring: "ring-orange-500",
  },
  yellow: {
    bg: "bg-yellow-50 dark:bg-yellow-950",
    text: "text-yellow-700 dark:text-yellow-300",
    border: "border-yellow-200 dark:border-yellow-800",
    badge:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    hover: "hover:bg-yellow-100 dark:hover:bg-yellow-900",
    ring: "ring-yellow-500",
  },
  blue: {
    bg: "bg-blue-50 dark:bg-blue-950",
    text: "text-blue-700 dark:text-blue-300",
    border: "border-blue-200 dark:border-blue-800",
    badge: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    hover: "hover:bg-blue-100 dark:hover:bg-blue-900",
    ring: "ring-blue-500",
  },
  purple: {
    bg: "bg-purple-50 dark:bg-purple-950",
    text: "text-purple-700 dark:text-purple-300",
    border: "border-purple-200 dark:border-purple-800",
    badge:
      "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    hover: "hover:bg-purple-100 dark:hover:bg-purple-900",
    ring: "ring-purple-500",
  },
  cyan: {
    bg: "bg-cyan-50 dark:bg-cyan-950",
    text: "text-cyan-700 dark:text-cyan-300",
    border: "border-cyan-200 dark:border-cyan-800",
    badge: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
    hover: "hover:bg-cyan-100 dark:hover:bg-cyan-900",
    ring: "ring-cyan-500",
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
    bg: "bg-green-50 dark:bg-green-950",
    text: "text-green-700 dark:text-green-300",
    border: "border-green-200 dark:border-green-800",
    badge: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    hover: "hover:bg-green-100 dark:hover:bg-green-900",
    ring: "ring-green-500",
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
