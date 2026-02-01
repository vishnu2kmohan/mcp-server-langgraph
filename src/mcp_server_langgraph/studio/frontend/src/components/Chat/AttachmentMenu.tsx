/**
 * AttachmentMenu Component
 *
 * Slack-style plus (+) menu for the chat input form.
 * Provides access to:
 * - File upload
 * - Knowledge Base Focus mode selection
 * - Code snippet insertion
 * - Mention insertion
 *
 * Features:
 * - Plus icon button that opens a dropdown menu
 * - KB Focus submenu with All/KB Only/Web Only/None options
 * - Keyboard navigation (Arrow keys, Enter, Escape)
 * - WCAG 2.1 AA accessibility compliance
 */

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import {
  Plus,
  Paperclip,
  Search,
  Database,
  Globe,
  Ban,
  Code,
  AtSign,
  ChevronRight,
  Check,
} from "lucide-react";
import { cn } from "../../utils/cn";
import type { KBFocusMode, KBStatus } from "./KnowledgeBaseFocus";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface AttachmentMenuProps {
  /** Callback when files are selected */
  onFileSelect: (files: File[]) => void;
  /** Whether files are currently being uploaded */
  isUploading?: boolean;
  /** Whether to show Knowledge Base Focus option */
  showKBFocus?: boolean;
  /** Current KB Focus mode */
  kbFocusValue?: KBFocusMode;
  /** Callback when KB Focus mode changes */
  onKBFocusChange?: (mode: KBFocusMode) => void;
  /** KB status for indicator */
  kbStatus?: KBStatus;
  /** Callback to insert a code block */
  onInsertCodeBlock?: () => void;
  /** Callback to insert a mention */
  onInsertMention?: () => void;
  /** Whether the menu is disabled */
  disabled?: boolean;
}

interface MenuItem {
  id: string;
  label: string;
  icon: React.ElementType;
  action?: () => void;
  hasSubmenu?: boolean;
}

interface KBFocusOption {
  value: KBFocusMode;
  label: string;
  icon: React.ElementType;
}

// =============================================================================
// Constants
// =============================================================================

const KB_FOCUS_OPTIONS: KBFocusOption[] = [
  { value: "all", label: "All Sources", icon: Search },
  { value: "kb_only", label: "Knowledge Base Only", icon: Database },
  { value: "web_only", label: "Web Only", icon: Globe },
  { value: "none", label: "No Search", icon: Ban },
];

// =============================================================================
// Component
// =============================================================================

