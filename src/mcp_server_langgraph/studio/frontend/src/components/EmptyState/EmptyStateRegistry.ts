/**
 * EmptyStateRegistry
 *
 * A registry of persona-specific empty state configurations.
 * Maps context + persona to appropriate messaging based on Fogg Behavior Model.
 *
 * Each entry provides:
 * - title: What's empty
 * - motivation: Why user should act (Fogg: Motivation)
 * - ability: How easy it is (Fogg: Ability - optional)
 * - action: Suggested action for CTA (Fogg: Trigger)
 * - target: Navigation target or modal to open
 */

import type { EmptyStateContext } from "./EmptyState";

/**
 * Persona types supported in the system
 */
export type Persona =
  | "admin"
  | "security-admin"
  | "auditor"
  | "alice-builder"
  | "alice-analyst"
  | "alice-devops"
  | "compliance-officer"
  | "bob"
  | "default";

/**
 * Empty state configuration entry
 */
export interface EmptyStateConfig {
  /** Main title */
  title: string;
  /** Motivation text (Fogg: Motivation) */
  motivation: string;
  /** Optional ability indicator (Fogg: Ability) */
  ability?: string;
  /** Primary action label */
  action: string;
  /** Navigation target or modal ID */
  target: string;
  /** Optional secondary action label */
  secondaryAction?: string;
  /** Optional secondary target */
  secondaryTarget?: string;
}

/**
 * Default configurations (used when no persona-specific config exists)
 */
const DEFAULT_CONFIGS: Record<EmptyStateContext, EmptyStateConfig> = {
  sessions: {
    title: "No sessions yet",
    motivation: "Start a conversation to see your sessions here",
    ability: "Takes less than a minute",
    action: "Start Chat",
    target: "/studio/chat/new",
  },
  projects: {
    title: "No projects",
    motivation: "Organize your work into projects for better management",
    ability: "Quick setup",
    action: "Create Project",
    target: "/studio/projects/new",
  },
  workflows: {
    title: "No workflows",
    motivation: "Build automated workflows to streamline your tasks",
    ability: "Use templates to get started quickly",
    action: "Create Workflow",
    target: "/studio/workflows/new",
    secondaryAction: "Browse Templates",
    secondaryTarget: "/studio/workflows/templates",
  },
  traces: {
    title: "No traces available",
    motivation: "Run workflows to see execution traces here",
    action: "View Workflows",
    target: "/studio/workflows",
  },
  messages: {
    title: "No messages",
    motivation: "Send a message to start the conversation",
    action: "Send Message",
    target: "focus:message-input",
  },
  files: {
    title: "No files",
    motivation: "Upload files to use in your workflows and sessions",
    ability: "Drag and drop supported",
    action: "Upload Files",
    target: "modal:file-upload",
  },
  alerts: {
    title: "No alerts",
    motivation: "System alerts will appear here when triggered",
    action: "Configure Alerts",
    target: "/studio/admin/alerts/settings",
  },
  connections: {
    title: "No connections",
    motivation: "Connect MCP servers to extend capabilities",
    ability: "Quick connection setup",
    action: "Add Connection",
    target: "/studio/connections/new",
  },
};

/**
 * Persona-specific overrides
 */
const PERSONA_OVERRIDES: Partial<
  Record<EmptyStateContext, Partial<Record<Persona, Partial<EmptyStateConfig>>>>
