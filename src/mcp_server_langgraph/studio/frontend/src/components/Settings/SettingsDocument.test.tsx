/**
 * SettingsDocument Component Tests
 *
 * TDD tests for the settings document component used in MainDock tabs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { SettingsDocument } from "./SettingsDocument";
import uiReducer from "../../store/slices/uiSlice";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";

// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: uiReducer,
      persona: personaReducer,
      auth: authReducer,
    },
  });
};

const renderWithProviders = (ui: React.ReactElement) => {
  const store = createTestStore();
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>,
    ),
  };
};

describe("SettingsDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<SettingsDocument />);
      expect(screen.getByTestId("settings-document")).toBeInTheDocument();
    });

    it("should display settings heading", () => {
      renderWithProviders(<SettingsDocument />);
      expect(
        screen.getByRole("heading", { name: /Settings/i }),
      ).toBeInTheDocument();
    });

    it("should apply compact mode styling when compact prop is true", () => {
      renderWithProviders(<SettingsDocument compact />);
      const doc = screen.getByTestId("settings-document");
      expect(doc).toHaveClass("text-sm");
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<SettingsDocument className="custom-class" />);
      const doc = screen.getByTestId("settings-document");
      expect(doc).toHaveClass("custom-class");
    });
  });
});
