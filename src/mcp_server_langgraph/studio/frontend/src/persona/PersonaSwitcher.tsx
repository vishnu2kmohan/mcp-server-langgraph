/**
 * PersonaSwitcher - Phase 2
 *
 * Persona and sub-persona selection component with
 * dropdown, grouping, and keyboard navigation.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import {
  ChevronDown,
  Shield,
  Code,
  User,
  BarChart,
  ClipboardCheck,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface Persona {
  id: string;
  name: string;
  role: "admin" | "developer" | "user";
  description: string;
  icon: string;
  color: string;
  parentId?: string;
}

export interface PersonaSwitcherProps {
  personas: Persona[];
  currentPersona: Persona;
  onSwitch: (persona: Persona) => void;
  groupByRole?: boolean;
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

// Icon mapping - using LucideIcon type for proper compatibility
const iconMap: Record<string, LucideIcon> = {
  shield: Shield,
  "shield-alert": ShieldAlert,
  "clipboard-check": ClipboardCheck,
  code: Code,
  "bar-chart": BarChart,
  user: User,
};

function getIcon(iconName: string) {
  return iconMap[iconName] || User;
}

// =============================================================================
// Component
// =============================================================================

export function PersonaSwitcher({
  personas,
  currentPersona,
  onSwitch,
  groupByRole = false,
  className,
}: PersonaSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Check which personas have children
  const personasWithChildren = useMemo(() => {
    const parentIds = new Set(
      personas.filter((p) => p.parentId).map((p) => p.parentId),
    );
    return parentIds;
  }, [personas]);

  // Group personas by role if needed
  const groupedPersonas = useMemo(() => {
    if (!groupByRole) return null;

    const groups: Record<string, Persona[]> = {
      admin: [],
      developer: [],
      user: [],
    };

    personas.forEach((persona) => {
      const group = groups[persona.role];
      if (group) {
        group.push(persona);
      }
    });

    return groups;
  }, [personas, groupByRole]);

  // Handle click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const handleSelect = useCallback(
    (persona: Persona) => {
      onSwitch(persona);
      setIsOpen(false);
    },
    [onSwitch],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.min(prev + 1, personas.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setFocusedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && focusedIndex >= 0) {
        e.preventDefault();
        const focusedPersona = personas[focusedIndex];
        if (focusedPersona) {
          handleSelect(focusedPersona);
        }
      }
    },
    [personas, focusedIndex, handleSelect],
  );

  const CurrentIcon = getIcon(currentPersona.icon);

  const renderPersonaItem = (persona: Persona, index: number) => {
    const isSelected = persona.id === currentPersona.id;
    const isFocused = index === focusedIndex;
    const hasChildren = personasWithChildren.has(persona.id);
    const isSubPersona = !!persona.parentId;
    const PersonaIcon = getIcon(persona.icon);

    return (
      <div
        key={persona.id}
        data-testid={`persona-item-${persona.id}`}
        data-has-children={hasChildren ? "true" : "false"}
        role="option"
        aria-selected={isSelected}
        tabIndex={-1}
        onClick={() => handleSelect(persona)}
        className={cn(
          "flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors",
          "hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700",
          isSelected && "selected bg-primary-50 dark:bg-primary-900/20",
          isFocused && "focused bg-gray-100 dark:bg-gray-700",
          isSubPersona && "sub-persona pl-8",
        )}
      >
        <PersonaIcon size={16} className="text-gray-500 dark:text-gray-400" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {persona.name}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
            {persona.description}
          </div>
        </div>
        {isSelected && <div className="w-2 h-2 rounded-full bg-primary-500" />}
      </div>
    );
  };

  return (
    <div
      data-testid="persona-switcher"
      ref={containerRef}
      className={cn("relative", className)}
    >
      {/* Trigger Button */}
      <button
        data-testid="persona-trigger"
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-lg",
          "bg-gray-100 dark:bg-gray-800",
          "hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-700",
          "transition-colors",
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <CurrentIcon size={16} className="text-gray-500 dark:text-gray-400" />
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {currentPersona.name}
        </span>
        <ChevronDown
          size={14}
          className={cn(
            "text-gray-400 dark:text-gray-400 transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div
          data-testid="persona-dropdown"
          ref={dropdownRef}
          role="listbox"
          tabIndex={0}
          onKeyDown={handleKeyDown}
          className={cn(
            "absolute top-full left-0 mt-1 w-64 z-50",
            "bg-white dark:bg-gray-800",
            "border border-gray-200 dark:border-gray-700",
            "rounded-lg shadow-lg",
            "max-h-80 overflow-y-auto",
          )}
        >
          {groupByRole && groupedPersonas
            ? Object.entries(groupedPersonas).map(
                ([role, rolePersonas]) =>
                  rolePersonas.length > 0 && (
                    <div key={role} data-testid={`role-group-${role}`}>
                      <div className="px-3 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase bg-gray-50 dark:bg-gray-900/50">
                        {role}
                      </div>
                      {rolePersonas.map((persona) =>
                        renderPersonaItem(
                          persona,
                          personas.findIndex((p) => p.id === persona.id),
                        ),
                      )}
                    </div>
                  ),
              )
            : personas.map((persona, index) =>
                renderPersonaItem(persona, index),
              )}
        </div>
      )}
    </div>
  );
}
