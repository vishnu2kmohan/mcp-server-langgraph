/**
 * ScopeSelector Component
 *
 * A radio group for selecting connection scope (user/project/session).
 * Uses the design system RadioGroup with card variant.
 *
 * @see ADR-0102 Phase 6
 */

import { RadioGroup, Radio } from "../UI/RadioGroup";
import type { ConnectionScope } from "@/types/connection";

/**
 * Configuration for each scope option
 */
const SCOPE_OPTIONS: Array<{
  value: ConnectionScope;
  label: string;
  description: string;
}> = [
  {
    value: "user",
    label: "Personal",
    description: "Only you can access this connection",
  },
  {
    value: "project",
    label: "Project",
    description: "All project members can access this connection",
  },
  {
    value: "session",
    label: "Session Only",
    description: "Temporary, not saved after session ends",
  },
];

export interface ScopeSelectorProps {
  /** Currently selected scope */
  value: ConnectionScope;
  /** Called when selection changes */
  onChange: (scope: ConnectionScope) => void;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * ScopeSelector - RadioGroup for connection scope selection
 *
 * Provides three options for connection access control:
 * - Personal (user): Only accessible by owner
 * - Project: Accessible by all project members
 * - Session Only: Ephemeral, current session only
 */
export function ScopeSelector({
  value,
  onChange,
  disabled = false,
  className,
}: ScopeSelectorProps) {
  return (
    <div data-testid="scope-selector" className={className}>
      <RadioGroup
        name="connection-scope"
        value={value}
        onChange={(newValue) => onChange(newValue as ConnectionScope)}
        disabled={disabled}
        variant="card"
        aria-label="Connection scope"
      >
        {SCOPE_OPTIONS.map((option) => (
          <Radio
            key={option.value}
            value={option.value}
            label={option.label}
            description={option.description}
          />
        ))}
      </RadioGroup>
    </div>
  );
}
