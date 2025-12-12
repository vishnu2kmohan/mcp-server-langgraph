/**
 * MCP StreamableHTTP Client Tests
 *
 * TDD tests for the MCP client that communicates with the
 * backend using the StreamableHTTP transport and NDJSON streaming.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MCPClient, MCPClientError, createMCPClient } from './mcp-client';
import type {
  MCPServerCapabilities,
  MCPTool,
  MCPResource,
  MCPPrompt,
  MCPStreamChunk,
} from './mcp-types';

// =============================================================================
// Test Setup
// =============================================================================

describe('MCPClient', () => {
  let client: MCPClient;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn();
    global.fetch = mockFetch;
    client = createMCPClient({ baseUrl: 'http://localhost:8001' });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Initialization Tests
  // ===========================================================================

  describe('initialize', () => {
    it('should_send_initialize_request_with_client_capabilities', async () => {
      // GIVEN: A mock successful initialize response
      const mockResponse = {
        jsonrpc: '2.0',
        id: 1,
        result: {
          protocolVersion: '2025-11-25',
          capabilities: {
            tools: { listChanged: true },
            resources: { subscribe: true },
            prompts: { listChanged: true },
          },
          serverInfo: { name: 'mcp-server-langgraph', version: '1.0.0' },
        },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      // WHEN: Client initializes
      const result = await client.initialize();

      // THEN: Request should include client capabilities
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8001/message',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: expect.stringContaining('"method":"initialize"'),
        })
      );

      // AND: Should return server info and capabilities
      expect(result.serverInfo.name).toBe('mcp-server-langgraph');
      expect(result.capabilities.tools).toBeDefined();
    });

    it('should_handle_initialization_error_gracefully', async () => {
      // GIVEN: Server returns an error
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      // WHEN/THEN: Initialize should throw MCPClientError
      await expect(client.initialize()).rejects.toThrow(MCPClientError);
    });

    it('should_store_server_capabilities_after_initialization', async () => {
      // GIVEN: Successful initialization
      const capabilities: MCPServerCapabilities = {
        tools: { listChanged: true },
        resources: { subscribe: true, listChanged: true },
        prompts: { listChanged: true },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              protocolVersion: '2025-11-25',
              capabilities,
              serverInfo: { name: 'test-server', version: '1.0.0' },
            },
          }),
      });

      // WHEN: Client initializes
      await client.initialize();

      // THEN: Capabilities should be stored
      expect(client.getServerCapabilities()).toEqual(capabilities);
    });
  });

  // ===========================================================================
  // Tools Tests
  // ===========================================================================

  describe('tools', () => {
    it('should_list_available_tools', async () => {
      // GIVEN: Server returns a list of tools
      const tools: MCPTool[] = [
        {
          name: 'agent_chat',
          description: 'Chat with the AI agent',
          inputSchema: {
            type: 'object',
            properties: {
              message: { type: 'string' },
              conversation_id: { type: 'string' },
            },
            required: ['message'],
          },
        },
        {
          name: 'execute_python',
          description: 'Execute Python code',
          inputSchema: {
            type: 'object',
            properties: { code: { type: 'string' } },
            required: ['code'],
          },
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: { tools },
          }),
      });

      // WHEN: Listing tools
      const result = await client.listTools();

      // THEN: Should return the tools
      expect(result).toHaveLength(2);
      expect(result[0].name).toBe('agent_chat');
      expect(result[1].name).toBe('execute_python');
    });

    it('should_call_tool_with_arguments', async () => {
      // GIVEN: Tool call succeeds
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              content: [{ type: 'text', text: 'Hello from agent!' }],
            },
          }),
      });

      // WHEN: Calling a tool
      const result = await client.callTool('agent_chat', {
        message: 'Hello',
        conversation_id: 'conv-123',
      });

      // THEN: Should return tool result
      expect(result.content).toHaveLength(1);
      expect(result.content[0]).toEqual({ type: 'text', text: 'Hello from agent!' });
    });

    it('should_handle_tool_call_error', async () => {
      // GIVEN: Tool call returns an error
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              content: [{ type: 'text', text: 'Tool execution failed' }],
              isError: true,
            },
          }),
      });

      // WHEN: Calling a tool that errors
      const result = await client.callTool('execute_python', { code: 'invalid code' });

      // THEN: Should return error result
      expect(result.isError).toBe(true);
    });
  });

  // ===========================================================================
  // Streaming Tests
  // ===========================================================================

  describe('streaming', () => {
    it('should_stream_tool_call_with_ndjson_chunks', async () => {
      // GIVEN: Server returns NDJSON stream
      const chunks = [
        { type: 'chunk', content: 'Hello' },
        { type: 'chunk', content: ' world' },
        { type: 'complete', messageId: 'msg-123', usage: { promptTokens: 10, completionTokens: 5, totalTokens: 15 } },
      ];

      const encoder = new TextEncoder();
      let chunkIndex = 0;

      const mockStream = new ReadableStream({
        pull(controller) {
          if (chunkIndex < chunks.length) {
            const line = JSON.stringify(chunks[chunkIndex]) + '\n';
            controller.enqueue(encoder.encode(line));
            chunkIndex++;
          } else {
            controller.close();
          }
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/x-ndjson' }),
        body: mockStream,
      });

      // WHEN: Streaming tool call
      const receivedChunks: MCPStreamChunk[] = [];
      await client.streamToolCall('agent_chat', { message: 'Hello' }, (chunk) => {
        receivedChunks.push(chunk);
      });

      // THEN: Should receive all chunks
      expect(receivedChunks).toHaveLength(3);
      expect(receivedChunks[0].content).toBe('Hello');
      expect(receivedChunks[1].content).toBe(' world');
      expect(receivedChunks[2].type).toBe('complete');
    });

    it('should_handle_stream_error_gracefully', async () => {
      // GIVEN: Stream returns an error chunk
      const chunks = [
        { type: 'chunk', content: 'Starting...' },
        { type: 'error', error: 'Connection lost' },
      ];

      const encoder = new TextEncoder();
      let chunkIndex = 0;

      const mockStream = new ReadableStream({
        pull(controller) {
          if (chunkIndex < chunks.length) {
            const line = JSON.stringify(chunks[chunkIndex]) + '\n';
            controller.enqueue(encoder.encode(line));
            chunkIndex++;
          } else {
            controller.close();
          }
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/x-ndjson' }),
        body: mockStream,
      });

      // WHEN: Streaming encounters error
      const receivedChunks: MCPStreamChunk[] = [];
      await client.streamToolCall('agent_chat', { message: 'Hello' }, (chunk) => {
        receivedChunks.push(chunk);
      });

      // THEN: Should receive error chunk
      const errorChunk = receivedChunks.find((c) => c.type === 'error');
      expect(errorChunk).toBeDefined();
      expect(errorChunk?.error).toBe('Connection lost');
    });

    it('should_support_abort_signal_for_cancellation', async () => {
      // GIVEN: A long-running stream
      const controller = new AbortController();

      mockFetch.mockImplementation(() => {
        return new Promise((_, reject) => {
          controller.signal.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'));
          });
        });
      });

      // WHEN: Stream is aborted
      const streamPromise = client.streamToolCall(
        'agent_chat',
        { message: 'Hello' },
        () => {},
        { signal: controller.signal }
      );

      controller.abort();

      // THEN: Should throw abort error
      await expect(streamPromise).rejects.toThrow('Aborted');
    });
  });

  // ===========================================================================
  // Resources Tests
  // ===========================================================================

  describe('resources', () => {
    it('should_list_available_resources', async () => {
      // GIVEN: Server returns resources
      const resources: MCPResource[] = [
        {
          uri: 'playground://session/123/traces',
          name: 'Session Traces',
          description: 'OpenTelemetry traces',
          mimeType: 'application/json',
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: { resources },
          }),
      });

      // WHEN: Listing resources
      const result = await client.listResources();

      // THEN: Should return resources
      expect(result.resources).toHaveLength(1);
      expect(result.resources[0].uri).toBe('playground://session/123/traces');
    });

    it('should_read_resource_content', async () => {
      // GIVEN: Server returns resource content
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              contents: [
                {
                  uri: 'playground://session/123/traces',
                  mimeType: 'application/json',
                  text: '{"traces": []}',
                },
              ],
            },
          }),
      });

      // WHEN: Reading a resource
      const result = await client.readResource('playground://session/123/traces');

      // THEN: Should return content
      expect(result.contents).toHaveLength(1);
      expect(result.contents[0].text).toBe('{"traces": []}');
    });
  });

  // ===========================================================================
  // Prompts Tests
  // ===========================================================================

  describe('prompts', () => {
    it('should_list_available_prompts', async () => {
      // GIVEN: Server returns prompts
      const prompts: MCPPrompt[] = [
        {
          name: 'code_review',
          description: 'Review code for issues',
          arguments: [{ name: 'code', required: true }],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: { prompts },
          }),
      });

      // WHEN: Listing prompts
      const result = await client.listPrompts();

      // THEN: Should return prompts
      expect(result).toHaveLength(1);
      expect(result[0].name).toBe('code_review');
    });

    it('should_get_prompt_messages', async () => {
      // GIVEN: Server returns prompt messages
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              description: 'Code review prompt',
              messages: [
                { role: 'user', content: { type: 'text', text: 'Review this code: ...' } },
              ],
            },
          }),
      });

      // WHEN: Getting a prompt
      const result = await client.getPrompt('code_review', { code: 'function test() {}' });

      // THEN: Should return messages
      expect(result.messages).toHaveLength(1);
      expect(result.messages[0].role).toBe('user');
    });
  });

  // ===========================================================================
  // Connection Management Tests
  // ===========================================================================

  describe('connection management', () => {
    it('should_track_connection_status', async () => {
      // GIVEN: Client is created
      expect(client.getStatus()).toBe('disconnected');

      // WHEN: Initializing
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              protocolVersion: '2025-11-25',
              capabilities: {},
              serverInfo: { name: 'test', version: '1.0.0' },
            },
          }),
      });

      await client.initialize();

      // THEN: Status should be connected
      expect(client.getStatus()).toBe('connected');
    });

    it('should_handle_disconnect', async () => {
      // GIVEN: Client is connected
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            result: {
              protocolVersion: '2025-11-25',
              capabilities: {},
              serverInfo: { name: 'test', version: '1.0.0' },
            },
          }),
      });

      await client.initialize();
      expect(client.getStatus()).toBe('connected');

      // WHEN: Disconnecting
      client.disconnect();

      // THEN: Status should be disconnected
      expect(client.getStatus()).toBe('disconnected');
    });

    it('should_increment_request_ids', async () => {
      // GIVEN: Client is ready
      const capturedBodies: string[] = [];

      mockFetch.mockImplementation(async (_url, options) => {
        capturedBodies.push(options.body);
        return {
          ok: true,
          json: () => Promise.resolve({ jsonrpc: '2.0', id: 1, result: { tools: [] } }),
        };
      });

      // WHEN: Making multiple requests
      await client.listTools();
      await client.listTools();

      // THEN: Request IDs should increment
      const body1 = JSON.parse(capturedBodies[0]);
      const body2 = JSON.parse(capturedBodies[1]);
      expect(body2.id).toBeGreaterThan(body1.id);
    });
  });

  // ===========================================================================
  // Error Handling Tests
  // ===========================================================================

  describe('error handling', () => {
    it('should_throw_MCPClientError_for_json_rpc_errors', async () => {
      // GIVEN: Server returns JSON-RPC error
      const errorResponse = {
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            error: {
              code: -32601,
              message: 'Method not found',
            },
          }),
      };
      mockFetch.mockResolvedValue(errorResponse);

      // WHEN/THEN: Should throw MCPClientError with correct message
      await expect(client.listTools()).rejects.toThrow(MCPClientError);

      // Verify error message
      try {
        await client.listTools();
        expect.fail('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(MCPClientError);
        expect((error as MCPClientError).message).toBe('Method not found');
      }
    });

    it('should_throw_MCPClientError_for_network_errors', async () => {
      // GIVEN: Network error occurs
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      // WHEN/THEN: Should throw MCPClientError
      await expect(client.listTools()).rejects.toThrow(MCPClientError);
    });

    it('should_include_error_code_in_MCPClientError', async () => {
      // GIVEN: Server returns error with code
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            jsonrpc: '2.0',
            id: 1,
            error: {
              code: -32602,
              message: 'Invalid params',
              data: { field: 'message' },
            },
          }),
      });

      // WHEN: Making a request
      try {
        await client.listTools();
        expect.fail('Should have thrown');
      } catch (error) {
        // THEN: Error should have code and data
        expect(error).toBeInstanceOf(MCPClientError);
        expect((error as MCPClientError).code).toBe(-32602);
        expect((error as MCPClientError).data).toEqual({ field: 'message' });
      }
    });
  });

  // ===========================================================================
  // Authentication Tests
  // ===========================================================================

  describe('authentication', () => {
    it('should_include_auth_token_in_requests_when_set', async () => {
      // GIVEN: Client with auth token
      client = createMCPClient({
        baseUrl: 'http://localhost:8001',
        authToken: 'test-token-123',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jsonrpc: '2.0', id: 1, result: { tools: [] } }),
      });

      // WHEN: Making a request
      await client.listTools();

      // THEN: Authorization header should be included
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token-123',
          }),
        })
      );
    });

    it('should_support_updating_auth_token', async () => {
      // GIVEN: Client without token
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ jsonrpc: '2.0', id: 1, result: { tools: [] } }),
      });

      await client.listTools();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.not.objectContaining({
          headers: expect.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );

      // WHEN: Setting auth token
      client.setAuthToken('new-token');
      await client.listTools();

      // THEN: New token should be used
      expect(mockFetch).toHaveBeenLastCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer new-token',
          }),
        })
      );
    });
  });

  // ===========================================================================
  // Ping Tests
  // ===========================================================================

  describe('ping', () => {
    it('should_send_ping_and_receive_pong', async () => {
      // GIVEN: Server responds to ping
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ jsonrpc: '2.0', id: 1, result: {} }),
      });

      // WHEN: Pinging
      const result = await client.ping();

      // THEN: Should succeed
      expect(result).toBe(true);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"method":"ping"'),
        })
      );
    });
  });
});

// =============================================================================
// Factory Function Tests
// =============================================================================

describe('createMCPClient', () => {
  it('should_create_client_with_default_options', () => {
    // WHEN: Creating client with minimal options
    const client = createMCPClient({ baseUrl: 'http://localhost:8001' });

    // THEN: Client should be created
    expect(client).toBeDefined();
    expect(client.getStatus()).toBe('disconnected');
  });

  it('should_create_client_with_custom_timeout', () => {
    // WHEN: Creating client with custom timeout
    const client = createMCPClient({
      baseUrl: 'http://localhost:8001',
      timeout: 5000,
    });

    // THEN: Client should be created
    expect(client).toBeDefined();
  });
});
