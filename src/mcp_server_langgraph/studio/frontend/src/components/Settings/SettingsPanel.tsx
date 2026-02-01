/**
 * SettingsPanel Component
 *
 * User preferences settings panel with tabbed interface.
 * Implements WCAG 2.1 AA accessibility requirements.
 *
 * Features:
 * - General settings (theme, language, auto-scroll)
 * - Accessibility settings (reduced motion, high contrast, screen reader)
 * - Model defaults (temperature, max tokens, reasoning effort)
 * - Keyboard shortcuts customization
 * - Privacy settings (analytics, error reporting)
 *
 * Based on UX patterns from Gemini CLI, OpenAI Codex, and Claude Code.
 */

import { useState, useCallback, useRef } from "react";
import {
  X,
  Settings,
  Accessibility,
  Cpu,
  Keyboard,
  Shield,
  RotateCcw,
  UserCheck,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  selectSubmitOnEnter,
  setSubmitOnEnter,
} from "../../store/slices/uiSlice";
import { usePreferences } from "../../contexts/PreferencesContext";
import {
  DEFAULT_KEYBOARD_SHORTCUTS,
  type ThemeMode,
  type FontSize,
} from "../../types/preferences";
import { useThresholdSettings } from "../../hooks/useThresholdSettings";

import { Button, Input, Select, Slider, Toggle } from "@/components/UI";

// ==============================================================================
// Types
// ==============================================================================

export interface SettingsPanelProps {
  /** Additional CSS classes */
  className?: string;
  /** Callback when panel is closed */
  onClose?: () => void;
}

type SettingsTab =
  | "general"
  | "accessibility"
  | "model"
  | "shortcuts"
  | "privacy"
  | "hitl";

interface TabConfig {
  id: SettingsTab;
  label: string;
  icon: React.ReactNode;
}

// ==============================================================================
// Constants
// ==============================================================================

const TABS: TabConfig[] = [
  { id: "general", label: "General", icon: <Settings size={16} /> },
  {
    id: "accessibility",
    label: "Accessibility",
    icon: <Accessibility size={16} />,
  },
  { id: "model", label: "Model Defaults", icon: <Cpu size={16} /> },
  { id: "shortcuts", label: "Shortcuts", icon: <Keyboard size={16} /> },
  { id: "privacy", label: "Privacy", icon: <Shield size={16} /> },
  { id: "hitl", label: "Agent Approval", icon: <UserCheck size={16} /> },
];

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "ja", label: "日本語" },
  { code: "zh", label: "中文" },
];

// ==============================================================================
// Component
// ==============================================================================

