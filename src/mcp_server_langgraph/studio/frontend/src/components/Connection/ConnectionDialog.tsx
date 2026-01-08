/**
 * ConnectionDialog Component
 *
 * Dialog for creating and editing MCP server connections.
 * Supports:
 * - No authentication
 * - API Key authentication
 * - OAuth2 authentication with PKCE
 *
 * Uses the base Dialog component for consistent modal behavior.
 */

import { useState, useEffect } from "react";
import type {
  MCPConnectionCamelCase,
  MCPConnectionCreate,
  AuthType,
} from "../../types/connection";
import {
  useCreateConnectionMutation,
  useUpdateConnectionMutation,
} from "../../api";
import { Dialog } from "../UI/Dialog";

interface ConnectionDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  connection?: MCPConnectionCamelCase;
  projectId?: string;
}

interface FormErrors {
  name?: string;
  url?: string;
  apiKey?: string;
  clientId?: string;
}

export function ConnectionDialog({
  open,
  onClose,
  onSuccess,
  connection,
  projectId,
}: ConnectionDialogProps) {
  const [createConnection, { isLoading: isCreating }] =
    useCreateConnectionMutation();
  const [updateConnection, { isLoading: isUpdating }] =
    useUpdateConnectionMutation();

  const isEditing = !!connection;
  const isLoading = isCreating || isUpdating;

  // Form state
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [authType, setAuthType] = useState<AuthType>("none");
  const [apiKey, setApiKey] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [scopes, setScopes] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});

  // Reset form when dialog opens or connection changes
  useEffect(() => {
    if (open) {
      if (connection) {
        setName(connection.name);
        setUrl(connection.url);
        setDescription(connection.description || "");
        setAuthType(connection.authType);
        if (connection.oauth2Config) {
          setClientId(connection.oauth2Config.clientId || "");
          setScopes(connection.oauth2Config.scopes.join(" "));
        }
      } else {
        setName("");
        setUrl("");
        setDescription("");
        setAuthType("none");
        setApiKey("");
        setClientId("");
        setClientSecret("");
        setScopes("");
      }
      setErrors({});
    }
  }, [open, connection]);

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = "Name is required";
    }

    if (!url.trim()) {
      newErrors.url = "URL is required";
    } else {
      try {
        new URL(url);
      } catch {
        newErrors.url = "Please enter a valid URL";
      }
    }

    if (authType === "api_key" && !apiKey.trim()) {
      newErrors.apiKey = "API Key is required";
    }

    if (authType === "oauth2" && !clientId.trim()) {
      newErrors.clientId = "Client ID is required";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      if (isEditing) {
        await updateConnection({
          id: connection.id,
          name,
          description: description || null,
          url,
        }).unwrap();
      } else {
        // Build connection data (camelCase - transformed at API boundary per ADR-0091)
        const data: MCPConnectionCreate = {
          name,
          url,
          description: description || null,
          authType: authType,
          projectId: projectId || null,
        };

        if (authType === "api_key") {
          data.apiKey = apiKey;
        }

        if (authType === "oauth2") {
          data.oauth2ClientId = clientId;
          data.oauth2ClientSecret = clientSecret || null;
          data.oauth2Scopes = scopes.split(/\s+/).filter(Boolean);
        }

        await createConnection(data).unwrap();
      }

      onSuccess();
      onClose();
    } catch (error) {
      // Error handling is managed by RTK Query
      console.error("Failed to save connection:", error);
    }
  };

  const footerContent = (
    <>
      <button
        onClick={onClose}
        className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-md"
        disabled={isLoading}
      >
        Cancel
      </button>
      <button
        onClick={handleSubmit}
        className="px-4 py-2 bg-primary-600 text-white hover:bg-primary-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={isLoading}
      >
        {isLoading ? "Saving..." : "Save"}
      </button>
    </>
  );

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={isEditing ? "Edit Connection" : "Add Connection"}
      footer={footerContent}
      contentClassName="space-y-4"
    >
      {/* Name */}
      <div>
        <label
          htmlFor="name"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Name
        </label>
        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (errors.name) setErrors({ ...errors, name: undefined });
          }}
          className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
            errors.name
              ? "border-error-500"
              : "border-gray-300 dark:border-gray-600"
          }`}
          placeholder="My MCP Server"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-error-500">{errors.name}</p>
        )}
      </div>

      {/* URL */}
      <div>
        <label
          htmlFor="url"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          URL
        </label>
        <input
          id="url"
          type="text"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (errors.url) setErrors({ ...errors, url: undefined });
          }}
          className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
            errors.url
              ? "border-error-500"
              : "border-gray-300 dark:border-gray-600"
          }`}
          placeholder="https://mcp.example.com"
        />
        {errors.url && (
          <p className="mt-1 text-sm text-error-500">{errors.url}</p>
        )}
      </div>

      {/* Description */}
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Description
        </label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          placeholder="Optional description"
          rows={2}
        />
      </div>

      {/* Auth Type */}
      <div>
        <label
          htmlFor="auth_type"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
        >
          Authentication
        </label>
        <select
          id="auth_type"
          value={authType}
          onChange={(e) => setAuthType(e.target.value as AuthType)}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          disabled={isEditing} // Can't change auth type when editing
        >
          <option value="none">No Authentication</option>
          <option value="api_key">API Key</option>
          <option value="oauth2">OAuth2</option>
        </select>
      </div>

      {/* API Key (conditional) */}
      {authType === "api_key" && (
        <div>
          <label
            htmlFor="api_key"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            API Key
          </label>
          <input
            id="api_key"
            type="password"
            value={apiKey}
            onChange={(e) => {
              setApiKey(e.target.value);
              if (errors.apiKey) setErrors({ ...errors, apiKey: undefined });
            }}
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
              errors.apiKey
                ? "border-error-500"
                : "border-gray-300 dark:border-gray-600"
            }`}
            placeholder="Enter your API key"
          />
          {errors.apiKey && (
            <p className="mt-1 text-sm text-error-500">{errors.apiKey}</p>
          )}
        </div>
      )}

      {/* OAuth2 fields (conditional) */}
      {authType === "oauth2" && (
        <>
          <div>
            <label
              htmlFor="client_id"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Client ID
            </label>
            <input
              id="client_id"
              type="text"
              value={clientId}
              onChange={(e) => {
                setClientId(e.target.value);
                if (errors.clientId)
                  setErrors({ ...errors, clientId: undefined });
              }}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                errors.clientId
                  ? "border-error-500"
                  : "border-gray-300 dark:border-gray-600"
              }`}
              placeholder="OAuth2 client ID"
            />
            {errors.clientId && (
              <p className="mt-1 text-sm text-error-500">{errors.clientId}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="client_secret"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Client Secret
            </label>
            <input
              id="client_secret"
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="Optional client secret"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Not required for PKCE flow
            </p>
          </div>

          <div>
            <label
              htmlFor="scopes"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Scopes
            </label>
            <input
              id="scopes"
              type="text"
              value={scopes}
              onChange={(e) => setScopes(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-primary-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="read write tools (space-separated)"
            />
          </div>
        </>
      )}
    </Dialog>
  );
}
