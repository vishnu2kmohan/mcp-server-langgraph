/**
 * SearchInput
 *
 * Reusable debounced search input component.
 * Delays onChange calls to prevent excessive API requests.
 */

import { useState, useEffect, useRef } from "react";
import { Search, X, Loader2 } from "lucide-react";

import { Button } from "@/components/UI";

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
            <Loader2 className="w-4 h-4 animate-spin text-neutral-400 dark:text-neutral-400" />
          </div>
        ) : (
          <div data-testid="search-icon">
            <Search className="w-4 h-4 text-neutral-400 dark:text-neutral-400" />
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
          border border-neutral-300 dark:border-neutral-600 rounded-lg
          bg-white dark:bg-neutral-700
          text-neutral-900 dark:text-neutral-100
          placeholder-neutral-400 dark:placeholder-neutral-500
          focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent
        "
      />
      {localValue && (
        <Button
          className="absolute right-2 p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300"
          onClick={handleClear}
          aria-label="Clear search"
        >
          <X className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}

export default SearchInput;