> = {
  sessions: {
    admin: {
      motivation: "Monitor team conversations and system activity",
      action: "View Dashboard",
      target: "/studio/admin/dashboard",
    },
    "security-admin": {
      motivation: "Review security-related sessions and audit trails",
      action: "Security Dashboard",
      target: "/studio/admin/security",
    },
    auditor: {
      motivation: "Access audit logs for compliance review",
      action: "View Audit Logs",
      target: "/studio/admin/audit",
    },
    bob: {
      motivation: "Start chatting to explore AI capabilities",
      ability: "No setup required",
      action: "Start Chatting",
      target: "/studio/chat/new",
    },
  },
  workflows: {
    admin: {
      motivation: "Configure system-wide workflow templates",
      action: "Manage Templates",
      target: "/studio/admin/workflows/templates",
    },
    "alice-builder": {
      motivation: "Build custom workflows with AI-powered nodes",
      ability: "Drag-and-drop interface",
      action: "Create Workflow",
      target: "/studio/workflows/new",
    },
    "alice-analyst": {
      motivation: "Analyze workflow performance and optimization opportunities",
      action: "View Analytics",
      target: "/studio/observability",
    },
    "alice-devops": {
      motivation: "Deploy and monitor production workflows",
      action: "Deployment Console",
      target: "/studio/connections",
    },
    bob: {
      motivation: "Use shared workflows created by your team",
      action: "Browse Shared",
      target: "/studio/workflows?filter=shared",
    },
  },
  projects: {
    admin: {
      motivation: "Manage organization-wide projects and permissions",
      action: "Organization Projects",
      target: "/studio/admin/projects",
    },
    "alice-builder": {
      motivation: "Group related workflows and sessions together",
      action: "New Project",
      target: "/studio/projects/new",
    },
    bob: {
      motivation: "Join existing projects or create your own",
      ability: "Easy collaboration",
      action: "Create Project",
      target: "/studio/projects/new",
    },
  },
  traces: {
    "alice-analyst": {
      motivation: "Deep-dive into execution traces for performance insights",
      action: "Run Workflow",
      target: "/studio/workflows",
      secondaryAction: "View Demo Trace",
      secondaryTarget: "/studio/observability/demo",
    },
    "alice-devops": {
      motivation: "Monitor production traces and identify issues",
      action: "Connect Monitoring",
      target: "/studio/connections",
    },
  },
  alerts: {
    admin: {
      motivation: "Configure and monitor system-wide alerts",
      action: "Alert Settings",
      target: "/studio/admin/alerts/settings",
    },
    "security-admin": {
      motivation: "Set up security alert rules and notifications",
      action: "Security Alerts",
      target: "/studio/admin/security/alerts",
    },
    "compliance-officer": {
      motivation: "Configure compliance monitoring alerts",
      action: "Compliance Alerts",
      target: "/studio/compliance/alerts",
    },
  },
  connections: {
    admin: {
      motivation: "Manage organization-wide MCP server connections",
      action: "Manage Servers",
      target: "/studio/admin/connections",
    },
    "alice-devops": {
      motivation: "Connect production services and monitoring tools",
      action: "Add Server",
      target: "/studio/connections/new",
    },
  },
};

/**
 * Get empty state configuration for a given context and persona
 */
export function getEmptyStateConfig(
  context: EmptyStateContext,
  persona: Persona = "default",
): EmptyStateConfig {
  const defaultConfig = DEFAULT_CONFIGS[context];
  const personaOverrides = PERSONA_OVERRIDES[context]?.[persona];

  if (!personaOverrides) {
    return defaultConfig;
  }

  return {
    ...defaultConfig,
    ...personaOverrides,
  };
}

/**
 * Get all supported contexts
 */
export function getSupportedContexts(): EmptyStateContext[] {
  return Object.keys(DEFAULT_CONFIGS) as EmptyStateContext[];
}

/**
 * Get all personas
 */
export function getSupportedPersonas(): Persona[] {
  return [
    "admin",
    "security-admin",
    "auditor",
    "alice-builder",
    "alice-analyst",
    "alice-devops",
    "compliance-officer",
    "bob",
    "default",
  ];
}

/**
 * Check if a persona has custom configuration for a context
 */
export function hasPersonaConfig(
  context: EmptyStateContext,
  persona: Persona,
): boolean {
  return !!PERSONA_OVERRIDES[context]?.[persona];
}

export default {
  getEmptyStateConfig,
  getSupportedContexts,
  getSupportedPersonas,
  hasPersonaConfig,
};
