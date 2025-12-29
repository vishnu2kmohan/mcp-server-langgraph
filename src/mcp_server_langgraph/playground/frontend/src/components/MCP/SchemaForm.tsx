/**
 * SchemaForm Component
 *
 * Dynamically generates a form from a JSON schema.
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';
import type { JSONSchema } from '../../api/mcp-types';

export interface SchemaFormProps {
  schema: JSONSchema;
  onSubmit: (data: Record<string, unknown>) => void;
  onChange?: (data: Record<string, unknown>) => void;
  initialValues?: Record<string, unknown>;
  submitLabel?: string;
}

function getDefaultValue(property: JSONSchema): unknown {
  if (property.default !== undefined) return property.default;
  if (property.type === 'boolean') return false;
  if (property.type === 'number' || property.type === 'integer') return '';
  if (property.enum && property.enum.length > 0) return property.enum[0];
  return '';
}

function capitalizeLabel(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/([A-Z])/g, ' $1');
}

export function SchemaForm({
  schema,
  onSubmit,
  onChange,
  initialValues = {},
  submitLabel = 'Submit',
}: SchemaFormProps): React.ReactElement {
  const properties = schema.properties || {};
  const required = schema.required || [];

  const [formData, setFormData] = useState<Record<string, unknown>>(() => {
    const initial: Record<string, unknown> = {};
    Object.entries(properties).forEach(([key, prop]) => {
      initial[key] = initialValues[key] ?? getDefaultValue(prop as JSONSchema);
    });
    return initial;
  });

  const handleChange = useCallback(
    (key: string, value: unknown) => {
      setFormData((prev) => {
        const updated = { ...prev, [key]: value };
        onChange?.(updated);
        return updated;
      });
    },
    [onChange]
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      onSubmit(formData);
    },
    [formData, onSubmit]
  );

  return (
    <form onSubmit={handleSubmit} role="form" className="space-y-4">
      {Object.entries(properties).map(([key, prop]) => {
        const property = prop as JSONSchema;
        const isRequired = required.includes(key);
        const label = capitalizeLabel(key);
        const inputId = `schema-field-${key}`;

        return (
          <div key={key} className="space-y-1">
            <label
              htmlFor={inputId}
              className="block text-sm font-medium text-gray-700 dark:text-dark-textSecondary"
            >
              {label}
              {isRequired && <span className="text-error-500 ml-1">*</span>}
            </label>

            {/* Enum - Select */}
            {property.enum ? (
              <select
                id={inputId}
                value={String(formData[key])}
                onChange={(e) => handleChange(key, e.target.value)}
                required={isRequired}
                className={clsx(
                  'w-full px-3 py-2 border rounded-lg',
                  'bg-white dark:bg-dark-surface',
                  'border-gray-300 dark:border-dark-border',
                  'text-gray-900 dark:text-dark-text',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500'
                )}
              >
                {property.enum.map((option) => (
                  <option key={String(option)} value={String(option)}>
                    {String(option)}
                  </option>
                ))}
              </select>
            ) : property.type === 'boolean' ? (
              /* Boolean - Checkbox */
              <div className="flex items-center">
                <input
                  id={inputId}
                  type="checkbox"
                  checked={Boolean(formData[key])}
                  onChange={(e) => handleChange(key, e.target.checked)}
                  className="h-4 w-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
              </div>
            ) : property.type === 'number' || property.type === 'integer' ? (
              /* Number - Number input */
              <input
                id={inputId}
                type="number"
                value={formData[key] as number | string}
                onChange={(e) =>
                  handleChange(
                    key,
                    e.target.value === '' ? '' : Number(e.target.value)
                  )
                }
                required={isRequired}
                min={property.minimum}
                max={property.maximum}
                className={clsx(
                  'w-full px-3 py-2 border rounded-lg',
                  'bg-white dark:bg-dark-surface',
                  'border-gray-300 dark:border-dark-border',
                  'text-gray-900 dark:text-dark-text',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500'
                )}
              />
            ) : (
              /* String - Text input */
              <input
                id={inputId}
                type={property.format === 'email' ? 'email' : 'text'}
                value={formData[key] as string}
                onChange={(e) => handleChange(key, e.target.value)}
                required={isRequired}
                className={clsx(
                  'w-full px-3 py-2 border rounded-lg',
                  'bg-white dark:bg-dark-surface',
                  'border-gray-300 dark:border-dark-border',
                  'text-gray-900 dark:text-dark-text',
                  'focus:outline-none focus:ring-2 focus:ring-primary-500'
                )}
              />
            )}

            {/* Description as help text */}
            {property.description && (
              <p className="text-xs text-gray-500 dark:text-dark-textMuted">
                {property.description}
              </p>
            )}
          </div>
        );
      })}

      <button
        type="submit"
        className={clsx(
          'w-full px-4 py-2 rounded-lg font-medium',
          'bg-primary-600 text-white',
          'hover:bg-primary-700',
          'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
        )}
      >
        {submitLabel}
      </button>
    </form>
  );
}
