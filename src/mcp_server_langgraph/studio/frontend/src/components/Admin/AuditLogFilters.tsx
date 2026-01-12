/**
 * AuditLogFilters Component
 *
 * Filter controls for audit log search and export.
 * Includes date range picker, action type filter, user search, and CSV export.
 */

import { useState, useCallback, ChangeEvent } from "react";
import { Download, RotateCcw, Search } from "lucide-react";

import { Button, Input, Select } from "@/components/UI";

export interface DateRange {
  startDate: string;
  endDate: string;
}

export type ActionType =
  | "all"
  | "user_created"
  | "user_updated"
  | "user_deleted"
  | "role_changed"
  | "login"
  | "logout";

export interface AuditLogFiltersProps {
  /** Called when date range changes */
  onDateRangeChange: (range: DateRange) => void;
  /** Called when action type filter changes */
  onActionTypeChange: (actionType: ActionType) => void;
  /** Called when user search input changes */
  onUserSearch: (query: string) => void;
  /** Called when export button is clicked */
  onExport: () => void;
  /** Called when reset button is clicked */
  onReset?: () => void;
}

const ACTION_TYPES: { value: ActionType; label: string }[] = [
  { value: "all", label: "All Actions" },
  { value: "user_created", label: "User Created" },
  { value: "user_updated", label: "User Updated" },
  { value: "user_deleted", label: "User Deleted" },
  { value: "role_changed", label: "Role Changed" },
  { value: "login", label: "Login" },
  { value: "logout", label: "Logout" },
];

/**
 * AuditLogFilters component for filtering and exporting audit logs.
 *
 * @example
 * ```tsx
 * <AuditLogFilters
 *   onDateRangeChange={(range) => setDateRange(range)}
 *   onActionTypeChange={(type) => setActionType(type)}
 *   onUserSearch={(query) => setUserQuery(query)}
 *   onExport={() => downloadCSV()}
 *   onReset={() => resetFilters()}
 * />
 * ```
 */
export function AuditLogFilters({
  onDateRangeChange,
  onActionTypeChange,
  onUserSearch,
  onExport,
  onReset,
}: AuditLogFiltersProps) {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [actionType, setActionType] = useState<ActionType>("all");
  const [userQuery, setUserQuery] = useState("");

  const handleStartDateChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setStartDate(value);
      onDateRangeChange({ startDate: value, endDate });
    },
    [endDate, onDateRangeChange],
  );

  const handleEndDateChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setEndDate(value);
      onDateRangeChange({ startDate, endDate: value });
    },
    [startDate, onDateRangeChange],
  );

  const handleActionTypeChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value as ActionType;
      setActionType(value);
      onActionTypeChange(value);
    },
    [onActionTypeChange],
  );

  const handleUserSearchChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setUserQuery(value);
      onUserSearch(value);
    },
    [onUserSearch],
  );

  const handleReset = useCallback(() => {
    setStartDate("");
    setEndDate("");
    setActionType("all");
    setUserQuery("");
    onReset?.();
  }, [onReset]);

  return (
    <div className="flex flex-wrap gap-4 items-end p-4 bg-white dark:bg-neutral-800 rounded-lg shadow">
      {/* Date Range */}
      <div className="flex gap-2">
        <div>
          <label
            htmlFor="start-date"
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            Start Date
          </label>
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-white text-sm"
            type="date"
            id="start-date"
            value={startDate}
            onChange={handleStartDateChange}
          />
        </div>
        <div>
          <label
            htmlFor="end-date"
            className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
          >
            End Date
          </label>
          <Input
            className="px-3 py-2 text-neutral-900 dark:text-white text-sm"
            type="date"
            id="end-date"
            value={endDate}
            onChange={handleEndDateChange}
          />
        </div>
      </div>
      {/* Action Type */}
      <div>
        <label
          htmlFor="action-type"
          className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
        >
          Action Type
        </label>
        <Select
          className="px-3 py-2 text-neutral-900 dark:text-white text-sm min-w-[150px]"
          id="action-type"
          value={actionType}
          onChange={handleActionTypeChange}
        >
          {ACTION_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </Select>
      </div>
      {/* User Search */}
      <div className="flex-1 min-w-[200px]">
        <label
          htmlFor="user-search"
          className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
        >
          User
        </label>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 dark:text-neutral-400" />
          <Input
            className="pl-9 pr-3 py-2 text-neutral-900 dark:text-white text-sm"
            id="user-search"
            value={userQuery}
            onChange={handleUserSearchChange}
            placeholder="Search user..."
          />
        </div>
      </div>
      {/* Action Buttons */}
      <div className="flex gap-2">
        <Button
          variant="secondary"
          className="flex px-3 py-2 text-sm text-neutral-600 dark:text-neutral-300 bg-neutral-100 dark:bg-neutral-700 rounded-md hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600"
          onClick={handleReset}
          aria-label="Reset filters"
        >
          <RotateCcw className="w-4 h-4" />
          Reset
        </Button>
        <Button
          variant="primary"
          className="flex px-3 py-2 text-sm text-white bg-primary-600 rounded-md hover:bg-primary-700"
          onClick={onExport}
          aria-label="Export CSV"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </Button>
      </div>
    </div>
  );
}

export default AuditLogFilters;
