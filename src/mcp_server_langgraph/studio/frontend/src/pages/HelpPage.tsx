/**
 * HelpPage
 *
 * Full-page help center for the Studio Shell.
 * Renders HelpPane with default topics and optional keyboard shortcuts.
 */
import { useCallback, useState } from "react";
import { HelpPane, type HelpTopic } from "../help/HelpPane";
import { KeyboardShortcuts } from "../help/KeyboardShortcuts";
import {
  DEFAULT_HELP_TOPICS,
  DEFAULT_SHORTCUT_CATEGORIES,
} from "../help/helpData";
import { cn } from "../utils/cn";

// Re-export for backwards compatibility
export { DEFAULT_SHORTCUT_CATEGORIES } from "../help/helpData";

export function HelpPage() {
  const [selectedTopic, setSelectedTopic] = useState<HelpTopic | null>(null);

  const handleTopicSelect = useCallback((topic: HelpTopic) => {
    setSelectedTopic(topic);
  }, []);

  return (
    <div
      data-testid="help-page"
      className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 p-6"
    >
      <div className="max-w-4xl mx-auto w-full space-y-6">
        {/* Page Header */}
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Help Center
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Help Topics */}
          <HelpPane
            topics={DEFAULT_HELP_TOPICS}
            onTopicSelect={handleTopicSelect}
            className="h-[500px]"
          />

          {/* Selected Topic or Keyboard Shortcuts */}
          <div className="space-y-6">
            {selectedTopic ? (
              <div
                data-testid="help-topic-detail"
                className={cn(
                  "rounded-lg border border-gray-200 dark:border-gray-700",
                  "bg-white dark:bg-gray-800 p-6",
                )}
              >
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {selectedTopic.title}
                </h2>
                <span
                  className={cn(
                    "inline-block text-xs px-2 py-0.5 rounded mb-4",
                    selectedTopic.category === "basics" &&
                      "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
                    selectedTopic.category === "productivity" &&
                      "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
                    selectedTopic.category === "compliance" &&
                      "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
                  )}
                >
                  {selectedTopic.category}
                </span>
                <p className="text-gray-600 dark:text-gray-300">
                  {selectedTopic.content}
                </p>
              </div>
            ) : (
              <div
                className={cn(
                  "rounded-lg border border-gray-200 dark:border-gray-700",
                  "bg-white dark:bg-gray-800 p-6",
                  "text-center text-gray-500 dark:text-gray-400",
                )}
              >
                <p>Select a topic to see details</p>
              </div>
            )}

            {/* Keyboard Shortcuts */}
            <KeyboardShortcuts
              categories={DEFAULT_SHORTCUT_CATEGORIES}
              className="h-auto"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
