/**
 * SearchInput
 *
 * Reusable debounced search input component.
 * Delays onChange calls to prevent excessive API requests.
 */

import { useState, useEffect, useRef } from "react";
import { Search, X, Loader2 } from "lucide-react";

export interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  debounceMs?: number;
  isLoading?: boolean;
}

export function SearchInput({
  value,
  onChange,
  placeholder = "Search...",
  debounceMs = 300,
  isLoading = false,
}: SearchInputProps) {
  const [localValue, setLocalValue] = useState(value);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync local value with prop value
  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalValue(newValue);

    // Clear existing timer
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    // Set new debounce timer
    debounceRef.current = setTimeout(() => {
      onChange(newValue);
    }, debounceMs);
  };

  const handleClear = () => {
    setLocalValue("");
    // Clear immediately without debounce
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    onChange("");
  };

  return (
    <div className="relative flex items-center">
      <div className="absolute left-3 pointer-events-none">
        {isLoading ? (
          <div data-testid="search-loading">
            <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
          </div>
        ) : (
          <div data-testid="search-icon">
            <Search className="w-4 h-4 text-gray-400" />
          </div>
        )}
      </div>

      <input
        type="search"
        value={localValue}
        onChange={handleChange}
        placeholder={placeholder}
        className="
          w-full pl-10 pr-8 py-2 text-sm
          border border-gray-300 dark:border-gray-600 rounded-lg
          bg-white dark:bg-gray-700
          text-gray-900 dark:text-gray-100
          placeholder-gray-400 dark:placeholder-gray-500
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
        "
      />

      {localValue && (
        <button
          onClick={handleClear}
          aria-label="Clear search"
          className="absolute right-2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default SearchInput;
