/**
 * Markdown Reference Types
 *
 * Supports [[type:qualifier:id]] syntax for inline references.
 * Part of the Unified Markdown Reference System.
 */

/**
 * Supported reference types.
 * - tool: MCP tool (server:tool_name)
 * - skill: Skill by name
 * - artifact: Artifact by ID
 * - memory: Memory note by ID (Phase 4)
 * - plan: Execution plan by ID (Phase 4)
 */
export type ReferenceType = 'tool' | 'skill' | 'artifact' | 'memory' | 'plan';

/**
 * Reference status after resolution.
 */
export type ReferenceStatus = 'valid' | 'not_found' | 'unauthorized' | 'loading';

/**
 * Parsed reference from markdown text.
 * Extracted by the remarkReferences plugin.
 */
export interface ParsedReference {
  /** Reference type */
  type: ReferenceType;
  /** Qualifier - server name for tools, name for skills/artifacts */
  qualifier: string;
  /** Identifier - tool name, skill name, or artifact ID */
  id: string;
  /** Optional custom label from syntax [[type:id|Label]] */
  label?: string;
  /** Original raw text from markdown */
  raw: string;
}

/**
 * Resolved reference with display information.
 * Returned from the /references/resolve API.
 */
export interface ResolvedReference extends Omit<ParsedReference, 'raw'> {
  /** Human-readable display name */
  displayName: string;
  /** Description for tooltip/popover */
  description?: string;
  /** Resolution status */
  status: ReferenceStatus;
  /** Additional metadata for deep linking and display */
  metadata?: {
    /** Connection UUID for tool deep links (navigate to ConnectionsPage) */
    connectionId?: string;
    /** Tool input schema */
    inputSchema?: Record<string, unknown>;
    /** Skill tags */
    tags?: string[];
    /** Skill version */
    version?: string;
    /** Artifact content type */
    contentType?: string;
    /** Additional custom metadata */
    [key: string]: unknown;
  };
}

/**
 * Request body for batch reference resolution.
 * Only includes fields needed by the backend (no label or raw).
 */
export interface ReferenceResolveRequest {
  type: ReferenceType;
  qualifier: string;
  id: string;
}

/**
 * Response from batch reference resolution API.
 */
export interface ResolveReferencesResponse {
  resolved: ResolvedReference[];
}

/**
 * Request body for the /references/resolve endpoint.
 */
export interface ResolveReferencesRequest {
  references: ReferenceResolveRequest[];
}

/**
 * Props for ReferenceChip component.
 */
export interface ReferenceChipProps {
  /** Reference type */
  type: ReferenceType;
  /** Server name for tools, name for skills/artifacts */
  qualifier: string;
  /** Tool name, skill name, or artifact ID */
  id: string;
  /** Optional custom display label */
  label?: string;
  /** Connection ID for tool deep links (optional, from resolved metadata) */
  connectionId?: string;
}

/**
 * Context value for reference resolution.
 */
export interface ReferenceResolverContextValue {
  /** Map of reference key to resolved reference */
  resolvedRefs: Map<string, ResolvedReference>;
  /** Whether resolution is in progress */
  isLoading: boolean;
  /** Error from resolution (if any) */
  error?: string;
  /** Resolve a batch of references */
  resolve: (refs: ParsedReference[]) => Promise<void>;
}

/**
 * Create a unique key for a reference.
 * Used for caching and deduplication.
 */
export function getReferenceKey(ref: Pick<ParsedReference, 'type' | 'qualifier' | 'id'>): string {
  return `${ref.type}:${ref.qualifier}:${ref.id}`;
}

/**
 * Parse a reference URL from remarkReferences plugin.
 * URL format: ref://type/qualifier:id
 *
 * @param url - URL to parse (e.g., "ref://tool/filesystem:read_file")
 * @returns Parsed reference data or null if invalid
 */
export function parseReferenceUrl(
  url: string
): { type: ReferenceType; qualifier: string; id: string } | null {
  if (!url.startsWith('ref://')) {
    return null;
  }

  const path = url.slice(6); // Remove "ref://"
  const slashIndex = path.indexOf('/');
  if (slashIndex === -1) {
    return null;
  }

  const type = path.slice(0, slashIndex) as ReferenceType;
  const rest = path.slice(slashIndex + 1);

  // Validate type
  if (!['tool', 'skill', 'artifact', 'memory', 'plan'].includes(type)) {
    return null;
  }

  // For tools: qualifier:id (e.g., filesystem:read_file)
  // For skills/artifacts: just id (qualifier === id)
  if (type === 'tool') {
    const colonIndex = rest.indexOf(':');
    if (colonIndex === -1) {
      return null;
    }
    return {
      type,
      qualifier: rest.slice(0, colonIndex),
      id: rest.slice(colonIndex + 1),
    };
  }

  // For skill and artifact, qualifier equals id
  return {
    type,
    qualifier: rest,
    id: rest,
  };
}
