/**
 * NotificationPreferencesSettings Tests
 *
 * TDD tests for notification preferences settings component.
 * Tests for:
 * - Loading and displaying current preferences
 * - Toggling individual notification types
 * - Saving preferences
 * - Reset to defaults
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { NotificationPreferencesSettings } from "./NotificationPreferencesSettings";
import { api } from "../../api";

// Create mock functions
const mockUseGetNotificationPreferencesQuery = vi.fn();
const mockUseUpdateNotificationPreferencesMutation = vi.fn();
const mockUseResetNotificationPreferencesMutation = vi.fn();

// Mock the API hooks
vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetNotificationPreferencesQuery: () =>
      mockUseGetNotificationPreferencesQuery(),
    useUpdateNotificationPreferencesMutation: () =>
      mockUseUpdateNotificationPreferencesMutation(),
    useResetNotificationPreferencesMutation: () =>
      mockUseResetNotificationPreferencesMutation(),
  };
});

const createMockStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const renderWithProvider = (component: React.ReactNode) => {
  const store = createMockStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("NotificationPreferencesSettings", () => {
  const mockPreferences = {
    user_id: "user:alice",
    info_enabled: true,
    success_enabled: true,
    warning_enabled: true,
    error_enabled: true,
  };

  const mockUpdateMutation = vi
    .fn()
    .mockResolvedValue({ data: mockPreferences });
  const mockResetMutation = vi
    .fn()
    .mockResolvedValue({ data: mockPreferences });
  const mockRefetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default mocks for mutations
    mockUseUpdateNotificationPreferencesMutation.mockReturnValue([
      mockUpdateMutation,
      { isLoading: false },
    ]);
    mockUseResetNotificationPreferencesMutation.mockReturnValue([
      mockResetMutation,
      { isLoading: false },
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("loading state", () => {
    it("shows loading spinner while fetching preferences", () => {
      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      expect(screen.getByTestId("preferences-loading")).toBeInTheDocument();
    });
  });

  describe("displaying preferences", () => {
    it("displays all notification type toggles", () => {
      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: mockPreferences,
        isLoading: false,
        isError: false,
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      expect(screen.getByText("Info Notifications")).toBeInTheDocument();
      expect(screen.getByText("Success Notifications")).toBeInTheDocument();
      expect(screen.getByText("Warning Notifications")).toBeInTheDocument();
      expect(screen.getByText("Error Notifications")).toBeInTheDocument();
    });

    it("shows correct toggle states from preferences", () => {
      const customPreferences = {
        ...mockPreferences,
        info_enabled: false,
        success_enabled: true,
      };

      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: customPreferences,
        isLoading: false,
        isError: false,
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      const infoToggle = screen.getByRole("switch", {
        name: /info notifications/i,
      });
      const successToggle = screen.getByRole("switch", {
        name: /success notifications/i,
      });

      expect(infoToggle).not.toBeChecked();
      expect(successToggle).toBeChecked();
    });
  });

  describe("updating preferences", () => {
    it("calls update mutation when toggling a preference", async () => {
      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: mockPreferences,
        isLoading: false,
        isError: false,
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      const infoToggle = screen.getByRole("switch", {
        name: /info notifications/i,
      });
      fireEvent.click(infoToggle);

      await waitFor(() => {
        expect(mockUpdateMutation).toHaveBeenCalledWith({
          info_enabled: false,
        });
      });
    });
  });

  describe("resetting preferences", () => {
    it("calls reset mutation when clicking reset button", async () => {
      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: { ...mockPreferences, info_enabled: false },
        isLoading: false,
        isError: false,
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      const resetButton = screen.getByRole("button", {
        name: /reset to defaults/i,
      });
      fireEvent.click(resetButton);

      await waitFor(() => {
        expect(mockResetMutation).toHaveBeenCalled();
      });
    });
  });

  describe("error handling", () => {
    it("displays error message when loading fails", () => {
      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Failed to load preferences" },
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });

    it("provides retry button on error", () => {
      mockUseGetNotificationPreferencesQuery.mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: { message: "Failed to load preferences" },
        refetch: mockRefetch,
      });

      renderWithProvider(<NotificationPreferencesSettings />);

      const retryButton = screen.getByRole("button", { name: /retry/i });
      fireEvent.click(retryButton);

      expect(mockRefetch).toHaveBeenCalled();
    });
  });
});
