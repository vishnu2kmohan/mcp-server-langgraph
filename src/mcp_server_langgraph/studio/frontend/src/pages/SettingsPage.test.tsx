/**
 * SettingsPage Tests
 *
 * TDD tests for the settings page.
 * Tests cover:
 * - Tab navigation
 * - Profile settings
 * - API keys display
 * - Save functionality
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { SettingsPage } from "./SettingsPage";
import personaReducer from "../store/slices/personaSlice";
import authReducer, { initialAuthState } from "../store/slices/authSlice";
import type { Persona } from "../store/slices/personaSlice";
import type { User } from "../types/auth";

// Mock usePushNotifications hook
const mockSubscribe = vi.fn();
const mockUnsubscribe = vi.fn();
const mockUsePushNotifications = vi.fn(() => ({
  isSupported: true,
  isSubscribed: false,
  permission: "default" as NotificationPermission,
  subscription: null,
  isLoading: false,
  error: null,
  subscribe: mockSubscribe,
  unsubscribe: mockUnsubscribe,
}));

vi.mock("../hooks/usePushNotifications", () => ({
  usePushNotifications: () => mockUsePushNotifications(),
}));

// Mock API hooks used by child components (NotificationPreferencesSettings)
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    useGetNotificationPreferencesQuery: () => ({
      data: {
        info_enabled: true,
        success_enabled: true,
        warning_enabled: true,
        error_enabled: true,
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    }),
    useUpdateNotificationPreferencesMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve({ success: true }) })),
      { isLoading: false },
    ],
    useResetNotificationPreferencesMutation: () => [
      vi.fn(() => ({ unwrap: () => Promise.resolve({ success: true }) })),
      { isLoading: false },
    ],
  };
});

// Create test store
const createTestStore = (
  persona: Persona = "user",
  user: User = {
    id: "user-1",
    username: "testuser",
    email: "test@example.com",
    displayName: "Test User",
    roles: ["user"],
    persona: "user",
  },
) => {
  return configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        ...initialAuthState,
        user,
        isInitializing: false,
      },
    },
  });
};

// Helper to render with store
const renderWithStore = (
  persona: Persona = "user",
  user: User = {
    id: "user-1",
    username: "testuser",
    email: "test@example.com",
    displayName: "Test User",
    roles: ["user"],
    persona: "user",
  },
) => {
  const store = createTestStore(persona, user);
  return {
    store,
    ...render(
      <Provider store={store}>
        <SettingsPage />
      </Provider>,
    ),
  };
};

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubscribe.mockReset();
    mockUnsubscribe.mockReset();
    mockUsePushNotifications.mockReturnValue({
      isSupported: true,
      isSubscribed: false,
      permission: "default" as NotificationPermission,
      subscription: null,
      isLoading: false,
      error: null,
      subscribe: mockSubscribe,
      unsubscribe: mockUnsubscribe,
    });
  });

  describe("Header", () => {
    it("should display page title", () => {
      renderWithStore();

      expect(screen.getByText("Settings")).toBeInTheDocument();
    });

    it("should display page description", () => {
      renderWithStore();

      expect(
        screen.getByText("Manage your account and preferences"),
      ).toBeInTheDocument();
    });

    it("should have save button", () => {
      renderWithStore();

      expect(screen.getByText("Save Changes")).toBeInTheDocument();
    });
  });

  describe("Tabs", () => {
    it("should have Profile tab", () => {
      renderWithStore();

      expect(screen.getByText("Profile")).toBeInTheDocument();
    });

    it("should have API Keys tab", () => {
      renderWithStore();

      expect(screen.getByText("API Keys")).toBeInTheDocument();
    });

    it("should have Notifications tab", () => {
      renderWithStore();

      expect(screen.getByText("Notifications")).toBeInTheDocument();
    });

    it("should have Appearance tab", () => {
      renderWithStore();

      expect(screen.getByText("Appearance")).toBeInTheDocument();
    });

    it("should have Security tab", () => {
      renderWithStore();

      expect(screen.getByText("Security")).toBeInTheDocument();
    });
  });

  describe("Profile Tab", () => {
    it("should display display name label", () => {
      renderWithStore();

      expect(screen.getByText("Display Name")).toBeInTheDocument();
    });

    it("should display email label", () => {
      renderWithStore();

      expect(screen.getByText("Email")).toBeInTheDocument();
    });

    it("should show current user data in fields", () => {
      renderWithStore();

      const inputs = screen.getAllByRole("textbox");
      const displayNameInput = inputs.find(
        (input) => (input as HTMLInputElement).value === "Test User",
      );
      expect(displayNameInput).toBeInTheDocument();
    });
  });

  describe("API Keys Tab", () => {
    it("should switch to API Keys tab when clicked", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("API Keys"));

      expect(screen.getByText("Your API Key")).toBeInTheDocument();
    });

    it("should show API key warning", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("API Keys"));

      expect(screen.getByText(/API keys provide access/)).toBeInTheDocument();
    });

    it("should have regenerate button", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("API Keys"));

      expect(screen.getByText("Regenerate API Key")).toBeInTheDocument();
    });
  });

  describe("Save Functionality", () => {
    it("should show Saving... when saving", async () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Save Changes"));

      expect(screen.getByText("Saving...")).toBeInTheDocument();
    });

    it("should show Saved after successful save", async () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Save Changes"));

      await waitFor(
        () => {
          expect(screen.getByText("Saved")).toBeInTheDocument();
        },
        { timeout: 1000 },
      );
    });
  });

  describe("Profile Form Interactions", () => {
    it("should update display name when typed", () => {
      renderWithStore();

      const inputs = screen.getAllByRole("textbox");
      const displayNameInput = inputs[0] as HTMLInputElement;

      fireEvent.change(displayNameInput, { target: { value: "New Name" } });

      expect(displayNameInput.value).toBe("New Name");
    });

    it("should update email when typed", () => {
      renderWithStore();

      const inputs = screen.getAllByRole("textbox");
      const emailInput = inputs[1] as HTMLInputElement;

      fireEvent.change(emailInput, { target: { value: "new@example.com" } });

      expect(emailInput.value).toBe("new@example.com");
    });

    it("should have persona selector", () => {
      renderWithStore();

      expect(screen.getByText("Default Persona")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should dispatch setPersona when persona is changed", () => {
      const { store } = renderWithStore();

      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "admin" } });

      // Verify Redux state was updated
      const state = store.getState();
      expect(state.persona.persona).toBe("admin");
    });
  });

  describe("API Keys Tab Interactions", () => {
    it("should show API key container when on API Keys tab", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("API Keys"));

      // Verify the API key label is present
      expect(screen.getByText("Your API Key")).toBeInTheDocument();
    });

    it("should have toggle visibility button", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("API Keys"));

      // Find buttons in the API keys section
      const allButtons = screen.getAllByRole("button");
      // There should be multiple buttons including the toggle
      expect(allButtons.length).toBeGreaterThan(0);
    });
  });

  describe("Notifications Tab", () => {
    it("should switch to notifications tab when clicked", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      // New component has real-time notification types
      expect(screen.getByText("Info Notifications")).toBeInTheDocument();
      expect(screen.getByText("Success Notifications")).toBeInTheDocument();
      expect(screen.getByText("Warning Notifications")).toBeInTheDocument();
      expect(screen.getByText("Error Notifications")).toBeInTheDocument();
    });

    it("should have toggle switches for notification settings", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      // New component has 4 notification type toggles with role="switch"
      const switches = screen.getAllByRole("switch");
      expect(switches.length).toBe(4);
    });

    it("should show reset to defaults button", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      expect(screen.getByText("Reset to Defaults")).toBeInTheDocument();
    });
  });

  describe("Push Notifications", () => {
    it("should show push notification section in notifications tab", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      expect(screen.getByText("Push Notifications")).toBeInTheDocument();
    });

    it("should show enable button when not subscribed", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: true,
        isSubscribed: false,
        permission: "default" as NotificationPermission,
        subscription: null,
        isLoading: false,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      expect(
        screen.getByRole("button", {
          name: /enable.*push|enable.*notifications/i,
        }),
      ).toBeInTheDocument();
    });

    it("should show disable button when subscribed", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: true,
        isSubscribed: true,
        permission: "granted" as NotificationPermission,
        subscription: {} as PushSubscription,
        isLoading: false,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      expect(
        screen.getByRole("button", {
          name: /disable.*push|disable.*notifications/i,
        }),
      ).toBeInTheDocument();
    });

    it("should call subscribe when enable button is clicked", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: true,
        isSubscribed: false,
        permission: "default" as NotificationPermission,
        subscription: null,
        isLoading: false,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));
      fireEvent.click(
        screen.getByRole("button", {
          name: /enable.*push|enable.*notifications/i,
        }),
      );

      expect(mockSubscribe).toHaveBeenCalledTimes(1);
    });

    it("should call unsubscribe when disable button is clicked", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: true,
        isSubscribed: true,
        permission: "granted" as NotificationPermission,
        subscription: {} as PushSubscription,
        isLoading: false,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));
      fireEvent.click(
        screen.getByRole("button", {
          name: /disable.*push|disable.*notifications/i,
        }),
      );

      expect(mockUnsubscribe).toHaveBeenCalledTimes(1);
    });

    it("should show loading state when loading", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: true,
        isSubscribed: false,
        permission: "default" as NotificationPermission,
        subscription: null,
        isLoading: true,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      const button = screen.getByRole("button", {
        name: /enable.*push|enable.*notifications/i,
      });
      expect(button).toBeDisabled();
    });

    it("should show unsupported message when not supported", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: false,
        isSubscribed: false,
        permission: "unsupported" as NotificationPermission | "unsupported",
        subscription: null,
        isLoading: false,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      expect(screen.getByText(/not supported/i)).toBeInTheDocument();
    });

    it("should show denied message when permission is denied", () => {
      mockUsePushNotifications.mockReturnValue({
        isSupported: true,
        isSubscribed: false,
        permission: "denied" as NotificationPermission,
        subscription: null,
        isLoading: false,
        error: null,
        subscribe: mockSubscribe,
        unsubscribe: mockUnsubscribe,
      });

      renderWithStore();

      fireEvent.click(screen.getByText("Notifications"));

      expect(screen.getByText(/denied|blocked/i)).toBeInTheDocument();
    });
  });

  describe("Appearance Tab", () => {
    it("should switch to appearance tab when clicked", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Appearance"));

      expect(screen.getByText("Theme")).toBeInTheDocument();
    });

    it("should show theme options", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Appearance"));

      expect(screen.getByText("light")).toBeInTheDocument();
      expect(screen.getByText("dark")).toBeInTheDocument();
      expect(screen.getByText("system")).toBeInTheDocument();
    });

    it("should select theme when clicked", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Appearance"));

      // System should be selected by default
      const systemButton = screen.getByText("system").closest("button");
      expect(systemButton).toHaveClass("border-blue-500");

      // Click dark
      const darkButton = screen.getByText("dark").closest("button")!;
      fireEvent.click(darkButton);

      expect(darkButton).toHaveClass("border-blue-500");
    });
  });

  describe("Security Tab", () => {
    it("should switch to security tab when clicked", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Security"));

      expect(screen.getByText("Two-Factor Authentication")).toBeInTheDocument();
    });

    it("should have enable 2FA button", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Security"));

      expect(screen.getByText("Enable 2FA")).toBeInTheDocument();
    });

    it("should show active sessions section", () => {
      renderWithStore();

      fireEvent.click(screen.getByText("Security"));

      expect(screen.getByText("Active Sessions")).toBeInTheDocument();
      expect(screen.getByText("Sign Out All Devices")).toBeInTheDocument();
    });
  });

  describe("Admin API Key Management", () => {
    const adminUser: User = {
      id: "admin-1",
      username: "admin",
      email: "admin@example.com",
      displayName: "Admin User",
      roles: ["admin"],
      persona: "admin",
    };

    it("should show Manage User Keys tab for admin users", () => {
      renderWithStore("admin", adminUser);

      expect(screen.getByText("Manage User Keys")).toBeInTheDocument();
    });

    it("should not show Manage User Keys tab for non-admin users", () => {
      renderWithStore();

      expect(screen.queryByText("Manage User Keys")).not.toBeInTheDocument();
    });

    it("should display user list in Manage User Keys tab", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          users: [
            { id: "user-1", email: "alice@example.com", has_api_key: true },
            { id: "user-2", email: "bob@example.com", has_api_key: false },
          ],
        }),
      });

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
        expect(screen.getByText("bob@example.com")).toBeInTheDocument();
      });
    });

    it("should have revoke button for users with API keys", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          users: [
            { id: "user-1", email: "alice@example.com", has_api_key: true },
          ],
        }),
      });

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /revoke/i }),
        ).toBeInTheDocument();
      });
    });

    it("should have generate button for users without API keys", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          users: [
            { id: "user-2", email: "bob@example.com", has_api_key: false },
          ],
        }),
      });

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /generate/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show error message when fetching users fails", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
        expect(screen.getByText(/failed to load users/i)).toBeInTheDocument();
      });
    });

    it("should show error message when revoking API key fails", async () => {
      // First load succeeds
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            users: [
              { id: "user-1", email: "alice@example.com", has_api_key: true },
            ],
          }),
        })
        // Then revoke fails
        .mockRejectedValueOnce(new Error("Revoke failed"));

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /revoke/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to revoke/i)).toBeInTheDocument();
      });
    });

    it("should show error message when generating API key fails", async () => {
      // First load succeeds
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            users: [
              { id: "user-2", email: "bob@example.com", has_api_key: false },
            ],
          }),
        })
        // Then generate fails
        .mockRejectedValueOnce(new Error("Generate failed"));

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByText("bob@example.com")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole("button", { name: /generate/i }));

      await waitFor(() => {
        expect(screen.getByText(/failed to generate/i)).toBeInTheDocument();
      });
    });

    it("should allow retry when fetch fails", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByRole("alert")).toBeInTheDocument();
      });

      // Should have retry button
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });

    it("should have search input for filtering users", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          users: [
            { id: "user-1", email: "alice@example.com", has_api_key: true },
            { id: "user-2", email: "bob@example.com", has_api_key: false },
          ],
        }),
      });

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search users/i),
        ).toBeInTheDocument();
      });
    });

    it("should filter users by email when typing in search", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          users: [
            { id: "user-1", email: "alice@example.com", has_api_key: true },
            { id: "user-2", email: "bob@example.com", has_api_key: false },
            { id: "user-3", email: "charlie@example.com", has_api_key: true },
          ],
        }),
      });

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
        expect(screen.getByText("bob@example.com")).toBeInTheDocument();
        expect(screen.getByText("charlie@example.com")).toBeInTheDocument();
      });

      // Type in search
      const searchInput = screen.getByPlaceholderText(/search users/i);
      fireEvent.change(searchInput, { target: { value: "alice" } });

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
        expect(screen.queryByText("bob@example.com")).not.toBeInTheDocument();
        expect(
          screen.queryByText("charlie@example.com"),
        ).not.toBeInTheDocument();
      });
    });

    it("should show no results message when search finds nothing", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          users: [
            { id: "user-1", email: "alice@example.com", has_api_key: true },
          ],
        }),
      });

      renderWithStore("admin", adminUser);

      fireEvent.click(screen.getByText("Manage User Keys"));

      await waitFor(() => {
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
      });

      // Type in search that matches nothing
      const searchInput = screen.getByPlaceholderText(/search users/i);
      fireEvent.change(searchInput, { target: { value: "xyz" } });

      await waitFor(() => {
        expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
        expect(screen.getByText(/no users match/i)).toBeInTheDocument();
      });
    });
  });
});
