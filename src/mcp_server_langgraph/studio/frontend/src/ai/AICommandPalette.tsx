/**
 * AICommandPalette - Phase 2
 *
 * AI-enhanced command palette with natural language interpretation.
 */
import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Search, Sparkles, Command as CommandIcon } from "lucide-react";
import { cn } from "../utils/cn";

import { Input } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface Command {
  id: string;
  name: string;
  description: string;
  shortcut?: string;
  category?: string;
  icon?: string;
}

export interface AIInterpretation {
  action: string;
  params: Record<string, unknown>;
  confidence: number;
}

export interface AICommandPaletteProps {
  commands: Command[];
  isOpen: boolean;
  onClose: () => void;
  onExecute: (command: Command | AIInterpretation) => void;
  onAIInterpret?: (query: string) => Promise<AIInterpretation>;
  groupByCategory?: boolean;
  placeholder?: string;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function AICommandPalette({
  commands,
  isOpen,
  onClose,
  onExecute,
  onAIInterpret,
  groupByCategory = false,
  placeholder = "Type a command or ask AI...",
  className,
}: AICommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [aiSuggestion, setAISuggestion] = useState<AIInterpretation | null>(
    null,
  );
  const [isLoadingAI, setIsLoadingAI] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Reset state when closed
  useEffect(() => {
    if (!isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setAISuggestion(null);
    }
  }, [isOpen]);

  // Filter commands based on query
  const filteredCommands = useMemo(() => {
    if (!query) return commands;
    const lowerQuery = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.name.toLowerCase().includes(lowerQuery) ||
        cmd.description.toLowerCase().includes(lowerQuery),
    );
  }, [commands, query]);

  // Group commands by category
  const groupedCommands = useMemo(() => {
    if (!groupByCategory) return null;

    const groups: Record<string, Command[]> = {};
    filteredCommands.forEach((cmd) => {
      const category = cmd.category || "other";
      if (!groups[category]) groups[category] = [];
      groups[category].push(cmd);
    });
    return groups;
  }, [filteredCommands, groupByCategory]);

