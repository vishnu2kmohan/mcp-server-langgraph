/**
 * MCP StreamableHTTP Client
 *
 * Client for communicating with the MCP backend using the
 * StreamableHTTP transport and NDJSON streaming.
 *
 * Implements the MCP 2025-11-25 specification.
 */

import type {
  JSONRPCRequest,
  JSONRPCResponse,
  MCPServerCapabilities,
  MCPServerInfo,
  MCPClientCapabilities,
  MCPClientInfo,
  InitializeResult,
  MCPTool,
  MCPToolResult,
  ResourceReadResult,
  ResourceListResult,
  MCPPrompt,
  PromptGetResult,
  MCPStreamChunk,
  MCPConnectionStatus,
  MCPRequestOptions,
} from './mcp-types';

// =============================================================================
// Error Classes
// =============================================================================

export class MCPClientError extends Error {
  constructor(
    message: string,
    public code?: number,
    public data?: unknown
  ) {
    super(message);
    this.name = 'MCPClientError';
  }
}

// =============================================================================
// Client Interface
// =============================================================================

export interface MCPClient {
  // Connection management
  initialize(): Promise<InitializeResult>;
  disconnect(): void;
  getStatus(): MCPConnectionStatus;
  getServerCapabilities(): MCPServerCapabilities | null;
  getServerInfo(): MCPServerInfo | null;
  ping(): Promise<boolean>;

  // Authentication
  setAuthToken(token: string | null): void;

  // Tools
  listTools(): Promise<MCPTool[]>;
  callTool(name: string, args?: Record<string, unknown>): Promise<MCPToolResult>;
  streamToolCall(
    name: string,
    args: Record<string, unknown>,
    onChunk: (chunk: MCPStreamChunk) => void,
    options?: MCPRequestOptions
  ): Promise<void>;

  // Resources
  listResources(): Promise<ResourceListResult>;
  readResource(uri: string): Promise<ResourceReadResult>;

  // Prompts
  listPrompts(): Promise<MCPPrompt[]>;
  getPrompt(name: string, args?: Record<string, string>): Promise<PromptGetResult>;
}

// =============================================================================
// Client Options
// =============================================================================

export interface MCPClientOptions {
  baseUrl: string;
  authToken?: string;
  timeout?: number;
  clientInfo?: MCPClientInfo;
  capabilities?: MCPClientCapabilities;
}

// =============================================================================
// Client Implementation
// =============================================================================

class MCPClientImpl implements MCPClient {
  private baseUrl: string;
  private authToken: string | null;
  private timeout: number;
  private clientInfo: MCPClientInfo;
  private clientCapabilities: MCPClientCapabilities;
  private status: MCPConnectionStatus = 'disconnected';
  private serverInfo: MCPServerInfo | null = null;
  private serverCapabilities: MCPServerCapabilities | null = null;
  private requestId = 0;

  constructor(options: MCPClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.authToken = options.authToken || null;
    this.timeout = options.timeout || 30000;
    this.clientInfo = options.clientInfo || {
      name: 'playground-frontend',
      version: '1.0.0',
    };
    this.clientCapabilities = options.capabilities || {
      elicitation: {},
      sampling: {},
      roots: { listChanged: true },
    };
  }

  // ===========================================================================
  // Connection Management
  // ===========================================================================

  async initialize(): Promise<InitializeResult> {
    this.status = 'connecting';

    try {
      const result = await this.sendRequest<InitializeResult>('initialize', {
        protocolVersion: '2025-11-25',
        capabilities: this.clientCapabilities,
        clientInfo: this.clientInfo,
      });

      this.serverInfo = result.serverInfo;
      this.serverCapabilities = result.capabilities;
      this.status = 'connected';

      // Send initialized notification
      await this.sendNotification('notifications/initialized');

      return result;
    } catch (error) {
      this.status = 'error';
      throw error;
    }
  }

  disconnect(): void {
    this.status = 'disconnected';
    this.serverInfo = null;
    this.serverCapabilities = null;
  }

  getStatus(): MCPConnectionStatus {
    return this.status;
  }

  getServerCapabilities(): MCPServerCapabilities | null {
    return this.serverCapabilities;
  }

  getServerInfo(): MCPServerInfo | null {
    return this.serverInfo;
  }

