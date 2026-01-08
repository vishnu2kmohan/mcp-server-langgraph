export interface ParsedLogEntry {
  timestamp?: number;
  level?: string;
  message: string;
  service?: string;
  logger?: string;
  extra?: Record<string, unknown>;
  rawMessage: string;
  isJson: boolean;
}

/**
 * Best-effort JSON log parser that tolerates plain strings.
 */
export function parseLogMessage(message: string): ParsedLogEntry {
  const base: ParsedLogEntry = {
    message,
    rawMessage: message,
    isJson: false,
  };

  try {
    const parsed = JSON.parse(message);
    if (parsed && typeof parsed === "object") {
      const obj = parsed as Record<string, unknown>;
      return {
        ...base,
        isJson: true,
        message: (obj.message as string) ?? message,
        timestamp:
          typeof obj.timestamp === "number" ? obj.timestamp : undefined,
        level: (obj.level as string) ?? undefined,
        service: (obj.service as string) ?? undefined,
        logger: (obj.logger as string) ?? undefined,
        extra: obj,
      };
    }
  } catch {
    // swallow parse errors; fall back to raw string
  }

  return base;
}

export default parseLogMessage;
