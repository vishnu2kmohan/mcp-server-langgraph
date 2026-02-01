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
  ConnectionScope,
} from "../../types/connection";
import {
  useCreateConnectionMutation,
  useUpdateConnectionMutation,
} from "../../api";
import { Dialog } from "../UI/Dialog";

import { Button, Input, Select, Textarea } from "@/components/UI";
import { ScopeSelector } from "./ScopeSelector";

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
  const [scope, setScope] = useState<ConnectionScope>("user");
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
        setScope(connection.scope || "user");
        if (connection.oauth2Config) {
          setClientId(connection.oauth2Config.clientId || "");
          setScopes(connection.oauth2Config.scopes.join(" "));
        }
      } else {
        setName("");
        setUrl("");
        setDescription("");
        setAuthType("none");
        setScope("user");
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
          scope: scope,
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
      <Button
        variant="secondary"
        className="px-4 py-2 text-neutral-11 hover:bg-neutral-2 rounded-md"
        onClick={onClose}
        disabled={isLoading}
      >
        Cancel
      </Button>
      <Button
        variant="primary"
        className="px-4 py-2 bg-primary-10 text-neutral-12 hover:bg-primary-11 rounded-md"
        onClick={handleSubmit}
        disabled={isLoading}
      >
        {isLoading ? "Saving..." : "Save"}
      </Button>
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
          className="block text-sm font-medium text-neutral-11 mb-1"
        >
          Name
        </label>
        <Input
          id="name"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            if (errors.name) setErrors({ ...errors, name: undefined });
          }}
          className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-7 ${
            errors.name ? "border-error-9" : "border-neutral-5"
          }`}
          placeholder="My MCP Server"
        />
        {errors.name && (
          <p className="mt-1 text-sm text-error-9">{errors.name}</p>
        )}
      </div>
      {/* URL */}
      <div>
        <label
          htmlFor="url"
          className="block text-sm font-medium text-neutral-11 mb-1"
        >
          URL
        </label>
        <Input
          id="url"
          value={url}
          onChange={(e) => {
            setUrl(e.target.value);
            if (errors.url) setErrors({ ...errors, url: undefined });
          }}
          className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-7 ${
            errors.url ? "border-error-9" : "border-neutral-5"
          }`}
          placeholder="https://mcp.example.com"
        />
        {errors.url && (
          <p className="mt-1 text-sm text-error-9">{errors.url}</p>
        )}
      </div>
      {/* Description */}
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-neutral-11 mb-1"
        >
          Description
        </label>
        <Textarea
          className="px-3 py-2 focus:ring-primary-7"
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
          rows={2}
        />
      </div>
      {/* Auth Type */}
      <div>
        <label
          htmlFor="auth_type"
          className="block text-sm font-medium text-neutral-11 mb-1"
        >
          Authentication
        </label>
        <Select
          className="px-3 py-2 focus:ring-primary-7"
          id="auth_type"
          value={authType}
          onChange={(e) => setAuthType(e.target.value as AuthType)}
          disabled={isEditing} // Can't change auth type when editing
        >
          <option value="none">No Authentication</option>
          <option value="api_key">API Key</option>
          <option value="oauth2">OAuth2</option>
        </Select>
      </div>
      {/* Scope Selector (ADR-0102 Phase 6) */}
      <div>
        <label className="block text-sm font-medium text-neutral-11 mb-2">
          Access Scope
        </label>
        <ScopeSelector value={scope} onChange={setScope} disabled={isEditing} />
        {isEditing && (
          <p className="mt-1 text-xs text-neutral-10">
            Scope cannot be changed after creation
          </p>
        )}
      </div>

      {/* API Key (conditional) */}
      {authType === "api_key" && (
        <div>
          <label
            htmlFor="api_key"
            className="block text-sm font-medium text-neutral-11 mb-1"
          >
            API Key
          </label>
          <Input
            id="api_key"
            type="password"
            value={apiKey}
            onChange={(e) => {
              setApiKey(e.target.value);
              if (errors.apiKey) setErrors({ ...errors, apiKey: undefined });
            }}
            className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-7 ${
              errors.apiKey ? "border-error-9" : "border-neutral-5"
            }`}
            placeholder="Enter your API key"
          />
          {errors.apiKey && (
            <p className="mt-1 text-sm text-error-9">{errors.apiKey}</p>
          )}
        </div>
      )}
      {/* OAuth2 fields (conditional) */}
      {authType === "oauth2" && (
        <>
          <div>
            <label
              htmlFor="client_id"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Client ID
            </label>
            <Input
              id="client_id"
              value={clientId}
              onChange={(e) => {
                setClientId(e.target.value);
                if (errors.clientId)
                  setErrors({ ...errors, clientId: undefined });
              }}
              className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-primary-7 ${
                errors.clientId ? "border-error-9" : "border-neutral-5"
              }`}
              placeholder="OAuth2 client ID"
            />
            {errors.clientId && (
              <p className="mt-1 text-sm text-error-9">{errors.clientId}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="client_secret"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Client Secret
            </label>
            <Input
              className="px-3 py-2 focus:ring-primary-7"
              id="client_secret"
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              placeholder="Optional client secret"
            />
            <p className="mt-1 text-xs text-neutral-10">
              Not required for PKCE flow
            </p>
          </div>

          <div>
            <label
              htmlFor="scopes"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Scopes
            </label>
            <Input
              className="px-3 py-2 focus:ring-primary-7"
              id="scopes"
              value={scopes}
              onChange={(e) => setScopes(e.target.value)}
              placeholder="read write tools (space-separated)"
            />
          </div>
        </>
      )}
    </Dialog>
  );
}