export function AttachmentMenu({
  onFileSelect,
  isUploading = false,
  showKBFocus = false,
  kbFocusValue = "all",
  onKBFocusChange,
  kbStatus: _kbStatus, // Reserved for future KB status indicator styling
  onInsertCodeBlock,
  onInsertMention,
  disabled = false,
}: AttachmentMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showKBSubmenu, setShowKBSubmenu] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [focusedKBIndex, setFocusedKBIndex] = useState(0);

  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const menuItemsRef = useRef<(HTMLButtonElement | null)[]>([]);

  // Build menu items based on props - memoized to prevent dependency array issues
  const menuItems: MenuItem[] = useMemo(
    () => [
      {
        id: "upload",
        label: "Upload file",
        icon: Paperclip,
        action: () => fileInputRef.current?.click(),
      },
      ...(showKBFocus
        ? [
            {
              id: "kb-focus",
              label: "Knowledge Base Focus",
              icon: Search,
              hasSubmenu: true,
            },
          ]
        : []),
      {
        id: "code",
        label: "Code snippet",
        icon: Code,
        action: onInsertCodeBlock,
      },
      {
        id: "mention",
        label: "Mention",
        icon: AtSign,
        action: onInsertMention,
      },
    ],
    [showKBFocus, onInsertCodeBlock, onInsertMention],
  );

  // Close menu on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
        setShowKBSubmenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (showKBSubmenu) {
          setShowKBSubmenu(false);
        } else {
          setIsOpen(false);
          buttonRef.current?.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, showKBSubmenu]);

  // Focus first item when menu opens
  useEffect(() => {
    if (isOpen && menuItemsRef.current[0]) {
      menuItemsRef.current[0].focus();
      setFocusedIndex(0);
    }
  }, [isOpen]);

  // Handle file input change
  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const files = event.target.files;
      if (files && files.length > 0) {
        onFileSelect(Array.from(files));
        setIsOpen(false);
      }
      // Reset input to allow selecting the same file again
      event.target.value = "";
    },
    [onFileSelect],
  );

  // Handle menu item click
  const handleMenuItemClick = useCallback(
    (item: MenuItem, _index: number) => {
      if (item.hasSubmenu) {
        setShowKBSubmenu(true);
        setFocusedKBIndex(
          KB_FOCUS_OPTIONS.findIndex((opt) => opt.value === kbFocusValue),
        );
      } else if (item.action) {
        item.action();
        setIsOpen(false);
        setShowKBSubmenu(false);
      }
    },
    [kbFocusValue],
  );

  // Handle KB Focus option click
  const handleKBFocusSelect = useCallback(
    (mode: KBFocusMode) => {
      onKBFocusChange?.(mode);
      setIsOpen(false);
      setShowKBSubmenu(false);
    },
    [onKBFocusChange],
  );

  // Handle keyboard navigation in main menu
  const handleMenuKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          setFocusedIndex((prev) => {
            const next = (prev + 1) % menuItems.length;
            menuItemsRef.current[next]?.focus();
            return next;
          });
          break;
        case "ArrowUp":
          event.preventDefault();
          setFocusedIndex((prev) => {
            const next = prev <= 0 ? menuItems.length - 1 : prev - 1;
            menuItemsRef.current[next]?.focus();
            return next;
          });
          break;
        case "ArrowRight":
          if (menuItems[focusedIndex]?.hasSubmenu) {
            event.preventDefault();
            setShowKBSubmenu(true);
            setFocusedKBIndex(0);
          }
          break;
        case "Enter":
        case " ":
          event.preventDefault();
          handleMenuItemClick(menuItems[focusedIndex], focusedIndex);
          break;
      }
    },
    [focusedIndex, menuItems, handleMenuItemClick],
  );

  // Handle keyboard navigation in KB submenu
  const handleKBSubmenuKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          setFocusedKBIndex((prev) => (prev + 1) % KB_FOCUS_OPTIONS.length);
          break;
        case "ArrowUp":
          event.preventDefault();
          setFocusedKBIndex((prev) =>
            prev <= 0 ? KB_FOCUS_OPTIONS.length - 1 : prev - 1,
          );
          break;
        case "ArrowLeft":
          event.preventDefault();
          setShowKBSubmenu(false);
          menuItemsRef.current[focusedIndex]?.focus();
          break;
        case "Enter":
        case " ":
          event.preventDefault();
          handleKBFocusSelect(KB_FOCUS_OPTIONS[focusedKBIndex].value);
          break;
      }
    },
    [focusedIndex, focusedKBIndex, handleKBFocusSelect],
  );

  const toggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev);
    if (isOpen) {
      setShowKBSubmenu(false);
    }
  }, [isOpen]);

  return (
    <div className="relative">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileChange}
        className="sr-only"
        aria-hidden="true"
        data-testid="attachment-file-input"
      />
      {/* Plus button trigger */}
      <Button
        size="icon"
        ref={buttonRef}
        variant="ghost"
        type="button"
        disabled={disabled || isUploading}
        onClick={toggleMenu}
        aria-label="Add attachment or action"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        data-testid="attachment-menu-button"
        className={cn(
          "p-2 rounded-full",
          "text-neutral-10 hover:text-neutral-11",

          "hover:bg-neutral-4",
          "transition-colors",
        )}
      >
        <Plus className="w-5 h-5" />
      </Button>
      {/* Dropdown menu */}
      {isOpen && (
        <div
          ref={menuRef}
          role="menu"
          aria-label="Attachment and actions menu"
          data-testid="attachment-menu"
          className={cn(
            "absolute bottom-full left-0 mb-2",
            "w-56 py-1",
            "bg-neutral-2",
            "border border-neutral-6",
            "rounded-lg shadow-lg",
            "z-dropdown",
          )}
          onKeyDown={showKBSubmenu ? handleKBSubmenuKeyDown : handleMenuKeyDown}
        >
          {menuItems.map((item, index) => {
            const Icon = item.icon;
            return (
              <Button
                variant="ghost"
                key={item.id}
                ref={(el) => {
                  menuItemsRef.current[index] = el;
                }}
                role="menuitem"
                data-testid={`menu-item-${item.id}`}
                onClick={() => handleMenuItemClick(item, index)}
                onMouseEnter={() => {
                  setFocusedIndex(index);
                  if (item.hasSubmenu) {
                    setShowKBSubmenu(true);
                  } else {
                    setShowKBSubmenu(false);
                  }
                }}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2",
                  "text-sm text-left",
                  "text-neutral-11",
                  "hover:bg-neutral-4",
                  "focus:bg-neutral-2",
                  "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-inset",
                  "transition-colors",
                )}
              >
                <Icon className="w-4 h-4 text-neutral-10" />
                <span className="flex-1">{item.label}</span>
                {item.hasSubmenu && (
                  <ChevronRight className="w-4 h-4 text-neutral-9" />
                )}
              </Button>
            );
          })}

          {/* KB Focus Submenu */}
          {showKBSubmenu && showKBFocus && (
            <div
              role="menu"
              aria-label="Knowledge Base Focus options"
              data-testid="kb-focus-submenu"
              className={cn(
                "absolute left-full top-0 ml-1",
                "w-52 py-1",
                "bg-neutral-2",
                "border border-neutral-6",
                "rounded-lg shadow-lg",
              )}
            >
              {KB_FOCUS_OPTIONS.map((option, index) => {
                const Icon = option.icon;
                const isSelected = kbFocusValue === option.value;
                return (
                  <Button
                    variant="ghost"
                    key={option.value}
                    role="menuitem"
                    onClick={() => handleKBFocusSelect(option.value)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2",
                      "text-sm text-left",
                      "text-neutral-11",
                      "hover:bg-neutral-4",
                      focusedKBIndex === index && "bg-neutral-4",
                      "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-9 focus-visible:ring-inset",
                      "transition-colors",
                    )}
                  >
                    <Icon className="w-4 h-4 text-neutral-10" />
                    <span className="flex-1">{option.label}</span>
                    {isSelected && (
                      <Check
                        className="w-4 h-4 text-primary-9"
                        data-testid={`kb-focus-check-${option.value}`}
                      />
                    )}
                  </Button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AttachmentMenu;
