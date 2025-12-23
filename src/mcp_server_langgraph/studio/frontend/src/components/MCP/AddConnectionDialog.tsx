/**
 * AddConnectionDialog
 *
 * Modal dialog for adding a new MCP connection with:
 * - Name and description
 * - URL
 * - Transport protocol (Streamable HTTP or stdio)
 * - Authentication type (None, API Key, OAuth2)
 * - Transport-specific fields (stdio: command, args, env)
 * - Auth-specific fields (api_key, oauth2 config)
 *
 * Per MCP 2025-11-25 specification.
 */

import { useState, useCallback } from "react";
import { X, Loader2 } from "lucide-react";
import type {
  MCPConnectionCreate,
  TransportProtocol,
  AuthType,
} from "../../types/connection";

export interface AddConnectionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: MCPConnectionCreate) => Promise<void> | void;
  isLoading?: boolean;
}

interface FormErrors {
  name?: string;
  url?: string;
  command?: string;
}

export function AddConnectionDialog({
  isOpen,
  onClose,
  onSubmit,
  isLoading = false,
}: AddConnectionDialogProps) {
  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [url, setUrl] = useState("");
  const [transport, setTransport] =
    useState<TransportProtocol>("streamable_http");
  const [authType, setAuthType] = useState<AuthType>("none");

  // Stdio transport fields
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [env, setEnv] = useState("");

  // Auth fields
  const [apiKey, setApiKey] = useState("");
  const [oauth2ClientId, setOauth2ClientId] = useState("");
  const [oauth2Scopes, setOauth2Scopes] = useState("");

  // Validation errors
  const [errors, setErrors] = useState<FormErrors>({});

  const resetForm = useCallback(() => {
    setName("");
    setDescription("");
    setUrl("");
    setTransport("streamable_http");
    setAuthType("none");
    setCommand("");
    setArgs("");
    setEnv("");
    setApiKey("");
    setOauth2ClientId("");
    setOauth2Scopes("");
    setErrors({});
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose, resetForm]);

  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    // Name is required
    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    // URL is required
    if (!url.trim()) {
      newErrors.url = "URL is required";
    } else if (transport === "streamable_http") {
      // Validate URL format for HTTP transport
      try {
        new URL(url);
      } catch {
        newErrors.url = "Please enter a valid URL";
      }
    }

    // Command is required for stdio transport
    if (transport === "stdio" && !command.trim()) {
      newErrors.command = "Command is required for stdio transport";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [name, url, transport, command]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!validateForm()) {
        return;
      }

      // Build connection data
      const data: MCPConnectionCreate = {
        name: name.trim(),
        description: description.trim() || undefined,
        url: url.trim(),
        transport,
        auth_type: authType,
      };

      // Add stdio fields if applicable
      if (transport === "stdio") {
        data.command = command.trim();
        if (args.trim()) {
          data.args = args.trim().split(/\s+/);
        }
        if (env.trim()) {
          // Parse env as KEY=VALUE pairs
          const envObj: Record<string, string> = {};
          env
            .trim()
            .split("\n")
            .forEach((line) => {
              const [key, ...valueParts] = line.split("=");
              if (key && valueParts.length > 0) {
                envObj[key.trim()] = valueParts.join("=").trim();
              }
            });
          if (Object.keys(envObj).length > 0) {
            data.env = envObj;
          }
        }
      }

      // Add auth fields if applicable
      if (authType === "api_key" && apiKey.trim()) {
        data.api_key = apiKey.trim();
      }

      if (authType === "oauth2") {
        if (oauth2ClientId.trim()) {
          data.oauth2_client_id = oauth2ClientId.trim();
        }
        if (oauth2Scopes.trim()) {
          data.oauth2_scopes = oauth2Scopes.trim().split(/\s+/);
        }
      }

      await onSubmit(data);
      handleClose();
    },
    [
      validateForm,
      name,
      description,
      url,
      transport,
      authType,
      command,
      args,
      env,
      apiKey,
      oauth2ClientId,
      oauth2Scopes,
      onSubmit,
      handleClose,
    ],
  );

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2
            id="dialog-title"
            className="text-lg font-semibold text-gray-900 dark:text-gray-100"
          >
            Add MCP Connection
          </h2>
          <button
            onClick={handleClose}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Name */}
          <div>
            <label
              htmlFor="connection-name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Name
            </label>
            <input
              id="connection-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Zapier MCP"
              className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.name
                  ? "border-red-500"
                  : "border-gray-300 dark:border-gray-600"
              }`}
              aria-invalid={!!errors.name}
              aria-describedby={errors.name ? "name-error" : undefined}
            />
            {errors.name && (
              <p id="name-error" className="mt-1 text-sm text-red-600">
                {errors.name}
              </p>
            )}
          </div>

          {/* Description */}
          <div>
            <label
              htmlFor="connection-description"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Description
            </label>
            <textarea
              id="connection-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          {/* URL */}
          <div>
            <label
              htmlFor="connection-url"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              URL
            </label>
            <input
              id="connection-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://mcp.example.com"
              className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                errors.url
                  ? "border-red-500"
                  : "border-gray-300 dark:border-gray-600"
              }`}
              aria-invalid={!!errors.url}
              aria-describedby={errors.url ? "url-error" : undefined}
            />
            {errors.url && (
              <p id="url-error" className="mt-1 text-sm text-red-600">
                {errors.url}
              </p>
            )}
          </div>

          {/* Transport Protocol */}
          <div>
            <label
              htmlFor="connection-transport"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Transport Protocol
            </label>
            <select
              id="connection-transport"
              value={transport}
              onChange={(e) =>
                setTransport(e.target.value as TransportProtocol)
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="streamable_http">Streamable HTTP</option>
              <option value="stdio">stdio</option>
            </select>
          </div>

          {/* Stdio-specific fields */}
          {transport === "stdio" && (
            <>
              <div>
                <label
                  htmlFor="connection-command"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Command
                </label>
                <input
                  id="connection-command"
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="e.g., python or npx"
                  className={`w-full px-3 py-2 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                    errors.command
                      ? "border-red-500"
                      : "border-gray-300 dark:border-gray-600"
                  }`}
                  aria-invalid={!!errors.command}
                  aria-describedby={
                    errors.command ? "command-error" : undefined
                  }
                />
                {errors.command && (
                  <p id="command-error" className="mt-1 text-sm text-red-600">
                    {errors.command}
                  </p>
                )}
              </div>

              <div>
                <label
                  htmlFor="connection-args"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Arguments
                </label>
                <input
                  id="connection-args"
                  type="text"
                  value={args}
                  onChange={(e) => setArgs(e.target.value)}
                  placeholder="e.g., -m mcp_server --port 3000"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Space-separated arguments
                </p>
              </div>
            </>
          )}

          {/* Authentication Type */}
          <div>
            <label
              htmlFor="connection-auth"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Authentication
            </label>
            <select
              id="connection-auth"
              value={authType}
              onChange={(e) => setAuthType(e.target.value as AuthType)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="none">None</option>
              <option value="api_key">API Key</option>
              <option value="oauth2">OAuth2</option>
            </select>
          </div>

          {/* API Key field */}
          {authType === "api_key" && (
            <div>
              <label
                htmlFor="connection-api-key"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                API Key
              </label>
              <input
                id="connection-api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your API key"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          )}

          {/* OAuth2 fields */}
          {authType === "oauth2" && (
            <>
              <div>
                <label
                  htmlFor="connection-oauth-client-id"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Client ID
                </label>
                <input
                  id="connection-oauth-client-id"
                  type="text"
                  value={oauth2ClientId}
                  onChange={(e) => setOauth2ClientId(e.target.value)}
                  placeholder="OAuth2 Client ID"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label
                  htmlFor="connection-oauth-scopes"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Scopes
                </label>
                <input
                  id="connection-oauth-scopes"
                  type="text"
                  value={oauth2Scopes}
                  onChange={(e) => setOauth2Scopes(e.target.value)}
                  placeholder="e.g., read write"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Space-separated scopes
                </p>
              </div>
            </>
          )}

          {/* Footer */}
          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={handleClose}
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Adding...
                </>
              ) : (
                "Add Connection"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AddConnectionDialog;
