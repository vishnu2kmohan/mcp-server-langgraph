import { afterEach, describe, expect, it, vi } from "vitest";

import { parseLogMessage } from "./jsonLogParser";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("parseLogMessage", () => {
  it("parses JSON message", () => {
    const parsed = parseLogMessage(
      JSON.stringify({ message: "hello", level: "info", service: "api" }),
    );
    expect(parsed.isJson).toBe(true);
    expect(parsed.message).toBe("hello");
    expect(parsed.level).toBe("info");
    expect(parsed.service).toBe("api");
    expect(parsed.extra).toBeDefined();
  });

  it("returns fallback for plain text", () => {
    const parsed = parseLogMessage("plain");
    expect(parsed.isJson).toBe(false);
    expect(parsed.message).toBe("plain");
    expect(parsed.rawMessage).toBe("plain");
  });
});
