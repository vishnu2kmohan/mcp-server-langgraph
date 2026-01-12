/**
 * HamburgerMenu Component (Sprint 5.1)
 *
 * A hamburger menu button for mobile navigation.
 * Toggles between hamburger and close icons based on drawer state.
 *
 * Accessibility:
 * - aria-expanded reflects drawer state
 * - aria-controls references the drawer
 * - aria-label provides context
 */
import { forwardRef } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

export interface HamburgerMenuProps {
  /** Click handler to toggle drawer */
  onClick: () => void;
  /** Whether the drawer is open */
  isOpen?: boolean;
  /** Additional class names */
  className?: string;
}

export const HamburgerMenu = forwardRef<HTMLButtonElement, HamburgerMenuProps>(
  function HamburgerMenu({ onClick, isOpen = false, className }, ref) {
    return (
      <Button
        ref={ref}
        type="button"
        data-testid="hamburger-menu"
        onClick={onClick}
        aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
        aria-expanded={isOpen}
        aria-controls="mobile-drawer"
        className={cn(
          "p-2 rounded-lg transition-colors",
          "text-neutral-600 dark:text-neutral-300",
          "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
          "focus:outline-none focus:ring-2 focus:ring-primary-500",
          className,
        )}
      >
        {isOpen ? (
          <X size={24} data-testid="hamburger-close-icon" />
        ) : (
          <Menu size={24} data-testid="hamburger-icon" />
        )}
      </Button>
    );
  },
);

HamburgerMenu.displayName = "HamburgerMenu";
