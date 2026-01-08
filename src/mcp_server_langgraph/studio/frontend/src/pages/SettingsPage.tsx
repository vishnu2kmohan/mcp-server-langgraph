/**
 * SettingsPage
 *
 * User settings page for configuring preferences,
 * API keys, and application behavior.
 */

import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { selectUser } from "../store/slices/authSlice";
import { selectPersona, setPersona } from "../store/slices/personaSlice";
import { resetToDefaults } from "../store/slices/canvasSlice";
import type { Persona } from "../store/slices/personaSlice";
import { usePushNotifications } from "../hooks/usePushNotifications";
import { NotificationPreferencesSettings } from "../components/Settings/NotificationPreferencesSettings";
import {
  User,
  Key,
  Bell,
  BellRing,
  Palette,
  Shield,
  Save,
  Eye,
  EyeOff,
  Check,
  Users,
  Plus,
  Trash2,
  RefreshCw,
  AlertCircle,
  Search,
  BellOff,
  ScrollText,
  LayoutGrid,
  RotateCcw,
} from "lucide-react";
import { AuditEventPanel } from "../components/Settings/AuditEventPanel";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";

type SettingsTab =
  | "profile"
  | "api-keys"
  | "notifications"
  | "appearance"
  | "security"
  | "manage-keys"
  | "audit-log";

// camelCase per ADR-0091 Phase 6 (RTK Query transforms)
interface ManagedUser {
  id: string;
  email: string;
  hasApiKey: boolean;
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const [showApiKey, setShowApiKey] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const navigate = useNavigate();
  const user = useAppSelector(selectUser);
  const persona = useAppSelector(selectPersona);
  const dispatch = useAppDispatch();

  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Form state
  const [displayName, setDisplayName] = useState(
    user?.displayName || user?.username || "",
  );
  const [email, setEmail] = useState(user?.email || "");
  const [theme, setTheme] = useState<"light" | "dark" | "system">("system");
  const [_notifications, _setNotifications] = useState({
    sessionComplete: true,
    errors: true,
    updates: false,
  });

  // Push notifications
  const {
    isSupported: isPushSupported,
    isSubscribed: isPushSubscribed,
    permission: pushPermission,
    isLoading: isPushLoading,
    subscribe: subscribePush,
    unsubscribe: unsubscribePush,
  } = usePushNotifications();

  // Admin user management
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [userSearch, setUserSearch] = useState("");

  const isAdmin = persona === "admin";

  // Filter users by search query
  const filteredManagedUsers = managedUsers.filter((user) =>
    user.email.toLowerCase().includes(userSearch.toLowerCase()),
  );

  // Fetch users for admin key management
  const loadManagedUsers = useCallback(async () => {
    setIsLoadingUsers(true);
    setAdminError(null);
    try {
      const response = await authenticatedFetch("/api/v1/admin/users", {
        method: "GET",
        onAuthFailure: handleAuthFailure,
      });
      if (response.ok) {
        const data = await response.json();
        setManagedUsers(data.users || []);
      } else {
        setAdminError("Failed to load users");
      }
    } catch {
      setAdminError("Failed to load users");
    } finally {
      setIsLoadingUsers(false);
    }
  }, [handleAuthFailure]);

  useEffect(() => {
    if (isAdmin && activeTab === "manage-keys") {
      loadManagedUsers();
    }
  }, [isAdmin, activeTab, loadManagedUsers]);

  const handleRevokeKey = useCallback(
    async (userId: string) => {
      setAdminError(null);
      try {
        const response = await authenticatedFetch(
          `/api/v1/admin/users/${userId}/api-key`,
          {
            method: "DELETE",
            onAuthFailure: handleAuthFailure,
          },
        );
        if (!response.ok) {
          setAdminError("Failed to revoke API key");
          return;
        }
        await loadManagedUsers();
      } catch {
        setAdminError("Failed to revoke API key");
      }
    },
    [handleAuthFailure, loadManagedUsers],
  );

