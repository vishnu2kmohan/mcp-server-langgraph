/**
 * InteractiveForm - Phase 2
 *
 * AI-generated interactive forms with validation
 * and various field types.
 */
import { useState, useCallback } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../utils/cn";

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
      "bg-gray-50 dark:bg-gray-900",
      "border",
      error ? "border-red-500" : "border-gray-200 dark:border-gray-700",
      "text-gray-900 dark:text-gray-100",
      "placeholder-gray-500 dark:placeholder-gray-400",
      "focus:outline-none focus:ring-2 focus:ring-primary-500",
    );

    switch (field.type) {
      case "text":
      case "email":
      case "number":
        return (
          <input
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
          <textarea
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
          <select
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
          </select>
        );

      case "checkbox":
        return (
          <input
            id={inputId}
            type="checkbox"
            checked={value as boolean}
            onChange={(e) => handleChange(field.id, e.target.checked)}
            aria-required={field.required}
            className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-500 focus:ring-primary-500"
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
        "bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6",
        className,
      )}
    >
      {/* Title */}
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
        {config.title}
      </h2>

      {/* Description */}
      {config.description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
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
                "text-sm font-medium text-gray-700 dark:text-gray-300",
                field.type === "checkbox" && "order-2",
              )}
            >
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </label>

            {renderField(field)}

            {errors[field.id] && (
              <span
                data-testid={`error-${field.id}`}
                className="text-xs text-red-500"
              >
                {errors[field.id]}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Submit Button */}
      <button
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
      </button>
    </form>
  );
}
