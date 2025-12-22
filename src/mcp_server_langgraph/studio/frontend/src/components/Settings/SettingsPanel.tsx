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

import { useState, useCallback, useRef, useEffect } from "react";
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
import { usePreferences } from "../../contexts/PreferencesContext";
import {
  DEFAULT_KEYBOARD_SHORTCUTS,
  type ThemeMode,
  type FontSize,
} from "../../types/preferences";
import { useThresholdSettings } from "../../hooks/useThresholdSettings";

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
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
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
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Theme
        </label>
        <select
          id="theme-select"
          value={preferences.general.theme}
          onChange={(e) =>
            updateGeneralPreferences({ theme: e.target.value as ThemeMode })
          }
          className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </div>

      {/* Language */}
      <div className="space-y-2">
        <label
          htmlFor="language-select"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Language
        </label>
        <select
          id="language-select"
          value={preferences.general.language}
          onChange={(e) =>
            updateGeneralPreferences({ language: e.target.value })
          }
          className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {LANGUAGES.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.label}
            </option>
          ))}
        </select>
      </div>

      {/* Auto-scroll */}
      <div className="flex items-center justify-between">
        <label
          htmlFor="auto-scroll-toggle"
          className="text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Auto-scroll to new messages
        </label>
        <button
          id="auto-scroll-toggle"
          role="switch"
          aria-checked={preferences.general.autoScroll}
          onClick={() =>
            updateGeneralPreferences({
              autoScroll: !preferences.general.autoScroll,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.general.autoScroll ? "bg-blue-600" : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.general.autoScroll ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Notifications */}
      <div className="flex items-center justify-between">
        <label
          htmlFor="notifications-toggle"
          className="text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Enable notifications
        </label>
        <button
          id="notifications-toggle"
          role="switch"
          aria-checked={preferences.general.notificationsEnabled}
          onClick={() =>
            updateGeneralPreferences({
              notificationsEnabled: !preferences.general.notificationsEnabled,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.general.notificationsEnabled
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.general.notificationsEnabled
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );

  const renderAccessibilityTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Accessibility Settings</h3>

      {/* Reduced Motion */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="reduced-motion-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Reduce motion
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Minimize animations and transitions
          </p>
        </div>
        <button
          id="reduced-motion-toggle"
          role="switch"
          aria-checked={preferences.accessibility.reducedMotion}
          onClick={() =>
            updateAccessibilityPreferences({
              reducedMotion: !preferences.accessibility.reducedMotion,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.accessibility.reducedMotion
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.accessibility.reducedMotion
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* High Contrast */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="high-contrast-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            High contrast
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Increase color contrast for better visibility
          </p>
        </div>
        <button
          id="high-contrast-toggle"
          role="switch"
          aria-checked={preferences.accessibility.highContrast}
          onClick={() =>
            updateAccessibilityPreferences({
              highContrast: !preferences.accessibility.highContrast,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.accessibility.highContrast
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.accessibility.highContrast
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Screen Reader Mode */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="screen-reader-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Screen reader optimized
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Optimize UI for screen reader usage
          </p>
        </div>
        <button
          id="screen-reader-toggle"
          role="switch"
          aria-checked={preferences.accessibility.screenReaderMode}
          onClick={() =>
            updateAccessibilityPreferences({
              screenReaderMode: !preferences.accessibility.screenReaderMode,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.accessibility.screenReaderMode
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.accessibility.screenReaderMode
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Font Size */}
      <div className="space-y-2">
        <label
          htmlFor="font-size-select"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Font size
        </label>
        <select
          id="font-size-select"
          value={preferences.accessibility.fontSize}
          onChange={(e) =>
            updateAccessibilityPreferences({
              fontSize: e.target.value as FontSize,
            })
          }
          className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="small">Small</option>
          <option value="medium">Medium</option>
          <option value="large">Large</option>
        </select>
      </div>
    </div>
  );

  const renderModelTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Model Default Settings</h3>

      {/* Temperature */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="temperature-slider"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Temperature
          </label>
          <span className="text-sm text-gray-500">
            {preferences.modelDefaults.defaultTemperature.toFixed(1)}
          </span>
        </div>
        <input
          id="temperature-slider"
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={preferences.modelDefaults.defaultTemperature}
          onChange={(e) =>
            updateModelDefaults({
              defaultTemperature: parseFloat(e.target.value),
            })
          }
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Higher values make output more random, lower values more focused
        </p>
      </div>

      {/* Max Tokens */}
      <div className="space-y-2">
        <label
          htmlFor="max-tokens-input"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Max tokens
        </label>
        <input
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
          className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Maximum number of tokens in the response
        </p>
      </div>

      {/* Reasoning Effort */}
      <div className="space-y-2">
        <label
          htmlFor="reasoning-effort-select"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Reasoning effort
        </label>
        <select
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
          className="block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
        <p className="text-xs text-gray-500 dark:text-gray-400">
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
            className="flex items-center justify-between py-2 border-b border-gray-200 dark:border-gray-700"
          >
            <span className="text-sm text-gray-700 dark:text-gray-300">
              {shortcut.label}
            </span>
            <kbd className="px-2 py-1 text-xs font-mono bg-gray-100 dark:bg-gray-800 rounded border border-gray-300 dark:border-gray-600">
              {preferences.keyboardShortcuts[shortcut.action] || shortcut.keys}
            </kbd>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-500 dark:text-gray-400">
        Keyboard shortcut customization coming soon
      </p>
    </div>
  );

  const renderPrivacyTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Privacy Settings</h3>

      {/* Analytics */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="analytics-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Usage analytics
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Help improve the product with anonymous usage data
          </p>
        </div>
        <button
          id="analytics-toggle"
          role="switch"
          aria-checked={preferences.privacy.analyticsEnabled}
          onClick={() =>
            updatePrivacyPreferences({
              analyticsEnabled: !preferences.privacy.analyticsEnabled,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.privacy.analyticsEnabled ? "bg-blue-600" : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.privacy.analyticsEnabled
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Error Reporting */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="error-reporting-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Error reporting
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Automatically report crashes and errors
          </p>
        </div>
        <button
          id="error-reporting-toggle"
          role="switch"
          aria-checked={preferences.privacy.errorReportingEnabled}
          onClick={() =>
            updatePrivacyPreferences({
              errorReportingEnabled: !preferences.privacy.errorReportingEnabled,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.privacy.errorReportingEnabled
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.privacy.errorReportingEnabled
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Store History */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="store-history-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Store history locally
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Keep conversation history in browser storage
          </p>
        </div>
        <button
          id="store-history-toggle"
          role="switch"
          aria-checked={preferences.privacy.storeHistoryLocally}
          onClick={() =>
            updatePrivacyPreferences({
              storeHistoryLocally: !preferences.privacy.storeHistoryLocally,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.privacy.storeHistoryLocally
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.privacy.storeHistoryLocally
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );

  const renderHITLTab = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium">Agent Approval Settings</h3>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        Configure when AI agents pause for your approval before taking actions.
      </p>

      {/* Enable HITL */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="hitl-enabled-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Enable agent approval
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Require approval for low-confidence agent decisions
          </p>
        </div>
        <button
          id="hitl-enabled-toggle"
          role="switch"
          aria-checked={preferences.hitl.enabled}
          onClick={() =>
            updateHITLPreferences({
              enabled: !preferences.hitl.enabled,
            })
          }
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            preferences.hitl.enabled ? "bg-blue-600" : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.hitl.enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Confidence Threshold */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="confidence-threshold-slider"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Confidence threshold
          </label>
          <span className="text-sm text-gray-500">
            {Math.round(preferences.hitl.confidenceThreshold * 100)}%
          </span>
        </div>
        <input
          id="confidence-threshold-slider"
          type="range"
          min="50"
          max="90"
          step="5"
          value={preferences.hitl.confidenceThreshold * 100}
          onChange={(e) =>
            updateHITLPreferences({
              confidenceThreshold: parseInt(e.target.value, 10) / 100,
            })
          }
          disabled={!preferences.hitl.enabled}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 disabled:opacity-50"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Require approval when agent confidence is below this threshold
        </p>
      </div>

      {/* Auto-approve Threshold */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label
            htmlFor="auto-approve-threshold-slider"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Auto-approve threshold
          </label>
          <span className="text-sm text-gray-500">
            {Math.round(preferences.hitl.autoApproveThreshold * 100)}%
          </span>
        </div>
        <input
          id="auto-approve-threshold-slider"
          type="range"
          min="85"
          max="100"
          step="5"
          value={preferences.hitl.autoApproveThreshold * 100}
          onChange={(e) =>
            updateHITLPreferences({
              autoApproveThreshold: parseInt(e.target.value, 10) / 100,
            })
          }
          disabled={!preferences.hitl.enabled}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 disabled:opacity-50"
        />
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Skip approval when agent confidence exceeds this threshold
        </p>
      </div>

      {/* Push Notifications */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="hitl-push-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Push notifications
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Get notified when an agent needs your approval
          </p>
        </div>
        <button
          id="hitl-push-toggle"
          role="switch"
          aria-checked={preferences.hitl.pushNotificationsEnabled}
          onClick={() =>
            updateHITLPreferences({
              pushNotificationsEnabled:
                !preferences.hitl.pushNotificationsEnabled,
            })
          }
          disabled={!preferences.hitl.enabled}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 ${
            preferences.hitl.pushNotificationsEnabled
              ? "bg-blue-600"
              : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.hitl.pushNotificationsEnabled
                ? "translate-x-6"
                : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Sound */}
      <div className="flex items-center justify-between">
        <div>
          <label
            htmlFor="hitl-sound-toggle"
            className="text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Sound alerts
          </label>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Play a sound when an agent needs approval
          </p>
        </div>
        <button
          id="hitl-sound-toggle"
          role="switch"
          aria-checked={preferences.hitl.soundEnabled}
          onClick={() =>
            updateHITLPreferences({
              soundEnabled: !preferences.hitl.soundEnabled,
            })
          }
          disabled={!preferences.hitl.enabled}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 ${
            preferences.hitl.soundEnabled ? "bg-blue-600" : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              preferences.hitl.soundEnabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>

      {/* Threshold Recommendation Section */}
      <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
        <h4 className="text-md font-medium text-gray-800 dark:text-gray-200 mb-2">
          Threshold Recommendation
        </h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Get AI-powered recommendations based on your approval history patterns.
        </p>

        {/* Auto-adjust toggle */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <label
              htmlFor="auto-adjust-toggle"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Auto-adjust thresholds
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Automatically adjust thresholds based on approval patterns
            </p>
          </div>
          <button
            id="auto-adjust-toggle"
            role="switch"
            aria-checked={autoAdjustEnabled}
            onClick={() => {
              const newValue = !autoAdjustEnabled;
              setAutoAdjustEnabled(newValue);
              updateThresholdSettings({ auto_adjust_enabled: newValue });
            }}
            disabled={!preferences.hitl.enabled}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 ${
              autoAdjustEnabled ? "bg-blue-600" : "bg-gray-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoAdjustEnabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* Recommendation display and actions */}
        <div className="flex flex-col gap-3">
          {recommendation && (
            <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-200 dark:border-blue-700">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={16} className="text-blue-500" />
                <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Recommended: {Math.round(recommendation.recommended_threshold * 100)}%
                </span>
              </div>
              <p className="text-xs text-blue-700 dark:text-blue-300 mb-2">
                {recommendation.reason}
              </p>
              <p className="text-xs text-gray-500">
                Based on {recommendation.sample_size} approval decisions (confidence: {Math.round(recommendation.confidence_level * 100)}%)
              </p>
            </div>
          )}

          {thresholdError && (
            <div className="bg-red-50 dark:bg-red-900/20 p-3 rounded-lg border border-red-200 dark:border-red-700">
              <p className="text-xs text-red-600 dark:text-red-400">{thresholdError}</p>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={fetchRecommendation}
              disabled={!preferences.hitl.enabled || thresholdLoading}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {thresholdLoading ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <RotateCcw size={14} />
              )}
              Get Recommendation
            </button>

            <button
              onClick={async () => {
                const result = await applyRecommendation();
                if (result) {
                  updateHITLPreferences({
                    confidenceThreshold: result.adjusted_threshold,
                  });
                }
              }}
              disabled={!preferences.hitl.enabled || !recommendation || thresholdLoading}
              className="flex items-center gap-2 px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles size={14} />
              Apply Recommendation
            </button>
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
      className={`settings-panel bg-white dark:bg-gray-900 rounded-lg shadow-lg ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold">Settings</h2>
        <button
          onClick={onClose}
          aria-label="Close settings"
          className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <X size={20} />
        </button>
      </div>

      {/* Tabs */}
      <div
        ref={tabListRef}
        role="tablist"
        aria-label="Settings tabs"
        className="flex border-b border-gray-200 dark:border-gray-700 px-2"
      >
        {TABS.map((tab, index) => (
          <button
            key={tab.id}
            id={`tab-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => setActiveTab(tab.id)}
            onKeyDown={(e) => handleTabKeyDown(e, index)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 ${
              activeTab === tab.id
                ? "border-blue-500 text-blue-600 dark:text-blue-400"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            }`}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
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
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-b-lg">
        <button
          onClick={() => setShowResetConfirm(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <RotateCcw size={14} />
          Reset to defaults
        </button>

        <button
          onClick={onClose}
          className="px-4 py-1.5 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Done
        </button>
      </div>

      {/* Reset Confirmation Modal */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div
            role="alertdialog"
            aria-labelledby="reset-dialog-title"
            aria-describedby="reset-dialog-description"
            className="bg-white dark:bg-gray-900 rounded-lg shadow-xl p-6 max-w-sm mx-4"
          >
            <h3 id="reset-dialog-title" className="text-lg font-semibold mb-2">
              Reset Settings
            </h3>
            <p
              id="reset-dialog-description"
              className="text-sm text-gray-600 dark:text-gray-400 mb-4"
            >
              Are you sure you want to reset all settings to their default
              values? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowResetConfirm(false)}
                className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
              <button
                onClick={handleReset}
                className="px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SettingsPanel;
