/**
 * InteractiveForm - Phase 2
 *
 * AI-generated interactive forms with validation
 * and various field types.
 */
import { useState, useCallback } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../utils/cn";

import { Button, Input, Select, Textarea, Checkbox } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface FormField {
  id: string;
  type: "text" | "email" | "number" | "select" | "checkbox" | "textarea";
  label: string;
  placeholder?: string;
  options?: string[];
  required?: boolean;
  validation?: {
    pattern?: string;
    min?: number;
    max?: number;
    message?: string;
  };
}

export interface FormConfig {
  id: string;
  title: string;
  description?: string;
  fields: FormField[];
  submitLabel?: string;
}

export interface InteractiveFormProps {
  config: FormConfig;
  onSubmit: (data: Record<string, string | boolean | number>) => void;
  isSubmitting?: boolean;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function InteractiveForm({
  config,
  onSubmit,
  isSubmitting = false,
  className,
}: InteractiveFormProps) {
  const [values, setValues] = useState<Record<string, string | boolean>>(() => {
    const initial: Record<string, string | boolean> = {};
    config.fields.forEach((field) => {
      initial[field.id] = field.type === "checkbox" ? false : "";
    });
    return initial;
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = useCallback(
    (fieldId: string, value: string | boolean) => {
      setValues((prev) => ({ ...prev, [fieldId]: value }));
      // Clear error when field is modified
      if (errors[fieldId]) {
        setErrors((prev) => {
          const next = { ...prev };
          delete next[fieldId];
          return next;
        });
      }
    },
    [errors],
  );

  const validate = useCallback(() => {
    const newErrors: Record<string, string> = {};

    config.fields.forEach((field) => {
      const value = values[field.id];

      if (field.required) {
        if (field.type === "checkbox") {
          // Checkboxes don't require true for required
        } else if (!value || (typeof value === "string" && !value.trim())) {
          newErrors[field.id] = `${field.label} is required`;
        }
      }

      if (field.validation?.pattern && typeof value === "string" && value) {
        const regex = new RegExp(field.validation.pattern);
        if (!regex.test(value)) {
          newErrors[field.id] = field.validation.message || "Invalid format";
        }
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [config.fields, values]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validate()) return;

    onSubmit(values);
  };

  const renderField = (field: FormField) => {
    const value = values[field.id];
    const error = errors[field.id];
    const inputId = `field-${field.id}`;

    const baseInputClass = cn(
      "w-full px-3 py-2 rounded-lg",
      "bg-neutral-50 dark:bg-neutral-900",
      "border",
      error ? "border-error-500" : "border-neutral-200 dark:border-neutral-700",
      "text-neutral-900 dark:text-neutral-100",
      "placeholder-neutral-500 dark:placeholder-neutral-400",
      "focus:outline-none focus:ring-2 focus:ring-primary-500",
    );

    switch (field.type) {
      case "text":
      case "email":
      case "number":
        return (
          <Input
            id={inputId}
            type={field.type}
            value={value as string}
            onChange={(e) => handleChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            aria-required={field.required}
            className={baseInputClass}
          />
        );

      case "textarea":
        return (
          <Textarea
            id={inputId}
            value={value as string}
            onChange={(e) => handleChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            aria-required={field.required}
            rows={3}
            className={baseInputClass}
          />
        );

      case "select":
        return (
          <Select
            id={inputId}
            value={value as string}
            onChange={(e) => handleChange(field.id, e.target.value)}
            aria-required={field.required}
            className={baseInputClass}
          >
            <option value="">Select an option</option>
            {field.options?.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
        );

      case "checkbox":
        return (
          <Checkbox
            id={inputId}
            checked={value as boolean}
            onChange={(checked) => handleChange(field.id, checked)}
            required={field.required}
          />
        );

      default:
        return null;
    }
  };

  return (
    <form
      data-testid="interactive-form"
      role="form"
      noValidate
      onSubmit={handleSubmit}
      className={cn(
        "bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6",
        className,
      )}
    >
      {/* Title */}
      <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
        {config.title}
      </h2>
      {/* Description */}
      {config.description && (
        <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
          {config.description}
        </p>
      )}
      {/* Fields */}
      <div className="space-y-4">
        {config.fields.map((field) => (
          <div
            key={field.id}
            className={cn(
              "flex",
              field.type === "checkbox"
                ? "items-center gap-2"
                : "flex-col gap-1",
            )}
          >
            <label
              htmlFor={`field-${field.id}`}
              className={cn(
                "text-sm font-medium text-neutral-700 dark:text-neutral-300",
                field.type === "checkbox" && "order-2",
              )}
            >
              {field.label}
              {field.required && <span className="text-error-500 ml-1">*</span>}
            </label>

            {renderField(field)}

            {errors[field.id] && (
              <span
                data-testid={`error-${field.id}`}
                className="text-xs text-error-500"
              >
                {errors[field.id]}
              </span>
            )}
          </div>
        ))}
      </div>
      {/* Submit Button */}
      <Button
        type="submit"
        disabled={isSubmitting}
        className={cn(
          "mt-6 w-full px-4 py-2 rounded-lg",
          "bg-primary-500 text-white font-medium",
          "hover:bg-primary-600",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "transition-colors",
          "flex items-center justify-center gap-2",
        )}
      >
        {isSubmitting && (
          <Loader2
            data-testid="submit-spinner"
            size={16}
            className="animate-spin"
          />
        )}
        {config.submitLabel || "Submit"}
      </Button>
    </form>
  );
}
