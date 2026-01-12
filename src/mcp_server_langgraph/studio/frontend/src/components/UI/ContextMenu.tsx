/**
 * ContextMenu Component
 *
 * A right-click context menu with keyboard navigation support.
 * Used for session actions, artifact actions, etc.
 */

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  cloneElement,
  isValidElement,
  type ReactNode,
  type ReactElement,
  type KeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { createPortal } from "react-dom";

import { Button } from "@/components/UI";
import { cn } from "../../utils/cn";

export interface ContextMenuItem {
  /** Unique identifier for the item */
  id: string;
  /** Display label */
  label?: string;
  /** Action to execute when clicked */
  action?: () => void;
  /** Whether the item is disabled */
  disabled?: boolean;
  /** Icon to display */
  icon?: ReactNode;
  /** Type of item (default is "item") */
  type?: "item" | "divider";
}

export interface ContextMenuProps {
  /** Menu items to display */
  items: ContextMenuItem[];
  /** The element that triggers the menu on right-click */
  children: ReactElement;
  /** Accessible label for the menu */
  "aria-label"?: string;
  /** Callback when menu opens */
  onOpen?: () => void;
  /** Callback when menu closes */
  onClose?: () => void;
}

/**
 * ContextMenu component for right-click menus
 */
export function ContextMenu({
  items,
  children,
  "aria-label": ariaLabel,
  onOpen,
  onClose,
}: ContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [focusedIndex, setFocusedIndex] = useState(0);
  const menuRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Get actionable items (non-dividers)
  const actionableItems = items.filter((item) => item.type !== "divider");

  // Handle opening the menu
  const handleContextMenu = useCallback(
    (e: ReactMouseEvent) => {
      e.preventDefault();
      setPosition({ x: e.clientX, y: e.clientY });
      setIsOpen(true);
      setFocusedIndex(0);
      onOpen?.();
    },
    [onOpen],
  );

  // Handle closing the menu
  const closeMenu = useCallback(() => {
    setIsOpen(false);
    onClose?.();
  }, [onClose]);

  // Handle item click
  const handleItemClick = useCallback(
    (item: ContextMenuItem) => {
      if (item.disabled || item.type === "divider") return;
      item.action?.();
      closeMenu();
    },
    [closeMenu],
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          e.preventDefault();
          closeMenu();
          break;
        case "ArrowDown":
          e.preventDefault();
          setFocusedIndex((prev) => (prev + 1) % actionableItems.length);
          break;
        case "ArrowUp":
          e.preventDefault();
          setFocusedIndex(
            (prev) =>
              (prev - 1 + actionableItems.length) % actionableItems.length,
          );
          break;
        case "Enter":
        case " ":
          e.preventDefault();
          if (actionableItems[focusedIndex]) {
            handleItemClick(actionableItems[focusedIndex]);
          }
          break;
        case "Tab":
          e.preventDefault();
          closeMenu();
          break;
      }
    },
    [actionableItems, focusedIndex, handleItemClick, closeMenu],
  );

  // Focus the appropriate item when focusedIndex changes
  useEffect(() => {
    if (isOpen && itemRefs.current[focusedIndex]) {
      itemRefs.current[focusedIndex]?.focus();
    }
  }, [isOpen, focusedIndex]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeMenu();
      }
    };

    // Use setTimeout to avoid closing immediately on the right-click that opened it
    const timeoutId = setTimeout(() => {
      document.addEventListener("click", handleClickOutside);
    }, 0);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener("click", handleClickOutside);
    };
  }, [isOpen, closeMenu]);

  // Close on scroll
  useEffect(() => {
    if (!isOpen) return;

    const handleScroll = () => closeMenu();
    document.addEventListener("scroll", handleScroll, true);

    return () => {
      document.removeEventListener("scroll", handleScroll, true);
    };
  }, [isOpen, closeMenu]);

  // Clone child with context menu handler
  if (!isValidElement(children)) {
    return children;
  }

  const trigger = cloneElement(children, {
    onContextMenu: handleContextMenu,
  } as React.HTMLAttributes<HTMLElement>);

  // Track which actionable item index we're at when rendering
  let actionableIndex = -1;

  return (
    <>
      {trigger}
      {isOpen &&
        createPortal(
          <div
            ref={menuRef}
            role="menu"
            aria-label={ariaLabel}
            className={cn(
              "fixed z-50 min-w-[160px] py-1 rounded-lg shadow-lg",
              "bg-white border border-neutral-200 dark:border-neutral-700",
              "dark:bg-neutral-800 dark:border-neutral-700",
              "animate-in fade-in-0 zoom-in-95 duration-100",
            )}
            style={{
              left: `${position.x}px`,
              top: `${position.y}px`,
            }}
            onKeyDown={handleKeyDown}
          >
            {items.map((item) => {
              if (item.type === "divider") {
                return (
                  <div
                    key={item.id}
                    role="separator"
                    className="my-1 border-t border-neutral-200 dark:border-neutral-700"
                  />
                );
              }

              // Increment actionable index for non-dividers
              actionableIndex++;
              const currentActionableIndex = actionableIndex;

              return (
                <Button
                  key={item.id}
                  ref={(el) => {
                    itemRefs.current[currentActionableIndex] = el;
                  }}
                  role="menuitem"
                  aria-disabled={item.disabled}
                  disabled={item.disabled}
                  onClick={() => handleItemClick(item)}
                  className={cn(
                    "w-full px-3 py-2 text-left text-sm flex items-center gap-2",
                    "focus:outline-none focus:bg-neutral-100 dark:bg-neutral-800 dark:focus:bg-neutral-700",
                    "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
                    item.disabled
                      ? "text-neutral-400 dark:text-neutral-400 cursor-not-allowed"
                      : "text-neutral-700 dark:text-neutral-200",
                  )}
                >
                  {item.icon && (
                    <span className="shrink-0 w-4 h-4" aria-hidden="true">
                      {item.icon}
                    </span>
                  )}
                  {item.label}
                </Button>
              );
            })}
          </div>,
          document.body,
        )}
    </>
  );
}

ContextMenu.displayName = "ContextMenu";
