/**
 * ConnectorSuggestionBar
 *
 * Proactive suggestion bar that appears above chat input when user's message
 * keywords match available connection templates. Helps users discover and
 * configure relevant MCP connections before sending messages.
 *
 * Design: Subtle info bar with template icon, message, Connect button, and Dismiss.
 */

import { motion, AnimatePresence } from "motion/react";
import { Lightbulb, X, Loader2 } from "lucide-react";
import { Button } from "@/components/UI";
import { toastVariants } from "../../design-system/micro-interactions";
import { useMotionSafeVariants } from "../../hooks/useMotionSafe";
import type { ConnectionTemplate } from "../../types/connectionTemplate";

export interface ConnectorSuggestionBarProps {
  /** Suggested templates matching user input */
  suggestions: ConnectionTemplate[];
  /** Called when user clicks Connect button */
  onConnect: (template: ConnectionTemplate) => void;
  /** Called when user dismisses the suggestion bar */
  onDismiss: () => void;
  /** Show loading indicator while fetching suggestions */
  isLoading?: boolean;
}

/**
 * ConnectorSuggestionBar displays proactive connection suggestions
 * based on user input keywords.
 */
export function ConnectorSuggestionBar({
  suggestions,
  onConnect,
  onDismiss,
  isLoading = false,
}: ConnectorSuggestionBarProps) {
  const safeToastVariants = useMotionSafeVariants(toastVariants);

  // Show loading state
  if (isLoading) {
    return (
      <div
        data-testid="suggestion-loading"
        className="flex items-center gap-2 px-4 py-2 bg-primary-3 border border-primary-6 rounded-lg"
      >
        <Loader2 className="w-4 h-4 animate-spin text-primary-9" />
        <span className="text-sm text-primary-11">
          Checking for relevant connections...
        </span>
      </div>
    );
  }

  // Don't render if no suggestions
  if (suggestions.length === 0) {
    return null;
  }

  // Display the first suggestion (most relevant)
  const template = suggestions[0];
  const displayName = template.name;

  return (
    <AnimatePresence>
      <motion.div
        data-testid="connector-suggestion-bar"
        variants={safeToastVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        className="flex items-center justify-between gap-3 px-4 py-2 bg-primary-3 border border-primary-6 rounded-lg"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Lightbulb className="w-4 h-4 text-primary-9 flex-shrink-0" />
          <span className="text-sm text-primary-11 truncate">
            This might need <strong>{displayName}</strong> access.
          </span>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <Button
            type="button"
            variant="primary"
            onClick={() => onConnect(template)}
            className="px-3 py-1 text-sm font-medium text-neutral-12 bg-primary-10 hover:bg-primary-11 rounded-md transition-colors"
          >
            Connect {displayName}
          </Button>
          <Button
            size="icon"
            type="button"
            variant="ghost"
            onClick={onDismiss}
            aria-label="Dismiss"
            className="p-1 text-primary-9 hover:text-primary-11 dark:hover:text-primary-5 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
