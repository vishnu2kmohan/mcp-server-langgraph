/**
 * WebSocket Protocol Types Tests
 *
 * TDD tests to verify that WebSocket protocol types are correctly defined
 * and type-safe. These tests validate the TypeScript types at compile-time
 * and runtime type guards.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import type {
  MessageEnvelope,
  // DevTools Protocol
  ConsoleLogEntry,
  NetworkRequestEntry,
  NetworkUpdateEntry,
  DevToolsMessage,
  // Traces Protocol
  TraceSpanEntry,
  TraceEventEntry as _TraceEventEntry,
  TraceSubscribeMessage,
  TracesMessage as _TracesMessage,
  // Budget Alerts Protocol
  BudgetAlertEntry,
  BudgetSubscribedResponse,
  BudgetSubscribeEntitiesMessage as _BudgetSubscribeEntitiesMessage,
  BudgetSubscribeAllMessage as _BudgetSubscribeAllMessage,
  BudgetAlertsMessage as _BudgetAlertsMessage,
  // AI Suggestions Protocol
  SuggestionResponseEntry,
  SuggestionRequestMessage,
  SuggestionAcceptMessage as _SuggestionAcceptMessage,
  SuggestionRejectMessage as _SuggestionRejectMessage,
  ContextUpdateMessage,
  AISuggestionsMessage as _AISuggestionsMessage,
  // MCP Aggregated Protocol
  MCPServerStatusEntry,
  MCPToolCallEntry,
  MCPAggregatedMessage as _MCPAggregatedMessage,
  // Error Protocol
  WebSocketError,
} from "./websocket-protocols";

// Import type guards as runtime functions (not type-only)
import {
  isConsoleLogEntry,
  isNetworkRequestEntry,
  isTraceSpanEntry,
  isTraceEventEntry,
  isBudgetAlertEntry,
  isWebSocketError,
} from "./websocket-protocols";

describe("WebSocket Protocol Types", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // Message Envelope
  // ===========================================================================

  describe("MessageEnvelope", () => {
    it("should have required type field", () => {
      const envelope: MessageEnvelope<"test", { value: number }> = {
        type: "test",
        payload: { value: 42 },
      };

      expect(envelope.type).toBe("test");
      expect(envelope.payload?.value).toBe(42);
    });

    it("should allow optional id field", () => {
      const envelope: MessageEnvelope<"test"> = {
        type: "test",
        id: "msg-123",
      };

      expect(envelope.id).toBe("msg-123");
    });
  });

  // ===========================================================================
  // DevTools Protocol
  // ===========================================================================

  describe("DevTools Protocol", () => {
    describe("ConsoleLogEntry", () => {
      it("should have correct structure", () => {
        const entry: ConsoleLogEntry = {
          type: "console",
          payload: {
            id: "log-1",
            level: "info",
            source: "system",
            message: "Test message",
            timestamp: Date.now(),
          },
        };

        expect(entry.type).toBe("console");
        expect(entry.payload.level).toBe("info");
      });

      it("should accept all log levels", () => {
        const levels = ["info", "warning", "error", "debug"] as const;
        levels.forEach((level) => {
          const entry: ConsoleLogEntry = {
            type: "console",
            payload: {
              level,
              source: "system",
              message: "Test",
              timestamp: Date.now(),
            },
          };
          expect(entry.payload.level).toBe(level);
        });
      });

      it("should accept all sources", () => {
        const sources = [
          "system",
          "api",
          "mcp",
          "notification",
          "execution",
          "websocket",
        ] as const;
        sources.forEach((source) => {
          const entry: ConsoleLogEntry = {
            type: "console",
            payload: {
              level: "info",
              source,
              message: "Test",
              timestamp: Date.now(),
            },
          };
          expect(entry.payload.source).toBe(source);
        });
      });

      it("should allow optional data and stackTrace", () => {
        const entry: ConsoleLogEntry = {
          type: "console",
          payload: {
            level: "error",
            source: "system",
            message: "Error occurred",
            timestamp: Date.now(),
            data: { code: 500 },
            stackTrace: "Error: at line 10",
          },
        };

        expect(entry.payload.data).toEqual({ code: 500 });
        expect(entry.payload.stackTrace).toBe("Error: at line 10");
      });
    });

    describe("NetworkRequestEntry", () => {
      it("should have correct structure", () => {
        const entry: NetworkRequestEntry = {
          type: "network",
          payload: {
            id: "req-1",
            method: "GET",
            url: "/api/test",
            status: "pending",
            startTime: Date.now(),
          },
        };

        expect(entry.type).toBe("network");
        expect(entry.payload.method).toBe("GET");
      });

      it("should accept all HTTP methods", () => {
        const methods = [
          "GET",
          "POST",
          "PUT",
          "DELETE",
          "PATCH",
          "OPTIONS",
        ] as const;
        methods.forEach((method) => {
          const entry: NetworkRequestEntry = {
            type: "network",
            payload: {
              method,
              url: "/api/test",
              status: "pending",
              startTime: Date.now(),
            },
          };
          expect(entry.payload.method).toBe(method);
        });
      });

      it("should accept all request statuses", () => {
        const statuses = [
          "pending",
          "completed",
          "error",
          "cancelled",
        ] as const;
        statuses.forEach((status) => {
          const entry: NetworkRequestEntry = {
            type: "network",
            payload: {
              method: "GET",
              url: "/api/test",
              status,
              startTime: Date.now(),
            },
          };
          expect(entry.payload.status).toBe(status);
        });
      });
    });

    describe("NetworkUpdateEntry", () => {
      it("should have correct structure", () => {
        const entry: NetworkUpdateEntry = {
          type: "network_update",
          payload: {
            id: "req-1",
            status: "completed",
            statusCode: 200,
            duration: 150,
            responseSize: 2048,
            endTime: Date.now(),
          },
        };

        expect(entry.type).toBe("network_update");
        expect(entry.payload.id).toBe("req-1");
      });
    });
  });

  // ===========================================================================
  // Traces Protocol
  // ===========================================================================

  describe("Traces Protocol", () => {
    describe("TraceSpanEntry", () => {
      it("should have correct structure", () => {
        const entry: TraceSpanEntry = {
          type: "trace_span",
          payload: {
            span_id: "span-123",
            trace_id: "trace-456",
            parent_span_id: null,
            name: "http.request",
            start_time: Date.now(),
            end_time: Date.now() + 100,
            duration_ms: 100,
            status: "ok",
            service_name: "api-gateway",
            attributes: {},
          },
        };

        expect(entry.type).toBe("trace_span");
        expect(entry.payload.span_id).toBe("span-123");
      });

      it("should accept all span statuses", () => {
        const statuses = ["ok", "error", "unset"] as const;
        statuses.forEach((status) => {
          const entry: TraceSpanEntry = {
            type: "trace_span",
            payload: {
              span_id: "span-123",
              trace_id: "trace-456",
              parent_span_id: null,
              name: "test",
              start_time: Date.now(),
              end_time: Date.now(),
              duration_ms: 0,
              status,
              service_name: "test",
              attributes: {},
            },
          };
          expect(entry.payload.status).toBe(status);
        });
      });
    });

    describe("TraceEventEntry", () => {
      it("should have correct structure", () => {
        const entry: TraceEventEntry = {
          type: "trace_event",
          payload: {
            span_id: "span-123",
            name: "http.request.start",
            timestamp: "2025-01-01T00:00:00Z",
            attributes: { method: "GET", path: "/api/test" },
          },
        };

        expect(entry.type).toBe("trace_event");
        expect(entry.payload.span_id).toBe("span-123");
        expect(entry.payload.name).toBe("http.request.start");
        expect(entry.payload.timestamp).toBe("2025-01-01T00:00:00Z");
        expect(entry.payload.attributes.method).toBe("GET");
      });
    });

    describe("TraceSubscribeMessage", () => {
      it("should have correct structure", () => {
        const msg: TraceSubscribeMessage = {
          type: "subscribe",
          id: "sub-123",
          payload: {
            service_filter: "api-*",
            trace_id: "trace-456",
          },
        };

        expect(msg.type).toBe("subscribe");
        expect(msg.payload?.service_filter).toBe("api-*");
      });
    });
  });

  // ===========================================================================
  // Budget Alerts Protocol
  // ===========================================================================

  describe("Budget Alerts Protocol", () => {
    describe("BudgetAlertEntry", () => {
      it("should have correct structure", () => {
        const entry: BudgetAlertEntry = {
          type: "budget_alert",
          payload: {
            entity_type: "organization",
            entity_id: "org-123",
            status: "warning",
            percent_used: 85.5,
            current_spend: "850.00",
            remaining: "150.00",
            monthly_limit_usd: "1000.00",
            message: "Budget at 85%",
          },
        };

        expect(entry.type).toBe("budget_alert");
        expect(entry.payload.status).toBe("warning");
      });

      it("should accept all entity types", () => {
        const types = ["organization", "project", "team", "user"] as const;
        types.forEach((entity_type) => {
          const entry: BudgetAlertEntry = {
            type: "budget_alert",
            payload: {
              entity_type,
              entity_id: "test-123",
              status: "ok",
              percent_used: 50,
              current_spend: "500.00",
              remaining: "500.00",
              monthly_limit_usd: "1000.00",
              message: "OK",
            },
          };
          expect(entry.payload.entity_type).toBe(entity_type);
        });
      });

      it("should accept all alert statuses", () => {
        const statuses = ["ok", "warning", "critical", "exceeded"] as const;
        statuses.forEach((status) => {
          const entry: BudgetAlertEntry = {
            type: "budget_alert",
            payload: {
              entity_type: "organization",
              entity_id: "org-123",
              status,
              percent_used: 85.5,
              current_spend: "850.00",
              remaining: "150.00",
              monthly_limit_usd: "1000.00",
              message: "Budget",
            },
          };
          expect(entry.payload.status).toBe(status);
        });
      });
    });

    describe("BudgetSubscribedResponse", () => {
      it("should have correct structure", () => {
        const response: BudgetSubscribedResponse = {
          type: "subscribed",
          payload: {
            entity_ids: ["org-123", "org-456"],
            subscribe_all: false,
          },
        };

        expect(response.type).toBe("subscribed");
        expect(response.payload.entity_ids).toHaveLength(2);
      });
    });
  });

  // ===========================================================================
  // AI Suggestions Protocol
  // ===========================================================================

  describe("AI Suggestions Protocol", () => {
    describe("SuggestionResponseEntry", () => {
      it("should have correct structure", () => {
        const entry: SuggestionResponseEntry = {
          type: "suggestion_response",
          payload: {
            suggestion_id: "sug-123",
            text: "I can help you with that!",
            confidence: 0.85,
            reasoning: "Based on greeting pattern",
          },
        };

        expect(entry.type).toBe("suggestion_response");
        expect(entry.payload.confidence).toBe(0.85);
      });
    });

    describe("SuggestionRequestMessage", () => {
      it("should have correct structure", () => {
        const msg: SuggestionRequestMessage = {
          type: "suggestion_request",
          id: "req-123",
          payload: {
            session_id: "session-123",
            input_text: "Hello, I need help with",
            cursor_position: 25,
            context_window: 500,
          },
        };

        expect(msg.type).toBe("suggestion_request");
        expect(msg.payload.cursor_position).toBe(25);
      });
    });

    describe("ContextUpdateMessage", () => {
      it("should have correct structure", () => {
        const msg: ContextUpdateMessage = {
          type: "context_update",
          id: "ctx-123",
          payload: {
            session_id: "session-123",
            context: "User is working on a Python project",
          },
        };

        expect(msg.type).toBe("context_update");
        expect(msg.payload.context).toContain("Python");
      });
    });
  });

  // ===========================================================================
  // MCP Aggregated Protocol
  // ===========================================================================

  describe("MCP Aggregated Protocol", () => {
    describe("MCPServerStatusEntry", () => {
      it("should have correct structure", () => {
        const entry: MCPServerStatusEntry = {
          type: "server_status",
          payload: {
            server_id: "mcp-server-1",
            status: "connected",
            name: "GitHub MCP",
            timestamp: Date.now(),
          },
        };

        expect(entry.type).toBe("server_status");
        expect(entry.payload.status).toBe("connected");
      });

      it("should accept all server statuses", () => {
        const statuses = ["connected", "disconnected", "error"] as const;
        statuses.forEach((status) => {
          const entry: MCPServerStatusEntry = {
            type: "server_status",
            payload: {
              server_id: "mcp-server-1",
              status,
              name: "Test MCP",
              timestamp: Date.now(),
            },
          };
          expect(entry.payload.status).toBe(status);
        });
      });
    });

    describe("MCPToolCallEntry", () => {
      it("should have correct structure", () => {
        const entry: MCPToolCallEntry = {
          type: "tool_call",
          payload: {
            server_id: "mcp-server-1",
            tool_name: "search_code",
            call_id: "call-123",
            status: "completed",
            input: { query: "test" },
            output: { results: [] },
            duration_ms: 150,
            timestamp: Date.now(),
          },
        };

        expect(entry.type).toBe("tool_call");
        expect(entry.payload.tool_name).toBe("search_code");
      });

      it("should accept all tool call statuses", () => {
        const statuses = ["started", "completed", "error"] as const;
        statuses.forEach((status) => {
          const entry: MCPToolCallEntry = {
            type: "tool_call",
            payload: {
              server_id: "mcp-server-1",
              tool_name: "test",
              call_id: "call-123",
              status,
              input: {},
              output: {},
              duration_ms: 0,
              timestamp: Date.now(),
            },
          };
          expect(entry.payload.status).toBe(status);
        });
      });
    });
  });

  // ===========================================================================
  // Error Protocol
  // ===========================================================================

  describe("Error Protocol", () => {
    describe("WebSocketError", () => {
      it("should have correct structure", () => {
        const error: WebSocketError = {
          type: "error",
          payload: {
            code: "token_expired",
            message: "Authentication token has expired",
            retryable: false,
          },
        };

        expect(error.type).toBe("error");
        expect(error.payload.retryable).toBe(false);
      });

      it("should accept all error codes", () => {
        const codes = [
          "token_expired",
          "unauthorized",
          "rate_limited",
          "internal_error",
          "invalid_request",
          "not_found",
        ] as const;
        codes.forEach((code) => {
          const error: WebSocketError = {
            type: "error",
            payload: {
              code,
              message: "Test error",
              retryable: code === "rate_limited",
            },
          };
          expect(error.payload.code).toBe(code);
        });
      });

      it("should allow optional details", () => {
        const error: WebSocketError = {
          type: "error",
          payload: {
            code: "internal_error",
            message: "Server error",
            retryable: true,
            details: { trace_id: "trace-123" },
          },
        };

        expect(error.payload.details?.trace_id).toBe("trace-123");
      });
    });
  });

  // ===========================================================================
  // Type Guards
  // ===========================================================================

  describe("Type Guards", () => {
    describe("isConsoleLogEntry", () => {
      it("should return true for valid console log entry", () => {
        const entry = {
          type: "console",
          payload: {
            level: "info",
            source: "system",
            message: "Test",
            timestamp: Date.now(),
          },
        };

        expect(isConsoleLogEntry(entry)).toBe(true);
      });

      it("should return false for invalid entry", () => {
        expect(isConsoleLogEntry({ type: "network" })).toBe(false);
        expect(isConsoleLogEntry(null)).toBe(false);
        expect(isConsoleLogEntry(undefined)).toBe(false);
      });
    });

    describe("isNetworkRequestEntry", () => {
      it("should return true for valid network request entry", () => {
        const entry = {
          type: "network",
          payload: {
            method: "GET",
            url: "/api/test",
            status: "pending",
            startTime: Date.now(),
          },
        };

        expect(isNetworkRequestEntry(entry)).toBe(true);
      });

      it("should return false for invalid entry", () => {
        expect(isNetworkRequestEntry({ type: "console" })).toBe(false);
      });
    });

    describe("isTraceSpanEntry", () => {
      it("should return true for valid trace span entry", () => {
        const entry = {
          type: "trace_span",
          payload: {
            span_id: "span-123",
            trace_id: "trace-456",
            name: "test",
          },
        };

        expect(isTraceSpanEntry(entry)).toBe(true);
      });

      it("should return false for invalid entry", () => {
        expect(isTraceSpanEntry({ type: "console" })).toBe(false);
      });
    });

    describe("isTraceEventEntry", () => {
      it("should return true for valid trace event entry", () => {
        const entry = {
          type: "trace_event",
          payload: {
            span_id: "span-123",
            name: "http.request.start",
            timestamp: "2025-01-01T00:00:00Z",
            attributes: {},
          },
        };

        expect(isTraceEventEntry(entry)).toBe(true);
      });

      it("should return false for invalid entry", () => {
        expect(isTraceEventEntry({ type: "console" })).toBe(false);
        expect(isTraceEventEntry({ type: "trace_span" })).toBe(false);
      });
    });

    describe("isBudgetAlertEntry", () => {
      it("should return true for valid budget alert entry", () => {
        const entry = {
          type: "budget_alert",
          payload: {
            entity_type: "organization",
            entity_id: "org-123",
            status: "warning",
          },
        };

        expect(isBudgetAlertEntry(entry)).toBe(true);
      });

      it("should return false for invalid entry", () => {
        expect(isBudgetAlertEntry({ type: "console" })).toBe(false);
      });
    });

    describe("isWebSocketError", () => {
      it("should return true for valid error", () => {
        const error = {
          type: "error",
          payload: {
            code: "internal_error",
            message: "Test error",
            retryable: true,
          },
        };

        expect(isWebSocketError(error)).toBe(true);
      });

      it("should return false for invalid error", () => {
        expect(isWebSocketError({ type: "console" })).toBe(false);
      });
    });
  });

  // ===========================================================================
  // Discriminated Unions (Compile-time checks)
  // ===========================================================================

  describe("Discriminated Unions (Type Narrowing)", () => {
    it("DevToolsMessage should narrow correctly", () => {
      const handleMessage = (msg: DevToolsMessage) => {
        switch (msg.type) {
          case "console":
            // TypeScript should know this is ConsoleLogEntry
            return msg.payload.level;
          case "network":
            // TypeScript should know this is NetworkRequestEntry
            return msg.payload.method;
          case "network_update":
            // TypeScript should know this is NetworkUpdateEntry
            return msg.payload.id;
          default:
            return "unknown";
        }
      };

      const consoleMsg: DevToolsMessage = {
        type: "console",
        payload: {
          level: "info",
          source: "system",
          message: "Test",
          timestamp: Date.now(),
        },
      };

      expect(handleMessage(consoleMsg)).toBe("info");
    });

    it("BudgetAlertsMessage should narrow correctly", () => {
      const handleMessage = (msg: BudgetAlertsMessage) => {
        switch (msg.type) {
          case "budget_alert":
            return msg.payload.status;
          case "subscribed":
            return msg.payload.entity_ids.length;
          case "unsubscribed":
            return "unsubscribed";
          case "error":
            return msg.payload.code;
          default:
            return "unknown";
        }
      };

      const alertMsg: BudgetAlertsMessage = {
        type: "budget_alert",
        payload: {
          entity_type: "organization",
          entity_id: "org-123",
          status: "warning",
          percent_used: 85,
          current_spend: "850.00",
          remaining: "150.00",
          monthly_limit_usd: "1000.00",
          message: "Warning",
        },
      };

      expect(handleMessage(alertMsg)).toBe("warning");
    });
  });
});
