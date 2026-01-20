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
import { useReducedMotion } from "motion/react";
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
    // WCAG 2.2 AA: Respect user's reduced motion preference
    const prefersReducedMotion = useReducedMotion();

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
          "p-2 rounded-lg",
          !prefersReducedMotion && "transition-colors",
          "text-neutral-11",
          "hover:bg-neutral-2",
          "focus:outline-none focus:ring-2 focus:ring-primary-7",
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