export function SettingsPanel({ className = "", onClose }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const tabListRef = useRef<HTMLDivElement>(null);

  const {
    preferences,
    isInitialized,
    updateGeneralPreferences,
    updateAccessibilityPreferences,
    updateModelDefaults,
    updatePrivacyPreferences,
    updateHITLPreferences,
    resetToDefaults,
  } = usePreferences();

  // Threshold settings hook for rotating thresholds
  const {
    recommendation,
    isLoading: thresholdLoading,
    error: thresholdError,
    fetchRecommendation,
    applyRecommendation,
    updateSettings: updateThresholdSettings,
  } = useThresholdSettings();

  // State for auto-adjust toggle (local, will be synced to backend)
  const [autoAdjustEnabled, setAutoAdjustEnabled] = useState(false);

  // Redux state for keyboard preference (Sprint 5.3)
  const dispatch = useAppDispatch();
  const submitOnEnter = useAppSelector(selectSubmitOnEnter);

  // ---------------------------------------------------------------------------
  // Keyboard navigation for tabs
  // ---------------------------------------------------------------------------
  const handleTabKeyDown = useCallback(
    (e: React.KeyboardEvent, currentIndex: number) => {
      const tabCount = TABS.length;
      let newIndex = currentIndex;

      switch (e.key) {
        case "ArrowRight":
          e.preventDefault();
          newIndex = (currentIndex + 1) % tabCount;
          break;
        case "ArrowLeft":
          e.preventDefault();
          newIndex = (currentIndex - 1 + tabCount) % tabCount;
          break;
        case "Home":
          e.preventDefault();
          newIndex = 0;
          break;
        case "End":
          e.preventDefault();
          newIndex = tabCount - 1;
          break;
        default:
          return;
      }

      const targetTab = TABS[newIndex];
      if (targetTab) {
        setActiveTab(targetTab.id);
        // Focus the new tab
        const tabs = tabListRef.current?.querySelectorAll('[role="tab"]');
        (tabs?.[newIndex] as HTMLElement)?.focus();
      }
    },
    [],
  );

  // ---------------------------------------------------------------------------
  // Reset confirmation
  // ---------------------------------------------------------------------------
  const handleReset = useCallback(() => {
    resetToDefaults();
    setShowResetConfirm(false);
  }, [resetToDefaults]);

  // ---------------------------------------------------------------------------
  // Render loading state
  // ---------------------------------------------------------------------------
  if (!isInitialized) {
    return (
      <div
        data-testid="settings-panel"
        className={`settings-panel loading ${className}`}
      >
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-9" />
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Tab content renderers
  // ---------------------------------------------------------------------------
  const renderGeneralTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">General Settings</h3>

      {/* Theme */}
      <div className="space-y-2">
        <label
          htmlFor="theme-select"
          className="block text-sm font-medium text-neutral-11"
        >
          Theme
        </label>
        <Select
          className="px-3 py-2 text-sm -500 focus:ring-primary-7"
          id="theme-select"
          value={preferences.general.theme}
          onChange={(e) =>
            updateGeneralPreferences({ theme: e.target.value as ThemeMode })
          }
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </Select>
      </div>

      {/* Language */}
      <div className="space-y-2">
        <label
          htmlFor="language-select"
          className="block text-sm font-medium text-neutral-11"
        >
          Language
        </label>
        <Select
          className="px-3 py-2 text-sm -500 focus:ring-primary-7"
          id="language-select"
          value={preferences.general.language}
          onChange={(e) =>
            updateGeneralPreferences({ language: e.target.value })
          }
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.label}
            </option>
          ))}
        </Select>
      </div>

      {/* Auto-scroll */}
      <Toggle
        id="auto-scroll-toggle"
        checked={preferences.general.autoScroll}
        onChange={(checked) =>
          updateGeneralPreferences({ autoScroll: checked })
        }
        label="Auto-scroll to new messages"
      />

      {/* Keyboard shortcut: Enter to send (Sprint 5.3) */}
      <Toggle
        id="submit-on-enter-toggle"
        checked={submitOnEnter}
        onChange={() => dispatch(setSubmitOnEnter(!submitOnEnter))}
        label="Press Enter to send messages"
        description={
          submitOnEnter ? "Shift+Enter for new line" : "Use Ctrl+Enter to send"
        }
      />

      {/* Notifications */}
      <Toggle
        id="notifications-toggle"
        checked={preferences.general.notificationsEnabled}
        onChange={(checked) =>
          updateGeneralPreferences({ notificationsEnabled: checked })
        }
        label="Enable notifications"
      />
    </div>
  );

  const renderAccessibilityTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Accessibility Settings</h3>

      {/* Reduced Motion */}
      <Toggle
        id="reduced-motion-toggle"
        checked={preferences.accessibility.reducedMotion}
        onChange={(checked) =>
          updateAccessibilityPreferences({ reducedMotion: checked })
        }
        label="Reduce motion"
        description="Minimize animations and transitions"
      />

      {/* High Contrast */}
      <Toggle
        id="high-contrast-toggle"
        checked={preferences.accessibility.highContrast}
        onChange={(checked) =>
          updateAccessibilityPreferences({ highContrast: checked })
        }
        label="High contrast"
        description="Increase color contrast for better visibility"
      />

      {/* Screen Reader Mode */}
      <Toggle
        id="screen-reader-toggle"
        checked={preferences.accessibility.screenReaderMode}
        onChange={(checked) =>
          updateAccessibilityPreferences({ screenReaderMode: checked })
        }
        label="Screen reader optimized"
        description="Optimize UI for screen reader usage"
      />

      {/* Font Size */}
      <div className="space-y-2">
        <label
          htmlFor="font-size-select"
          className="block text-sm font-medium text-neutral-11"
        >
          Font size
        </label>
        <Select
          className="px-3 py-2 text-sm -500 focus:ring-primary-7"
          id="font-size-select"
          value={preferences.accessibility.fontSize}
          onChange={(e) =>
            updateAccessibilityPreferences({
              fontSize: e.target.value as FontSize,
            })
          }
        >
          <option value="small">Small</option>
          <option value="medium">Medium</option>
          <option value="large">Large</option>
        </Select>
      </div>
    </div>
  );

  const renderModelTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Model Default Settings</h3>

      {/* Temperature */}
      <div className="space-y-2">
        <Slider
          id="temperature-slider"
          value={preferences.modelDefaults.defaultTemperature}
          onChange={(value) =>
            updateModelDefaults({ defaultTemperature: value })
          }
          min={0}
          max={1}
          step={0.1}
          label="Temperature"
          showValue
          formatValue={(v) => v.toFixed(1)}
        />
        <p className="text-xs text-neutral-10">
          Higher values make output more random, lower values more focused
        </p>
      </div>

      {/* Max Tokens */}
      <div className="space-y-2">
        <label
          htmlFor="max-tokens-input"
          className="block text-sm font-medium text-neutral-11"
        >
          Max tokens
        </label>
        <Input
          className="px-3 py-2 text-sm -500 focus:ring-primary-7"
          id="max-tokens-input"
          type="number"
          min="100"
          max="128000"
          step="100"
          value={preferences.modelDefaults.defaultMaxTokens}
          onChange={(e) =>
            updateModelDefaults({
              defaultMaxTokens: parseInt(e.target.value, 10) || 4096,
            })
          }
        />
        <p className="text-xs text-neutral-10">
          Maximum number of tokens in the response
        </p>
      </div>

      {/* Reasoning Effort */}
      <div className="space-y-2">
        <label
          htmlFor="reasoning-effort-select"
          className="block text-sm font-medium text-neutral-11"
        >
          Reasoning effort
        </label>
        <Select
          className="px-3 py-2 text-sm -500 focus:ring-primary-7"
          id="reasoning-effort-select"
          value={preferences.modelDefaults.defaultReasoningEffort}
          onChange={(e) =>
            updateModelDefaults({
              defaultReasoningEffort: e.target.value as
                | "low"
                | "medium"
                | "high",
            })
          }
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </Select>
        <p className="text-xs text-neutral-10">
          Amount of thinking for models with extended thinking capabilities
        </p>
      </div>
    </div>
  );

  const renderShortcutsTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Keyboard Shortcuts</h3>

      <div className="space-y-2">
        {DEFAULT_KEYBOARD_SHORTCUTS.map((shortcut) => (
          <div
            key={shortcut.action}
            className="flex items-center justify-between py-2 border-b border-neutral-5"
          >
            <span className="text-sm text-neutral-11">{shortcut.label}</span>
            <kbd className="px-2 py-1 text-xs font-mono bg-neutral-2 rounded border border-neutral-5">
              {preferences.keyboardShortcuts[shortcut.action] || shortcut.keys}
            </kbd>
          </div>
        ))}
      </div>

      <p className="text-xs text-neutral-10">
        Keyboard shortcut customization coming soon
      </p>
    </div>
  );

  const renderPrivacyTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Privacy Settings</h3>

      {/* Analytics */}
      <Toggle
        id="analytics-toggle"
        checked={preferences.privacy.analyticsEnabled}
        onChange={(checked) =>
          updatePrivacyPreferences({ analyticsEnabled: checked })
        }
        label="Usage analytics"
        description="Help improve the product with anonymous usage data"
      />

      {/* Error Reporting */}
      <Toggle
        id="error-reporting-toggle"
        checked={preferences.privacy.errorReportingEnabled}
        onChange={(checked) =>
          updatePrivacyPreferences({ errorReportingEnabled: checked })
        }
        label="Error reporting"
        description="Automatically report crashes and errors"
      />

      {/* Store History */}
      <Toggle
        id="store-history-toggle"
        checked={preferences.privacy.storeHistoryLocally}
        onChange={(checked) =>
          updatePrivacyPreferences({ storeHistoryLocally: checked })
        }
        label="Store history locally"
        description="Keep conversation history in browser storage"
      />
    </div>
  );

  const renderHITLTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Agent Approval Settings</h3>
      <p className="text-sm text-neutral-11">
        Configure when AI agents pause for your approval before taking actions.
      </p>

      {/* Enable HITL */}
      <Toggle
        id="hitl-enabled-toggle"
        checked={preferences.hitl.enabled}
        onChange={(checked) => updateHITLPreferences({ enabled: checked })}
        label="Enable agent approval"
        description="Require approval for low-confidence agent decisions"
      />

      {/* Confidence Threshold */}
      <div className="space-y-2">
        <Slider
          id="confidence-threshold-slider"
          value={preferences.hitl.confidenceThreshold * 100}
          onChange={(value) =>
            updateHITLPreferences({ confidenceThreshold: value / 100 })
          }
          min={50}
          max={90}
          step={5}
          label="Confidence threshold"
          showValue
          formatValue={(v) => `${Math.round(v)}%`}
          disabled={!preferences.hitl.enabled}
        />
        <p className="text-xs text-neutral-10">
          Require approval when agent confidence is below this threshold
        </p>
      </div>

      {/* Auto-approve Threshold */}
      <div className="space-y-2">
        <Slider
          id="auto-approve-threshold-slider"
          value={preferences.hitl.autoApproveThreshold * 100}
          onChange={(value) =>
            updateHITLPreferences({ autoApproveThreshold: value / 100 })
          }
          min={85}
          max={100}
          step={5}
          label="Auto-approve threshold"
          showValue
          formatValue={(v) => `${Math.round(v)}%`}
          disabled={!preferences.hitl.enabled}
        />
        <p className="text-xs text-neutral-10">
          Skip approval when agent confidence exceeds this threshold
        </p>
      </div>

      {/* Push Notifications */}
      <Toggle
        id="hitl-push-toggle"
        checked={preferences.hitl.pushNotificationsEnabled}
        onChange={(checked) =>
          updateHITLPreferences({ pushNotificationsEnabled: checked })
        }
        label="Push notifications"
        description="Get notified when an agent needs your approval"
        disabled={!preferences.hitl.enabled}
      />

      {/* Sound */}
      <Toggle
        id="hitl-sound-toggle"
        checked={preferences.hitl.soundEnabled}
        onChange={(checked) => updateHITLPreferences({ soundEnabled: checked })}
        label="Sound alerts"
        description="Play a sound when an agent needs approval"
        disabled={!preferences.hitl.enabled}
      />

      {/* Threshold Recommendation Section */}
      <div className="mt-6 pt-6 border-t border-neutral-5">
        <h4 className="text-md font-medium text-neutral-12 mb-2">
          Threshold Recommendation
        </h4>
        <p className="text-xs text-neutral-10 mb-4">
          Get AI-powered recommendations based on your approval history
          patterns.
        </p>

        {/* Auto-adjust toggle */}
        <div className="mb-4">
          <Toggle
            id="auto-adjust-toggle"
            checked={autoAdjustEnabled}
            onChange={(checked) => {
              setAutoAdjustEnabled(checked);
              updateThresholdSettings({ autoAdjustEnabled: checked });
            }}
            label="Auto-adjust thresholds"
            description="Automatically adjust thresholds based on approval patterns"
            disabled={!preferences.hitl.enabled}
          />
        </div>

        {/* Recommendation display and actions */}
        <div className="flex flex-col gap-3">
          {recommendation && (
            <div className="bg-primary-1 dark:bg-primary-a3 p-3 rounded-lg border border-primary-4 dark:border-primary-11">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={16} className="text-primary-9" />
                <span className="text-sm font-medium text-primary-11 dark:text-primary-4">
                  Recommended:{" "}
                  {Math.round(recommendation.recommendedThreshold * 100)}%
                </span>
              </div>
              <p className="text-xs text-primary-11 dark:text-primary-5 mb-2">
                {recommendation.reason}
              </p>
              <p className="text-xs text-neutral-10">
                Based on {recommendation.sampleSize} approval decisions
                (confidence: {Math.round(recommendation.confidenceLevel * 100)}
                %)
              </p>
            </div>
          )}

          {thresholdError && (
            <div className="bg-error-1 dark:bg-error-a3 p-3 rounded-lg border border-error-4 dark:border-error-11">
              <p className="text-xs text-error-10 dark:text-error-7">
                {thresholdError}
              </p>
            </div>
          )}

          <div className="flex gap-2">
            <Button
              variant="secondary"
              className="flex px-3 py-2 text-sm bg-neutral-2 hover:bg-neutral-3 rounded-md"
              onClick={fetchRecommendation}
              disabled={!preferences.hitl.enabled || thresholdLoading}
            >
              {thresholdLoading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RotateCcw size={14} />
              )}
              Get Recommendation
            </Button>

            <Button
              variant="primary"
              className="flex px-3 py-2 text-sm bg-primary-10 hover:bg-primary-11 text-neutral-12 rounded-md"
              onClick={async () => {
                const result = await applyRecommendation();
                if (result) {
                  updateHITLPreferences({
                    confidenceThreshold: result.adjustedThreshold,
                  });
                }
              }}
              disabled={
                !preferences.hitl.enabled || !recommendation || thresholdLoading
              }
            >
              <Sparkles size={14} />
              Apply Recommendation
            </Button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderTabContent = () => {
    switch (activeTab) {
      case "general":
        return renderGeneralTab();
      case "accessibility":
        return renderAccessibilityTab();
      case "model":
        return renderModelTab();
      case "shortcuts":
        return renderShortcutsTab();
      case "privacy":
        return renderPrivacyTab();
      case "hitl":
        return renderHITLTab();
      default:
        return null;
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div
      data-testid="settings-panel"
      className={`settings-panel bg-neutral-1 rounded-lg shadow-lg ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-5">
        <h2 className="text-lg font-semibold">Settings</h2>
        <Button
          size="icon"
          variant="secondary"
          className="p-1 rounded-md hover:bg-neutral-2 focus:ring-primary-7"
          onClick={onClose}
          aria-label="Close settings"
        >
          <X size={20} />
        </Button>
      </div>
      {/* Tabs */}
      <div
        ref={tabListRef}
        role="tablist"
        aria-label="Settings tabs"
        className="flex border-b border-neutral-5 px-2"
      >
        {TABS.map((tab, index) => (
          <Button
            variant="ghost"
            className="flex .5 px-3 py-2 text-sm border-b-2 -mb-px focus:ring-inset focus:ring-primary-7"
            key={tab.id}
            id={`tab-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => setActiveTab(tab.id)}
            onKeyDown={(e) => handleTabKeyDown(e, index)}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </Button>
        ))}
      </div>
      {/* Tab Content */}
      <div
        id={`tabpanel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className="p-4 min-h-[300px]"
      >
        {renderTabContent()}
      </div>
      {/* Footer */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-neutral-5 bg-neutral-1 rounded-b-lg">
        <Button
          variant="danger"
          className="flex .5 px-3 py-1.5 text-sm text-error-10 dark:text-error-7 hover:bg-error-1 dark:hover:bg-error-a3 rounded-md focus:ring-error-7"
          onClick={() => setShowResetConfirm(true)}
        >
          <RotateCcw size={14} />
          Reset to defaults
        </Button>

        <Button
          variant="primary"
          className="px-4 py-1.5 text-sm text-neutral-12 bg-primary-10 rounded-md hover:bg-primary-11 focus:ring-primary-7 focus:ring-offset-2"
          onClick={onClose}
        >
          Done
        </Button>
      </div>
      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-modal flex items-center justify-center bg-neutral-a6">
          <div
            role="alertdialog"
            aria-labelledby="reset-dialog-title"
            aria-describedby="reset-dialog-description"
            className="bg-neutral-1 rounded-lg shadow-xl p-6 max-w-sm mx-4"
          >
            <h3 id="reset-dialog-title" className="text-lg font-semibold mb-2">
              Reset Settings
            </h3>
            <p
              id="reset-dialog-description"
              className="text-sm text-neutral-11 mb-4"
            >
              Are you sure you want to reset all settings to their default
              values? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                className="px-3 py-1.5 text-sm text-neutral-11 hover:bg-neutral-2 rounded-md focus:ring-neutral-8"
                onClick={() => setShowResetConfirm(false)}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                className="px-3 py-1.5 text-sm text-neutral-12 bg-error-10 rounded-md hover:bg-error-11 focus:ring-error-7"
                onClick={handleReset}
              >
                Reset
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SettingsPanel;
