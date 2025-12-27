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