  async ping(): Promise<boolean> {
    try {
      await this.sendRequest('ping', {});
      return true;
    } catch {
      return false;
    }
  }

  // ===========================================================================
  // Authentication
  // ===========================================================================

  setAuthToken(token: string | null): void {
    this.authToken = token;
  }

  // ===========================================================================
  // Tools
  // ===========================================================================

  async listTools(): Promise<MCPTool[]> {
    const result = await this.sendRequest<{ tools: MCPTool[] }>('tools/list', {});
    return result.tools;
  }

  async callTool(
    name: string,
    args?: Record<string, unknown>
  ): Promise<MCPToolResult> {
    return this.sendRequest<MCPToolResult>('tools/call', {
      name,
      arguments: args || {},
    });
  }

  async streamToolCall(
    name: string,
    args: Record<string, unknown>,
    onChunk: (chunk: MCPStreamChunk) => void,
    options?: MCPRequestOptions
  ): Promise<void> {
    const request = this.createRequest('tools/call', {
      name,
      arguments: args,
      _stream: true, // Hint for backend to use streaming
    });

    const response = await this.fetchWithOptions(`${this.baseUrl}/message`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(request),
      signal: options?.signal,
    });

    if (!response.ok) {
      throw new MCPClientError(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new MCPClientError('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim()) {
            try {
              const chunk = JSON.parse(line) as MCPStreamChunk;
              onChunk(chunk);
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      }

      // Process any remaining buffer
      if (buffer.trim()) {
        try {
          const chunk = JSON.parse(buffer) as MCPStreamChunk;
          onChunk(chunk);
        } catch {
          // Skip malformed JSON
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // ===========================================================================
  // Resources
  // ===========================================================================

  async listResources(): Promise<ResourceListResult> {
    return this.sendRequest<ResourceListResult>('resources/list', {});
  }

  async readResource(uri: string): Promise<ResourceReadResult> {
    return this.sendRequest<ResourceReadResult>('resources/read', { uri });
  }

  // ===========================================================================
  // Prompts
  // ===========================================================================

  async listPrompts(): Promise<MCPPrompt[]> {
    const result = await this.sendRequest<{ prompts: MCPPrompt[] }>('prompts/list', {});
    return result.prompts;
  }

  async getPrompt(
    name: string,
    args?: Record<string, string>
  ): Promise<PromptGetResult> {
    return this.sendRequest<PromptGetResult>('prompts/get', {
      name,
      arguments: args,
    });
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  private getNextId(): number {
    return ++this.requestId;
  }

  private createRequest<P>(method: string, params?: P): JSONRPCRequest<P> {
    return {
      jsonrpc: '2.0',
      id: this.getNextId(),
      method,
      params,
    };
  }

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json, application/x-ndjson',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  private async fetchWithOptions(
    url: string,
    init: RequestInit
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...init,
        signal: init.signal || controller.signal,
      });
      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async sendRequest<T>(method: string, params?: unknown): Promise<T> {
    const request = this.createRequest(method, params);

    let response: Response;
    try {
      response = await this.fetchWithOptions(`${this.baseUrl}/message`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(request),
      });
    } catch (error) {
      throw new MCPClientError(
        error instanceof Error ? error.message : 'Network error'
      );
    }

    if (!response.ok) {
      throw new MCPClientError(`HTTP ${response.status}: ${response.statusText}`);
    }

    const jsonResponse = (await response.json()) as JSONRPCResponse<T>;

    if (jsonResponse.error) {
      throw new MCPClientError(
        jsonResponse.error.message,
        jsonResponse.error.code,
        jsonResponse.error.data
      );
    }

    return jsonResponse.result as T;
  }

  private async sendNotification(method: string, params?: unknown): Promise<void> {
    const notification = {
      jsonrpc: '2.0' as const,
      method,
      params,
    };

    try {
      await this.fetchWithOptions(`${this.baseUrl}/message`, {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(notification),
      });
    } catch {
      // Notifications don't require responses
    }
  }
}

// =============================================================================
// Factory Function
// =============================================================================

export function createMCPClient(options: MCPClientOptions): MCPClient {
  return new MCPClientImpl(options);
}

// =============================================================================
// Export MCP Methods for convenience
// =============================================================================

export { MCP_METHODS } from './mcp-types';
