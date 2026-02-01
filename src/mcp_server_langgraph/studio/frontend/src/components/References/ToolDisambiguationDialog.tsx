/**
 * ToolDisambiguationDialog Component
 *
 * Displays when multiple connections provide the same tool.
 * Allows user to select which connection to use for the reference.
 *
 * WCAG 2.2 AA compliant with proper dialog and radiogroup patterns.
 */

import { useState, useCallback, useEffect, useId } from "react";
import { Server, Check, AlertCircle, Wrench } from "lucide-react";
import { Button, Checkbox } from "@/components/UI";
import { cn } from "@/utils/cn";

export interface AmbiguousConnection {
  /** Unique connection ID */
  connectionId: string;
  /** Server name (will be same for all in list) */
  serverName: string;
  /** User-friendly display name */
  displayName: string;
  /** Optional description */
  description?: string;
  /** Connection status */
  status: "connected" | "disconnected" | "error";
  /** Owner email/name */
  owner?: string;
}

export interface ToolDisambiguationDialogProps {
  /** Whether dialog is open */
  isOpen: boolean;
  /** The original tool reference string */
  toolReference: string;
  /** Server name from the reference */
  serverName: string;
  /** Tool name from the reference */
  toolName: string;
  /** List of connections that provide this tool */
  connections: AmbiguousConnection[];
  /** Callback when user selects a connection */
  onSelect: (connection: AmbiguousConnection, remember?: boolean) => void;
  /** Callback when user cancels */
  onCancel: () => void;
}

/**
 * ToolDisambiguationDialog shows options when multiple connections
 * provide the same tool.
 */
export function ToolDisambiguationDialog({
  isOpen,
  serverName,
  toolName,
  connections,
  onSelect,
  onCancel,
}: ToolDisambiguationDialogProps) {
  const titleId = useId();
  const descId = useId();

  // Find first connected option for default selection
  const defaultIndex = connections.findIndex((c) => c.status === "connected");
  const initialIndex = defaultIndex >= 0 ? defaultIndex : 0;

  const [selectedIndex, setSelectedIndex] = useState(initialIndex);
  const [rememberChoice, setRememberChoice] = useState(false);

  // Reset selection when connections change
  useEffect(() => {
    const newDefault = connections.findIndex((c) => c.status === "connected");
    setSelectedIndex(newDefault >= 0 ? newDefault : 0);
  }, [connections]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onCancel();
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, connections.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      }
    },
    [connections.length, onCancel],
  );

  const handleConfirm = useCallback(() => {
    if (connections[selectedIndex]) {
      onSelect(connections[selectedIndex], rememberChoice);
    }
  }, [connections, selectedIndex, rememberChoice, onSelect]);

  const handleOptionClick = useCallback((index: number) => {
    setSelectedIndex(index);
  }, []);

  if (!isOpen) {
    return null;
  }

  const selectedConnection = connections[selectedIndex];
  const isDisconnectedSelected = selectedConnection?.status === "disconnected";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descId}
      className="fixed inset-0 z-modal flex items-center justify-center bg-neutral-1/80 backdrop-blur-sm"
      onKeyDown={handleKeyDown}
    >
      <div className="w-full max-w-md bg-neutral-1 border border-neutral-6 rounded-lg shadow-xl">
        {/* Header */}
        <div className="px-4 py-3 border-b border-neutral-6">
          <h2
            id={titleId}
            className="text-base font-semibold text-neutral-12 flex items-center gap-2"
          >
            <Wrench size={18} className="text-primary-9" aria-hidden />
            Multiple connections found
          </h2>
          <p className="text-sm text-neutral-11 mt-1">
            <code className="px-1 py-0.5 bg-neutral-3 rounded text-primary-11">
              {serverName}:{toolName}
            </code>
          </p>
        </div>

        {/* Description */}
        <p
          id={descId}
          className="px-4 py-2 text-sm text-neutral-11 bg-neutral-2"
        >
          Multiple connections provide this tool. Select which one to use.
        </p>

        {/* Options */}
        {connections.length === 0 ? (
          <div className="px-4 py-6 text-center text-neutral-10">
            <AlertCircle size={24} className="mx-auto mb-2 text-warning-9" />
            <p>No connections available for this tool.</p>
          </div>
        ) : (
          <div
            role="radiogroup"
            aria-label="Select connection"
            className="px-4 py-3 space-y-2 max-h-64 overflow-y-auto"
          >
            {connections.map((connection, index) => {
              const isSelected = index === selectedIndex;
              const isDisconnected = connection.status === "disconnected";

              return (
                <div
                  key={connection.connectionId}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={isSelected ? 0 : -1}
                  onClick={() => handleOptionClick(index)}
                  className={cn(
                    "p-3 rounded-lg border cursor-pointer transition-colors",
                    "flex items-start gap-3",
                    isSelected
                      ? "border-primary-7 bg-primary-2"
                      : "border-neutral-6 hover:border-neutral-8 hover:bg-neutral-2",
                    isDisconnected && "opacity-60",
                  )}
                >
                  {/* Selection indicator */}
                  <div
                    className={cn(
                      "w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-0.5",
                      isSelected
                        ? "border-primary-9 bg-primary-9"
                        : "border-neutral-7",
                    )}
                  >
                    {isSelected && (
                      <Check size={12} className="text-white" aria-hidden />
                    )}
                  </div>

                  {/* Connection info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Server
                        size={14}
                        className="text-neutral-9"
                        aria-hidden
                      />
                      <span className="font-medium text-neutral-12 truncate">
                        {connection.displayName}
                      </span>

                      {/* Status badge */}
                      <span
                        className={cn(
                          "text-xs px-1.5 py-0.5 rounded",
                          connection.status === "connected"
                            ? "bg-success-3 text-success-11"
                            : "bg-warning-3 text-warning-11",
                        )}
                      >
                        {connection.status === "connected"
                          ? "Connected"
                          : "Disconnected"}
                      </span>
                    </div>

                    {connection.description && (
                      <p className="text-sm text-neutral-10 mt-1 truncate">
                        {connection.description}
                      </p>
                    )}

                    {connection.owner && (
                      <p className="text-xs text-neutral-9 mt-1">
                        Owner: {connection.owner}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Warning for disconnected selection */}
        {isDisconnectedSelected && (
          <div className="mx-4 mb-3 p-2 bg-warning-2 border border-warning-6 rounded text-sm text-warning-11 flex items-center gap-2">
            <AlertCircle size={16} aria-hidden />
            This connection is currently disconnected. The tool may not be
            available.
          </div>
        )}

        {/* Remember choice */}
        <div className="px-4 pb-3">
          <Checkbox
            checked={rememberChoice}
            onChange={(checked) => setRememberChoice(checked)}
            label="Remember my choice for this tool"
          />
        </div>

        {/* Actions */}
        <div className="px-4 py-3 border-t border-neutral-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConfirm}
            disabled={connections.length === 0}
          >
            Use Selected
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ToolDisambiguationDialog;
