/**
 * SelectionCard Component
 *
 * A reusable selection card component that provides consistent styling
 * across wizard steps, template selectors, and option lists.
 *
 * Ensures visual consistency with:
 * - Consistent padding (p-4)
 * - Consistent gap (gap-3)
 * - Consistent border width (border-2)
 * - Consistent icon container sizing (w-10 h-10)
 * - Proper selected/unselected state styling
 */

import { ReactNode } from "react";

export interface SelectionCardProps<T = void> {
  /** Card title */
  title: string;
  /** Optional description text */
  description?: string;
  /** Icon element to display */
  icon: ReactNode;
  /** Whether the card is currently selected */
  selected?: boolean;
  /** Click handler */
  onClick: T extends void ? () => void : (value: T) => void;
  /** Optional value passed to onClick */
  value?: T;
  /** Optional badge text (e.g., "Recommended", "AI Pick") */
  badge?: string;
  /** Optional aria-label override */
  ariaLabel?: string;
  /** Optional additional className */
  className?: string;
}

export function SelectionCard<T = void>({
  title,
  description,
  icon,
  selected = false,
  onClick,
  value,
  badge,
  ariaLabel,
  className = "",
}: SelectionCardProps<T>) {
  const handleClick = () => {
    if (value !== undefined) {
      (onClick as (value: T) => void)(value);
    } else {
      (onClick as () => void)();
    }
  };

  return (
    <button
      type="button"
      className={`w-full flex items-start gap-3 p-4 text-left rounded-lg border-2 transition-colors ${
        selected
          ? "border-primary-7 bg-primary-3"
          : "border-neutral-6 bg-neutral-3 hover:border-neutral-7"
      } ${className}`}
      onClick={handleClick}
      aria-label={ariaLabel}
      aria-pressed={selected}
    >
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
          selected
            ? "bg-primary-4 text-primary-11"
            : "bg-neutral-4 text-neutral-11"
        }`}
      >
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-neutral-12">{title}</h3>
          {badge && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-insight-11 bg-insight-3 rounded-full">
              {badge}
            </span>
          )}
        </div>
        {description && (
          <p className="text-sm text-neutral-11 mt-1">{description}</p>
        )}
      </div>
    </button>
  );
}

export default SelectionCard;