  const handleGenerateKey = useCallback(
    async (userId: string) => {
      setAdminError(null);
      try {
        const response = await authenticatedFetch(
          `/api/v1/admin/users/${userId}/api-key`,
          {
            method: "POST",
            onAuthFailure: handleAuthFailure,
          },
        );
        if (!response.ok) {
          setAdminError("Failed to generate API key");
          return;
        }
        await loadManagedUsers();
      } catch {
        setAdminError("Failed to generate API key");
      }
    },
    [handleAuthFailure, loadManagedUsers],
  );

  const baseTabs = [
    { id: "profile" as const, label: "Profile", icon: User },
    { id: "api-keys" as const, label: "API Keys", icon: Key },
    { id: "notifications" as const, label: "Notifications", icon: Bell },
    { id: "appearance" as const, label: "Appearance", icon: Palette },
    { id: "security" as const, label: "Security", icon: Shield },
  ];

  // Add admin-only tabs
  const tabs = isAdmin
    ? [
        ...baseTabs,
        { id: "manage-keys" as const, label: "Manage User Keys", icon: Users },
        { id: "audit-log" as const, label: "Audit Log", icon: ScrollText },
      ]
    : baseTabs;

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
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Settings
            </h1>
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
                Save Changes
              </>
            )}
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400"
                    : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
                }`}
              >
                <tab.icon size={20} />
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-2xl">
            {/* Profile Tab */}
            {activeTab === "profile" && (
              <div className="space-y-6">
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
              <div className="space-y-6">
                <div className="p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
                  <p className="text-sm text-warning-800 dark:text-warning-200">
                    API keys provide access to your account. Keep them secure
                    and never share them publicly.
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
                      className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono"
                    />
                    <button
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700"
                    >
                      {showApiKey ? <EyeOff size={20} /> : <Eye size={20} />}
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
              <div data-testid="notifications-settings" className="space-y-6">
                {/* Push Notifications Section */}
                <div
                  data-testid="push-notifications-section"
                  className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <BellRing className="h-5 w-5 text-primary-500" />
                    <h3 className="font-medium text-gray-900 dark:text-gray-100">
                      Push Notifications
                    </h3>
                  </div>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                    Receive real-time notifications even when the app is closed.
                  </p>

                  {!isPushSupported ? (
                    <div className="flex items-center gap-2 text-warning-600 dark:text-warning-400">
                      <BellOff className="h-4 w-4" />
                      <span className="text-sm">
                        Push notifications are not supported in this browser.
                      </span>
                    </div>
                  ) : pushPermission === "denied" ? (
                    <div className="flex items-center gap-2 text-error-600 dark:text-error-400">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm">
                        Notifications are blocked. Please enable them in your
                        browser settings.
                      </span>
                    </div>
                  ) : isPushSubscribed ? (
                    <button
                      data-testid="push-notifications-toggle"
                      onClick={unsubscribePush}
                      disabled={isPushLoading}
                      className="flex items-center gap-2 px-4 py-2 bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200 dark:hover:bg-error-900/50 disabled:opacity-50"
                      aria-label="Disable push notifications"
                    >
                      <BellOff className="h-4 w-4" />
                      {isPushLoading
                        ? "Disabling..."
                        : "Disable Push Notifications"}
                    </button>
                  ) : (
                    <button
                      data-testid="push-notifications-toggle"
                      onClick={subscribePush}
                      disabled={isPushLoading}
                      className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
                      aria-label="Enable push notifications"
                    >
                      <Bell className="h-4 w-4" />
                      {isPushLoading
                        ? "Enabling..."
                        : "Enable Push Notifications"}
                    </button>
                  )}
                </div>

                {/* Real-Time Notification Preferences (API-backed) */}
                <NotificationPreferencesSettings />
              </div>
            )}

            {/* Appearance Tab */}
            {activeTab === "appearance" && (
              <div className="space-y-6">
                <div>
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
                          <span className="capitalize">{t}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Panel Layout Section (Sprint 1.2) */}
                <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-start gap-3">
                    <LayoutGrid
                      size={24}
                      className="text-gray-500 dark:text-gray-400 flex-shrink-0 mt-0.5"
                    />
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-1">
                        Panel Layout
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        Restore your panel layout to the default configuration
                        for your current persona. This will reset session nav,
                        conversation, and canvas panel sizes.
                      </p>
                      <button
                        type="button"
                        onClick={() => dispatch(resetToDefaults())}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors"
                      >
                        <RotateCcw size={16} />
                        Reset to Persona Defaults
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Security Tab */}
            {activeTab === "security" && (
              <div className="space-y-6">
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
                    Manage devices that are logged in to your account
                  </p>
                  <button className="px-4 py-2 bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200">
                    Sign Out All Devices
                  </button>
                </div>
              </div>
            )}

            {/* Audit Log Tab (Admin Only) */}
            {activeTab === "audit-log" && isAdmin && (
              <div className="space-y-6">
                <div className="p-4 bg-insight-50 dark:bg-insight-900/20 border border-insight-200 dark:border-insight-800 rounded-lg">
                  <p className="text-sm text-insight-800 dark:text-insight-200">
                    Real-time audit event stream for compliance and security
                    monitoring.
                  </p>
                </div>
                <AuditEventPanel maxHeight="500px" />
              </div>
            )}

            {/* Manage User Keys Tab (Admin Only) */}
            {activeTab === "manage-keys" && isAdmin && (
              <div className="space-y-6">
                <div className="p-4 bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 rounded-lg">
                  <p className="text-sm text-primary-800 dark:text-primary-200">
                    As an administrator, you can manage API keys for all users
                    in the system.
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
                    User API Keys
                  </h3>
                  <button
                    onClick={loadManagedUsers}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                  >
                    <RefreshCw
                      size={16}
                      className={isLoadingUsers ? "animate-spin" : ""}
                    />
                    Refresh
                  </button>
                </div>

                {/* Error banner for admin operations */}
                {adminError && !isLoadingUsers && (
                  <div
                    role="alert"
                    className="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <AlertCircle size={20} className="text-error-500" />
                      <p className="text-sm text-error-700 dark:text-error-400">
                        {adminError}
                      </p>
                    </div>
                    <button
                      onClick={loadManagedUsers}
                      className="mt-3 flex items-center gap-2 px-3 py-1.5 text-sm bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200"
                    >
                      <RefreshCw size={14} />
                      Retry
                    </button>
                  </div>
                )}

                {/* Search input */}
                {!isLoadingUsers && managedUsers.length > 0 && (
                  <div className="relative">
                    <Search
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-400"
                    />
                    <input
                      type="text"
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Search users by email..."
                      className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                    />
                  </div>
                )}

                {isLoadingUsers ? (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw
                      size={24}
                      className="animate-spin text-primary-500"
                    />
                  </div>
                ) : adminError &&
                  managedUsers.length ===
                    0 ? null /* Error banner is shown above */ : managedUsers.length ===
                  0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No users found
                  </div>
                ) : filteredManagedUsers.length === 0 ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                    No users match your search
                  </div>
                ) : (
                  <div className="space-y-2">
                    {filteredManagedUsers.map((managedUser) => (
                      <div
                        key={managedUser.id}
                        className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                            <User
                              size={20}
                              className="text-gray-500 dark:text-gray-400"
                            />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 dark:text-gray-100">
                              {managedUser.email}
                            </p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {managedUser.hasApiKey
                                ? "Has API Key"
                                : "No API Key"}
                            </p>
                          </div>
                        </div>
                        <div>
                          {managedUser.hasApiKey ? (
                            <button
                              onClick={() => handleRevokeKey(managedUser.id)}
                              aria-label="Revoke"
                              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded-lg hover:bg-error-200"
                            >
                              <Trash2 size={14} />
                              Revoke
                            </button>
                          ) : (
                            <button
                              onClick={() => handleGenerateKey(managedUser.id)}
                              aria-label="Generate"
                              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400 rounded-lg hover:bg-success-200"
                            >
                              <Plus size={14} />
                              Generate
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

export default SettingsPage;
