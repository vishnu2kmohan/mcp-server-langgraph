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

import { Button } from "@/components/UI";

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
          "hover:bg-neutral-2",
          isSelected && "selected bg-primary-1 dark:bg-primary-a3",
          isFocused && "focused bg-neutral-2",
          isSubPersona && "sub-persona pl-8",
        )}
      >
        <PersonaIcon size={16} className="text-neutral-10" />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-neutral-12">
            {persona.name}
          </div>
          <div className="text-xs text-neutral-10 truncate">
            {persona.description}
          </div>
        </div>
        {isSelected && <div className="w-2 h-2 rounded-full bg-primary-9" />}
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
      <Button
        variant="ghost"
        data-testid="persona-trigger"
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-lg",
          "bg-neutral-2",
          "hover:bg-neutral-3",
          "transition-colors",
        )}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <CurrentIcon size={16} className="text-neutral-10" />
        <span className="text-sm font-medium text-neutral-12">
          {currentPersona.name}
        </span>
        <ChevronDown
          size={14}
          className={cn(
            "text-neutral-9 transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </Button>
      {/* Dropdown */}
      {isOpen && (
        <div
          data-testid="persona-dropdown"
          ref={dropdownRef}
          role="listbox"
          tabIndex={0}
          onKeyDown={handleKeyDown}
          className={cn(
            "absolute top-full left-0 mt-1 w-64 z-dropdown",
            "bg-neutral-1",
            "border border-neutral-5",
            "rounded-lg shadow-lg",
            "max-h-80 overflow-y-auto",
          )}
        >
          {groupByRole && groupedPersonas
            ? Object.entries(groupedPersonas).map(
                ([role, rolePersonas]) =>
                  rolePersonas.length > 0 && (
                    <div key={role} data-testid={`role-group-${role}`}>
                      <div className="px-3 py-1 text-xs font-semibold text-neutral-10 uppercase bg-neutral-1">
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
