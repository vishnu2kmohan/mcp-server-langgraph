/**
 * WebSocket helper utilities for parsing standardized message envelopes.
 *
 * IMPORTANT: These helpers are OPT-IN per hook. Do NOT apply to:
 * - MCP WebSocket hooks (use JSON-RPC protocol)
 * - Trace WebSocket hooks (use MCP protocol)
 *
 * Only use for hooks connecting to /api/v1/ws/* endpoints that use
 * the MessageEnvelope schema from websocket/types.py.
 *
 * @module utils/websocketHelpers
 */

/**
 * Standard message envelope format from WebSocket handlers.
 *
 * Backend reference: websocket/types.py MessageEnvelope
 */
export interface MessageEnvelope<T = unknown> {
  /** Message type identifier */
  type: string;
  /** Optional payload data */
  payload: T;
  /** Optional correlation ID */
  id?: string;
  /** Optional ISO 8601 timestamp */
  timestamp?: string;
}

/**
 * Parse MessageEnvelope format from standardized WebSocket handlers.
 *
 * Returns the payload if the data is a valid envelope, or null if not.
 * This allows callers to distinguish between envelope and non-envelope messages.
 *
 * @example
 * ```typescript
 * const envelope = parseMessageEnvelope<MyPayloadType>(message);
 * if (envelope !== null) {
 *   handleEnvelopePayload(envelope);
 * } else {
 *   handleLegacyFlatMessage(message);
 * }
 * ```
 *
 * @param data - Raw WebSocket message data
 * @returns The payload if data is an envelope with payload, null otherwise
 */
export function parseMessageEnvelope<T>(data: unknown): T | null {
  if (typeof data === "object" && data !== null && "payload" in data) {
    const envelope = data as { payload: T };
    return envelope.payload;
  }
  return null;
}

/**
 * Type guard to check if data is a valid MessageEnvelope.
 *
 * A valid envelope must have both 'type' (string) and 'payload' properties.
 *
 * @param data - Raw WebSocket message data
 * @returns True if data is a valid MessageEnvelope
 */
export function isMessageEnvelope(data: unknown): data is MessageEnvelope {
  return (
    typeof data === "object" &&
    data !== null &&
    "type" in data &&
    typeof (data as Record<string, unknown>).type === "string" &&
    "payload" in data
  );
}

/**
 * Extract payload from envelope or return data as-is for backward compatibility.
 *
 * This helper supports graceful migration from flat messages to envelope format.
 * Use this when you need to handle both formats during the migration period.
 *
 * @example
 * ```typescript
 * // Handles both envelope and legacy flat messages
 * const data = extractPayload<ConnectionStatus>(message);
 * updateConnectionStatus(data);
 * ```
 *
 * @param data - Raw WebSocket message data (envelope or flat)
 * @returns The payload if envelope, or the original data if not
 */
export function extractPayload<T>(data: unknown): T | null | undefined {
  if (data === null) return null;
  if (data === undefined) return undefined;

  if (isMessageEnvelope(data)) {
    return data.payload as T;
  }

  // Return original data for backward compatibility with flat messages
  return data as T;
}
