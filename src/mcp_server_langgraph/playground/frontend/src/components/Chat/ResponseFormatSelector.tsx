/**
 * ResponseFormatSelector Component
 *
 * Allows users to toggle between concise and detailed response formats.
 * Persists preference to localStorage.
 */

import React, { useState, useCallback, useEffect } from 'react';
import clsx from 'clsx';

export type ResponseFormat = 'concise' | 'detailed';

export interface ResponseFormatSelectorProps {
  value?: ResponseFormat;
  onChange?: (format: ResponseFormat) => void;
  className?: string;
}

const STORAGE_KEY = 'playground_response_format';

export function ResponseFormatSelector({
  value,
  onChange,
  className,
}: ResponseFormatSelectorProps): React.ReactElement {
  const [format, setFormat] = useState<ResponseFormat>(() => {
    if (value) return value;
    const stored = localStorage.getItem(STORAGE_KEY);
    return (stored as ResponseFormat) || 'detailed';
  });

  // Sync with controlled value
  useEffect(() => {
    if (value && value !== format) {
      setFormat(value);
    }
  }, [value, format]);

  const handleChange = useCallback(
    (newFormat: ResponseFormat) => {
      setFormat(newFormat);
      localStorage.setItem(STORAGE_KEY, newFormat);
      onChange?.(newFormat);
    },
    [onChange]
  );

  return (
    <div className={clsx('inline-flex items-center gap-1', className)}>
      <span className="text-xs text-gray-500 dark:text-dark-textMuted mr-2">
        Response:
      </span>
      <div className="inline-flex rounded-lg bg-gray-100 dark:bg-dark-bg p-0.5">
        <button
          onClick={() => handleChange('concise')}
          className={clsx(
            'px-3 py-1 text-xs font-medium rounded-md transition-colors',
            format === 'concise'
              ? 'bg-white dark:bg-dark-surface text-gray-900 dark:text-dark-text shadow-sm'
              : 'text-gray-600 dark:text-dark-textSecondary hover:text-gray-900 dark:hover:text-dark-text'
          )}
          aria-pressed={format === 'concise'}
          title="Shorter, more direct responses"
        >
          Concise
        </button>
        <button
          onClick={() => handleChange('detailed')}
          className={clsx(
            'px-3 py-1 text-xs font-medium rounded-md transition-colors',
            format === 'detailed'
              ? 'bg-white dark:bg-dark-surface text-gray-900 dark:text-dark-text shadow-sm'
              : 'text-gray-600 dark:text-dark-textSecondary hover:text-gray-900 dark:hover:text-dark-text'
          )}
          aria-pressed={format === 'detailed'}
          title="More comprehensive explanations"
        >
          Detailed
        </button>
      </div>
    </div>
  );
}

/**
 * Hook to manage response format preference
 */
export function useResponseFormat() {
  const [format, setFormat] = useState<ResponseFormat>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return (stored as ResponseFormat) || 'detailed';
  });

  const updateFormat = useCallback((newFormat: ResponseFormat) => {
    setFormat(newFormat);
    localStorage.setItem(STORAGE_KEY, newFormat);
  }, []);

  return { format, setFormat: updateFormat };
}