  // AI interpretation when no static matches
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.length > 10 && filteredCommands.length === 0 && onAIInterpret) {
      debounceRef.current = setTimeout(async () => {
        setIsLoadingAI(true);
        try {
          const result = await onAIInterpret(query);
          setAISuggestion(result);
        } catch {
          setAISuggestion(null);
        } finally {
          setIsLoadingAI(false);
        }
      }, 500);
    } else {
      setAISuggestion(null);
    }

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query, filteredCommands.length, onAIInterpret]);

  const handleExecute = useCallback(
    (item: Command | AIInterpretation) => {
      onExecute(item);
      onClose();
    },
    [onExecute, onClose],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }

      const totalItems = filteredCommands.length + (aiSuggestion ? 1 : 0);

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, totalItems - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const selectedCommand = filteredCommands[selectedIndex];
        if (selectedIndex < filteredCommands.length && selectedCommand) {
          handleExecute(selectedCommand);
        } else if (aiSuggestion) {
          handleExecute(aiSuggestion);
        }
      }
    },
    [filteredCommands, aiSuggestion, selectedIndex, onClose, handleExecute],
  );

  if (!isOpen) return null;

  return (
    <div
      data-testid="ai-command-palette"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      className={cn(
        "fixed inset-0 z-modal flex items-start justify-center pt-[20vh]",
        "bg-neutral-a6",
        className,
      )}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="w-full max-w-xl bg-neutral-1 rounded-xl shadow-2xl overflow-hidden">
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-neutral-5">
          <Search size={18} className="text-neutral-9" />
          <Input
            className="flex-1 bg-transparent text-neutral-12 placeholder-neutral-9"
            ref={inputRef}
            data-testid="command-search"
            role="combobox"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            aria-autocomplete="list"
            aria-expanded="true"
            aria-controls="command-listbox"
          />
          {isLoadingAI && (
            <Sparkles size={18} className="text-primary-9 animate-pulse" />
          )}
        </div>

        {/* Command List */}
        <div
          id="command-listbox"
          role="listbox"
          className="max-h-80 overflow-y-auto"
        >
          {filteredCommands.length === 0 && !aiSuggestion && !isLoadingAI && (
            <div
              data-testid="no-results"
              className="p-4 text-center text-neutral-10"
            >
              No commands found
            </div>
          )}

          {groupByCategory && groupedCommands
            ? Object.entries(groupedCommands).map(([category, cmds]) => (
                <div key={category} data-testid={`category-${category}`}>
                  <div className="px-4 py-1 text-xs font-semibold text-neutral-10 uppercase bg-neutral-1">
                    {category}
                  </div>
                  {cmds.map((cmd, _index) => {
                    const globalIndex = filteredCommands.indexOf(cmd);
                    return (
                      <div
                        key={cmd.id}
                        data-testid="command-item"
                        role="option"
                        aria-selected={globalIndex === selectedIndex}
                        onClick={() => handleExecute(cmd)}
                        className={cn(
                          "flex items-center justify-between px-4 py-2 cursor-pointer",
                          "hover:bg-neutral-2",
                          globalIndex === selectedIndex &&
                            "selected bg-neutral-2",
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <CommandIcon size={16} className="text-neutral-9" />
                          <div>
                            <div className="text-sm font-medium text-neutral-12">
                              {cmd.name}
                            </div>
                            <div className="text-xs text-neutral-10">
                              {cmd.description}
                            </div>
                          </div>
                        </div>
                        {cmd.shortcut && (
                          <kbd className="px-2 py-0.5 text-xs bg-neutral-2 rounded">
                            {cmd.shortcut}
                          </kbd>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))
            : filteredCommands.map((cmd, index) => (
                <div
                  key={cmd.id}
                  data-testid="command-item"
                  role="option"
                  aria-selected={index === selectedIndex}
                  onClick={() => handleExecute(cmd)}
                  className={cn(
                    "flex items-center justify-between px-4 py-2 cursor-pointer",
                    "hover:bg-neutral-2",
                    index === selectedIndex && "selected bg-neutral-2",
                  )}
                >
                  <div className="flex items-center gap-3">
                    <CommandIcon size={16} className="text-neutral-9" />
                    <div>
                      <div className="text-sm font-medium text-neutral-12">
                        {cmd.name}
                      </div>
                      <div className="text-xs text-neutral-10">
                        {cmd.description}
                      </div>
                    </div>
                  </div>
                  {cmd.shortcut && (
                    <kbd className="px-2 py-0.5 text-xs bg-neutral-2 rounded">
                      {cmd.shortcut}
                    </kbd>
                  )}
                </div>
              ))}

          {/* AI Suggestion */}
          {aiSuggestion && (
            <div
              data-testid="ai-suggestion"
              role="option"
              aria-selected={selectedIndex >= filteredCommands.length}
              onClick={() => handleExecute(aiSuggestion)}
              className={cn(
                "flex items-center gap-3 px-4 py-2 cursor-pointer",
                "hover:bg-primary-1 dark:hover:bg-primary-a3",
                "border-t border-neutral-5",
                selectedIndex >= filteredCommands.length &&
                  "bg-primary-1 dark:bg-primary-a3",
              )}
            >
              <Sparkles size={16} className="text-primary-9" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-neutral-12">
                    {aiSuggestion.action}
                  </span>
                  <span
                    data-testid="ai-badge"
                    className="px-1.5 py-0.5 text-xs bg-primary-3 bg-primary-4 text-primary-10 dark:text-primary-7 rounded"
                  >
                    AI
                  </span>
                </div>
                <div className="text-xs text-neutral-10">
                  Confidence: {Math.round(aiSuggestion.confidence * 100)}%
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
