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
      className="flex flex-col h-full bg-neutral-1 p-6"
    >
      <div className="max-w-4xl mx-auto w-full space-y-6">
        {/* Page Header */}
        <h1 className="text-2xl font-bold text-neutral-12">Help Center</h1>

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
                  "rounded-lg border border-neutral-5",
                  "bg-neutral-1 p-6",
                )}
              >
                <h2 className="text-lg font-semibold text-neutral-12 mb-2">
                  {selectedTopic.title}
                </h2>
                <span
                  className={cn(
                    "inline-block text-xs px-2 py-0.5 rounded mb-4",
                    selectedTopic.category === "basics" &&
                      "bg-primary-3 text-primary-11",
                    selectedTopic.category === "productivity" &&
                      "bg-success-3 text-success-11",
                    selectedTopic.category === "compliance" &&
                      "bg-insight-2 text-insight-11",
                  )}
                >
                  {selectedTopic.category}
                </span>
                <p className="text-neutral-11">{selectedTopic.content}</p>
              </div>
            ) : (
              <div
                className={cn(
                  "rounded-lg border border-neutral-5",
                  "bg-neutral-1 p-6",
                  "text-center text-neutral-11",
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
