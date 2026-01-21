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
  Wrench,
} from "lucide-react";
import { AuditEventPanel } from "../components/Settings/AuditEventPanel";
import { ThemeSettings } from "../components/Settings/ThemeSettings";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import { useToolPreference } from "../contexts/PreferencesContext";

// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "@/components/UI/Button";
import { Input } from "@/components/UI/Input";
import { Select } from "@/components/UI/Select";

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

  // v7: Tool preference persistence
  const { toolPreference, setToolPreference } = useToolPreference();

  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Form state
  const [displayName, setDisplayName] = useState(
    user?.displayName || user?.username || "",
  );
  const [email, setEmail] = useState(user?.email || "");
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
    <div className="h-screen flex flex-col bg-neutral-1">
      {/* Header */}
      <header className="px-6 py-4 bg-neutral-2 border-b border-neutral-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-12">
              Settings
            </h1>
            <p className="text-sm text-neutral-11">
              Manage your account and preferences
            </p>
          </div>
          <Button
            variant="primary"
            className="gap-2"
            onClick={handleSave}
            disabled={isSaving}
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
          </Button>
        </div>
      </header>
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-neutral-2 border-r border-neutral-6 p-4">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                variant="ghost"
                onClick={() => setActiveTab(tab.id)}
                className={`w-full justify-start gap-2 px-4 py-2 ${
                  activeTab === tab.id
                    ? "bg-primary-3 text-primary-11 dark:bg-primary-4 dark:text-primary-9"
                    : "text-neutral-11 hover:bg-neutral-3"
                }`}
              >
                <tab.icon size={20} />
                {tab.label}
              </Button>
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
                  <label className="block text-sm font-medium text-neutral-11 mb-2">
                    Display Name
                  </label>
                  <Input
                    size="lg"
                    className="px-4 py-2 text-neutral-12"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-11 mb-2">
                    Email
                  </label>
                  <Input
                    size="lg"
                    className="px-4 py-2 text-neutral-12"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-11 mb-2">
                    Default Persona
                  </label>
                  <Select
                    size="lg"
                    className="px-4 py-2 text-neutral-12"
                    value={persona}
                    onChange={(e) => {
                      dispatch(setPersona(e.target.value as Persona));
                    }}
                  >
                    <option value="user">User</option>
                    <option value="developer">Developer</option>
                    <option value="admin">Admin</option>
                  </Select>
                </div>

                {/* v7: Tool Preference Setting */}
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <div className="flex items-start gap-3">
                    <Wrench
                      size={24}
                      className="text-neutral-11 flex-shrink-0 mt-0.5"
                    />
                    <div className="flex-1">
                      <h3 className="font-medium text-neutral-12 mb-1">
                        Tool Execution Preference
                      </h3>
                      <p className="text-sm text-neutral-11 mb-4">
                        Choose how tools are executed. Native tools use the LLM
                        provider&apos;s built-in capabilities (e.g., Anthropic web
                        search). Built-in tools use the server&apos;s implementations.
                      </p>
                      <Select
                        size="lg"
                        className="px-4 py-2 text-neutral-12"
                        value={toolPreference}
                        onChange={(e) => {
                          setToolPreference(
                            e.target.value as "auto" | "native" | "builtin" | "mcp"
                          );
                        }}
                        aria-label="Tool execution preference"
                      >
                        <option value="auto">Auto (Prefer Native when available)</option>
                        <option value="native">Native Only (LLM provider tools)</option>
                        <option value="builtin">Built-in Only (Server tools)</option>
                        <option value="mcp">MCP Only (External servers)</option>
                      </Select>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* API Keys Tab */}
            {activeTab === "api-keys" && (
              <div className="space-y-6">
                <div className="p-4 bg-warning-3 border border-warning-6 rounded-lg">
                  <p className="text-sm text-warning-11">
                    API keys provide access to your account. Keep them secure
                    and never share them publicly.
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-11 mb-2">
                    Your API Key
                  </label>
                  <div className="flex gap-2">
                    <Input
                      size="lg"
                      className="flex-1 px-4 py-2 bg-neutral-1 text-neutral-12 font-mono"
                      type={showApiKey ? "text" : "password"}
                      value="sk-mcp-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      readOnly
                    />
                    <Button
                      variant="secondary"
                      className="px-4 py-2 border border-neutral-6 rounded-lg hover:bg-neutral-21 dark:hover:bg-neutral-10"
                      onClick={() => setShowApiKey(!showApiKey)}
                    >
                      {showApiKey ? <EyeOff size={20} /> : <Eye size={20} />}
                    </Button>
                  </div>
                </div>
                <Button
                  variant="danger"
                  className="px-4 py-2 bg-error-3 text-error-11 bg-error-4 rounded-lg hover:bg-error-4 dark:hover:bg-error-12/50"
                >
                  Regenerate API Key
                </Button>
              </div>
            )}

            {/* Notifications Tab */}
            {activeTab === "notifications" && (
              <div data-testid="notifications-settings" className="space-y-6">
                {/* Push Notifications Section */}
                <div
                  data-testid="push-notifications-section"
                  className="p-4 bg-neutral-2 rounded-lg border border-neutral-6"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <BellRing className="h-5 w-5 text-primary-9" />
                    <h3 className="font-medium text-neutral-12">
                      Push Notifications
                    </h3>
                  </div>
                  <p className="text-sm text-neutral-11 mb-4">
                    Receive real-time notifications even when the app is closed.
                  </p>

                  {!isPushSupported ? (
                    <div className="flex items-center gap-2 text-warning-9">
                      <BellOff className="h-4 w-4" />
                      <span className="text-sm">
                        Push notifications are not supported in this browser.
                      </span>
                    </div>
                  ) : pushPermission === "denied" ? (
                    <div className="flex items-center gap-2 text-error-10">
                      <AlertCircle className="h-4 w-4" />
                      <span className="text-sm">
                        Notifications are blocked. Please enable them in your
                        browser settings.
                      </span>
                    </div>
                  ) : isPushSubscribed ? (
                    <Button
                      variant="danger"
                      className="flex px-4 py-2 bg-error-3 text-error-11 bg-error-4 rounded-lg hover:bg-error-4 dark:hover:bg-error-12/50"
                      data-testid="push-notifications-toggle"
                      onClick={unsubscribePush}
                      disabled={isPushLoading}
                      aria-label="Disable push notifications"
                    >
                      <BellOff className="h-4 w-4" />
                      {isPushLoading
                        ? "Disabling..."
                        : "Disable Push Notifications"}
                    </Button>
                  ) : (
                    <Button
                      variant="primary"
                      className="gap-2"
                      data-testid="push-notifications-toggle"
                      onClick={subscribePush}
                      disabled={isPushLoading}
                      aria-label="Enable push notifications"
                    >
                      <Bell className="h-4 w-4" />
                      {isPushLoading
                        ? "Enabling..."
                        : "Enable Push Notifications"}
                    </Button>
                  )}
                </div>

                {/* Real-Time Notification Preferences (API-backed) */}
                <NotificationPreferencesSettings />
              </div>
            )}

            {/* Appearance Tab */}
            {activeTab === "appearance" && (
              <div className="space-y-6">
                {/* Full Theme Settings Component with color themes */}
                <ThemeSettings />

                {/* Panel Layout Section (Sprint 1.2) */}
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <div className="flex items-start gap-3">
                    <LayoutGrid
                      size={24}
                      className="text-neutral-11 flex-shrink-0 mt-0.5"
                    />
                    <div className="flex-1">
                      <h3 className="font-medium text-neutral-12 mb-1">
                        Panel Layout
                      </h3>
                      <p className="text-sm text-neutral-11 mb-4">
                        Restore your panel layout to the default configuration
                        for your current persona. This will reset session nav,
                        conversation, and canvas panel sizes.
                      </p>
                      <Button
                        variant="secondary"
                        className="flex px-4 py-2 bg-neutral-3 text-neutral-11 rounded-lg hover:bg-neutral-30 dark:hover:bg-neutral-9"
                        type="button"
                        onClick={() => dispatch(resetToDefaults())}
                      >
                        <RotateCcw size={16} />
                        Reset to Persona Defaults
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Security Tab */}
            {activeTab === "security" && (
              <div className="space-y-6">
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="font-medium text-neutral-12 mb-2">
                    Two-Factor Authentication
                  </h3>
                  <p className="text-sm text-neutral-11 mb-4">
                    Add an extra layer of security to your account
                  </p>
                  <Button
                    variant="success"
                  >
                    Enable 2FA
                  </Button>
                </div>
                <div className="p-4 bg-neutral-2 rounded-lg border border-neutral-6">
                  <h3 className="font-medium text-neutral-12 mb-2">
                    Active Sessions
                  </h3>
                  <p className="text-sm text-neutral-11 mb-4">
                    Manage devices that are logged in to your account
                  </p>
                  <Button
                    variant="danger"
                    className="px-4 py-2 bg-error-3 text-error-11 bg-error-4 rounded-lg hover:bg-error-4"
                  >
                    Sign Out All Devices
                  </Button>
                </div>
              </div>
            )}

            {/* Audit Log Tab (Admin Only) */}
            {activeTab === "audit-log" && isAdmin && (
              <div className="space-y-6">
                <div className="p-4 bg-insight-1 border border-insight-4 rounded-lg">
                  <p className="text-sm text-insight-11">
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
                <div className="p-4 bg-primary-1/20 border border-primary-4 rounded-lg">
                  <p className="text-sm text-primary-11">
                    As an administrator, you can manage API keys for all users
                    in the system.
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-medium text-neutral-12">
                    User API Keys
                  </h3>
                  <Button
                    variant="ghost"
                    className="flex px-3 py-1.5 text-sm text-neutral-11 hover:text-neutral-12 dark:hover:text-neutral-2"
                    onClick={loadManagedUsers}>
                    <RefreshCw
                      size={16}
                      className={isLoadingUsers ? "animate-spin" : ""}
                    />
                    Refresh
                  </Button>
                </div>

                {/* Error banner for admin operations */}
                {adminError && !isLoadingUsers && (
                  <div
                    role="alert"
                    className="p-4 bg-error-1/20 border border-error-4 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <AlertCircle size={20} className="text-error-9" />
                      <p className="text-sm text-error-11">
                        {adminError}
                      </p>
                    </div>
                    <Button
                      variant="danger"
                      className="mt-3 flex px-3 py-1.5 text-sm bg-error-3 text-error-11 bg-error-4 rounded-lg hover:bg-error-4"
                      onClick={loadManagedUsers}
                    >
                      <RefreshCw size={14} />
                      Retry
                    </Button>
                  </div>
                )}

                {/* Search input */}
                {!isLoadingUsers && managedUsers.length > 0 && (
                  <div className="relative">
                    <Search
                      size={16}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-6"
                    />
                    <Input
                      className="pl-9 pr-4 py-2 text-neutral-12"
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                      placeholder="Search users by email..."
                    />
                  </div>
                )}

                {isLoadingUsers ? (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw
                      size={24}
                      className="animate-spin text-primary-9"
                    />
                  </div>
                ) : adminError &&
                  managedUsers.length ===
                    0 ? null /* Error banner is shown above */ : managedUsers.length ===
                  0 ? (
                  <div className="text-center py-8 text-neutral-11">
                    No users found
                  </div>
                ) : filteredManagedUsers.length === 0 ? (
                  <div className="text-center py-8 text-neutral-11">
                    No users match your search
                  </div>
                ) : (
                  <div className="space-y-2">
                    {filteredManagedUsers.map((managedUser) => (
                      <div
                        key={managedUser.id}
                        className="flex items-center justify-between p-4 bg-neutral-2 rounded-lg border border-neutral-6"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 bg-neutral-3 rounded-full flex items-center justify-center">
                            <User
                              size={20}
                              className="text-neutral-11"
                            />
                          </div>
                          <div>
                            <p className="font-medium text-neutral-12">
                              {managedUser.email}
                            </p>
                            <p className="text-sm text-neutral-11">
                              {managedUser.hasApiKey
                                ? "Has API Key"
                                : "No API Key"}
                            </p>
                          </div>
                        </div>
                        <div>
                          {managedUser.hasApiKey ? (
                            <Button
                              variant="danger"
                              className="flex px-3 py-1.5 text-sm bg-error-3 text-error-11 bg-error-4 rounded-lg hover:bg-error-4"
                              onClick={() => handleRevokeKey(managedUser.id)}
                              aria-label="Revoke"
                            >
                              <Trash2 size={14} />
                              Revoke
                            </Button>
                          ) : (
                            <Button
                              variant="success"
                              className="flex px-3 py-1.5 text-sm bg-success-3 text-success-11 bg-success-4 rounded-lg hover:bg-success-4"
                              onClick={() => handleGenerateKey(managedUser.id)}
                              aria-label="Generate"
                            >
                              <Plus size={14} />
                              Generate
                            </Button>
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
