/**
 * InboundElicitationModal Component
 *
 * A modal for handling server-initiated elicitation JSON-RPC requests.
 * When an MCP server sends an elicitation/create request, this modal
 * displays the request and allows the user to respond or cancel.
 *
 * Features:
 * - Dynamic form generation from JSON schema
 * - Required field validation
 * - Accessible dialog with focus management
 * - Support for both numeric and string JSON-RPC IDs
 *
 * @see ADR-0069 MCP 2025-11-25 Upgrade
 */

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { X, Server } from "lucide-react";
import { Button, Input, Checkbox } from "@/components/UI";
import { parseSchemaToFields, getInputType } from "@/utils/schemaForm";
import type { PendingElicitation } from "@/types/mcp";

// ============================================================================
// Types
// ============================================================================

export interface InboundElicitationModalProps {
  /** The pending elicitation request */
  request: PendingElicitation;
  /** Called when user submits a response */
  onRespond: (result: Record<string, unknown>) => void;
  /** Called when user cancels the request */
  onCancel: () => void;
}

// ============================================================================
// Component
// ============================================================================

export function InboundElicitationModal({
  request,
  onRespond,
  onCancel,
}: InboundElicitationModalProps) {
  // Parse schema to form fields
  const fields = useMemo(
    () => parseSchemaToFields(request.requestedSchema),
    [request.requestedSchema],
  );

  // Form state - initialize with default values
  const [formValues, setFormValues] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    fields.forEach((field) => {
      if (field.defaultValue !== undefined) {
        initial[field.name] = field.defaultValue;
      } else if (field.type === "boolean") {
        initial[field.name] = false;
      } else {
        initial[field.name] = "";
      }
    });
    return initial;
  });

  // Focus management
  const firstInputRef = useRef<HTMLInputElement>(null);

  // Focus first input on mount
  useEffect(() => {
    if (firstInputRef.current) {
      firstInputRef.current.focus();
    }
  }, []);

  // Validate form
  const isFormValid = useMemo(() => {
    return fields
      .filter((field) => field.required)
      .every((field) => {
        const value = formValues[field.name];
        if (field.type === "boolean") return true; // Booleans are always valid
        if (typeof value === "string") return value.trim() !== "";
        if (typeof value === "number") return !isNaN(value);
        return value !== undefined && value !== null && value !== "";
      });
  }, [fields, formValues]);

  // Handle field change
  const handleChange = useCallback(
    (name: string, value: unknown, type: string) => {
      setFormValues((prev) => ({
        ...prev,
        [name]:
          type === "number" || type === "integer"
            ? value === ""
              ? ""
              : Number(value)
            : value,
      }));
    },
    [],
  );

  // Handle form submission
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!isFormValid) return;

      // Clean up the values (remove empty strings for optional fields)
      const result: Record<string, unknown> = {};
      fields.forEach((field) => {
        const value = formValues[field.name];
        if (
          field.required ||
          (typeof value === "string" && value.trim() !== "") ||
          (typeof value === "number" && !isNaN(value)) ||
          typeof value === "boolean"
        ) {
          result[field.name] = value;
        }
      });

      onRespond(result);
    },
    [fields, formValues, isFormValid, onRespond],
  );

  return (
    <div
      role="dialog"
      aria-labelledby="elicitation-modal-title"
      aria-describedby="elicitation-modal-message"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        data-testid="modal-backdrop"
        className="absolute inset-0 bg-neutral-a6"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Modal content */}
      <div className="relative z-10 w-full max-w-lg rounded-lg bg-neutral-1 p-6 shadow-xl">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="elicitation-modal-title"
            className="text-lg font-semibold text-neutral-12"
          >
            Elicitation Request
          </h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            className="p-1"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Server info */}
        <div className="mb-4 flex items-center gap-2 text-sm text-neutral-10">
          <Server className="h-4 w-4" />
          <span>From: {request.serverId}</span>
        </div>

        {/* Message */}
        <p id="elicitation-modal-message" className="mb-6 text-neutral-11">
          {request.message}
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {fields.map((field, index) => (
            <div key={field.name} className="space-y-1">
              {field.type === "boolean" ? (
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`field-${field.name}`}
                    checked={formValues[field.name] as boolean}
                    onChange={(checked) =>
                      handleChange(field.name, checked, field.type)
                    }
                    aria-describedby={
                      field.description
                        ? `field-${field.name}-description`
                        : undefined
                    }
                  />
                  <label
                    htmlFor={`field-${field.name}`}
                    className="text-sm font-medium text-neutral-12"
                  >
                    {field.name}
                    {field.required && (
                      <span className="ml-1 text-danger-9">*</span>
                    )}
                  </label>
                </div>
              ) : (
                <>
                  <label
                    htmlFor={`field-${field.name}`}
                    className="block text-sm font-medium text-neutral-12"
                  >
                    {field.name}
                    {field.required && (
                      <span className="ml-1 text-danger-9">*</span>
                    )}
                  </label>
                  <Input
                    ref={index === 0 ? firstInputRef : undefined}
                    id={`field-${field.name}`}
                    type={getInputType(field.type)}
                    value={formValues[field.name] as string | number}
                    onChange={(e) =>
                      handleChange(field.name, e.target.value, field.type)
                    }
                    required={field.required}
                    aria-describedby={
                      field.description
                        ? `field-${field.name}-description`
                        : undefined
                    }
                    className="w-full"
                  />
                </>
              )}
              {field.description && (
                <p
                  id={`field-${field.name}-description`}
                  className="text-xs text-neutral-10"
                >
                  {field.description}
                </p>
              )}
            </div>
          ))}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="secondary" onClick={onCancel}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" disabled={!isFormValid}>
              Respond
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default InboundElicitationModal;
