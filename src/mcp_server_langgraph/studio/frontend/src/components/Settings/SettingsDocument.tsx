/**
 * SettingsDocument Component
 *
 * A settings document component for use within the MainDock.
 * Displays application settings and preferences in a tabbed layout.
 *
 * Features:
 * - Profile settings (display name, email, persona)
 * - API key management
 * - Notification preferences
 * - Appearance settings (theme)
 * - Security options
 * - Compact mode for docked tabs
 */

import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
import { selectUser } from "../../store/slices/authSlice";
import { selectPersona, setPersona } from "../../store/slices/personaSlice";
import type { Persona } from "../../store/slices/personaSlice";
import {
  User,
  Key,
  Bell,
  Palette,
  Shield,
  Save,
  Eye,
  EyeOff,
  Check,
} from "lucide-react";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface SettingsDocumentProps {
  /** Whether to use compact styling for docked mode */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

type SettingsTab =
  | "profile"
  | "api-keys"
  | "notifications"
  | "appearance"
  | "security";

// =============================================================================
// Component
// =============================================================================

export function SettingsDocument({
  compact = false,
  className,
}: SettingsDocumentProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const user = useAppSelector(selectUser);
  const persona = useAppSelector(selectPersona);
  const dispatch = useAppDispatch();

  // Form state
  const [displayName, setDisplayName] = useState(
    user?.displayName || user?.username || "",
  );
  const [email, setEmail] = useState(user?.email || "");
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [notifications, setNotifications] = useState({
    sessionComplete: true,
    errors: true,
    updates: false,
  });

  const tabs = [
    { id: "profile" as const, label: "Profile", icon: User },
    { id: "api-keys" as const, label: "API Keys", icon: Key },
    { id: "notifications" as const, label: "Notifications", icon: Bell },
    { id: "appearance" as const, label: "Appearance", icon: Palette },
    { id: "security" as const, label: "Security", icon: Shield },
  ];

  const handleSave = async () => {
    setIsSaving(true);
    setSaveSuccess(false);
    try {
      await new Promise((r) => setTimeout(r, 500));
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      data-testid="settings-document"
      className={cn(
        "flex flex-col h-full",
        "bg-gray-50 dark:bg-gray-900",
        compact && "text-sm",
        className,
      )}
    >
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Settings
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Manage your account and preferences
            </p>
          </div>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
          >
            {saveSuccess ? (
              <>
                <Check size={16} />
                Saved
              </>
            ) : isSaving ? (
              <>
                <Save size={16} className="animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save size={16} />
                Save
              </>
            )}
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-48 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-3">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 text-sm rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
                }`}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-xl">
            {/* Profile Tab */}
            {activeTab === "profile" && (
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Default Persona
                  </label>
                  <select
                    value={persona}
                    onChange={(e) => {
                      dispatch(setPersona(e.target.value as Persona));
                    }}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    <option value="user">User</option>
                    <option value="developer">Developer</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
            )}

            {/* API Keys Tab */}
            {activeTab === "api-keys" && (
              <div className="space-y-5">
                <div className="p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
                  <p className="text-sm text-warning-800 dark:text-warning-200">
                    API keys provide access to your account. Keep them secure.
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Your API Key
                  </label>
                  <div className="flex gap-2">
                    <input
                      type={showApiKey ? "text" : "password"}
                      value="sk-mcp-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      readOnly
                      className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm"
                    />
                    <button
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
                    >
                      {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <button className="px-4 py-2 bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200 dark:hover:bg-error-900/50">
                  Regenerate API Key
                </button>
              </div>
            )}

            {/* Notifications Tab */}
            {activeTab === "notifications" && (
              <div className="space-y-4">
                {Object.entries(notifications).map(([key, enabled]) => (
                  <label
                    key={key}
                    className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div>
                      <p className="font-medium text-gray-900 dark:text-gray-100">
                        {key === "sessionComplete" && "Session Complete"}
                        {key === "errors" && "Error Alerts"}
                        {key === "updates" && "Product Updates"}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {key === "sessionComplete" &&
                          "Get notified when sessions finish"}
                        {key === "errors" && "Receive alerts for errors"}
                        {key === "updates" &&
                          "Stay informed about new features"}
                      </p>
                    </div>
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) =>
                        setNotifications({
                          ...notifications,
                          [key]: e.target.checked,
                        })
                      }
                      className="w-5 h-5 text-primary-600 rounded"
                    />
                  </label>
                ))}
              </div>
            )}

            {/* Appearance Tab */}
            {activeTab === "appearance" && (
              <div className="space-y-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
                  Theme
                </label>
                <div className="grid grid-cols-3 gap-4">
                  {(["light", "dark", "system"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setTheme(t)}
                      className={`p-4 rounded-lg border-2 transition-colors ${
                        theme === t
                          ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
                          : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:border-gray-600"
                      }`}
                    >
                      <div className="text-center">
                        <Palette size={24} className="mx-auto mb-2" />
                        <span className="capitalize text-sm">{t}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Security Tab */}
            {activeTab === "security" && (
              <div className="space-y-5">
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                    Two-Factor Authentication
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Add an extra layer of security to your account
                  </p>
                  <button className="px-4 py-2 bg-success-600 text-white rounded-lg hover:bg-success-700">
                    Enable 2FA
                  </button>
                </div>
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
                    Active Sessions
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Manage devices logged in to your account
                  </p>
                  <button className="px-4 py-2 bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200">
                    Sign Out All Devices
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default SettingsDocument;
