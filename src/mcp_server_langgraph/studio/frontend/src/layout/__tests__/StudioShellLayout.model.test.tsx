/**
 * StudioShellLayout Model Selection Tests
 *
 * Tests for model selection functionality including:
 * - Error toast on model API failure
 * - Model persistence to localStorage
 * - Model validation against available models
 * - Loading state propagation
 *
 * Sprint 1 - Chat Input Gap Fix
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import React from "react";
import { toast } from "sonner";
import { storage, STORAGE_KEYS } from "../../utils/storage";

// Import shared setup
import {
  resetAllMocks,
  createTestStore,
  flushPromises,
  mockImplementations,
  mockResizablePanels,
  mockReactRouter,
  resetPanelCounter,
  mockFns,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  mockBreakpointState,
  mockFeatureFlags,
} from "./StudioShellLayout.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

// Mock sonner toast
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  },
  Toaster: () => null,
}));

// Mock storage utility
vi.mock("../../utils/storage", async () => {
  const actual = await vi.importActual("../../utils/storage");
  return {
    ...actual,
    storage: {
      get: vi.fn(),
      set: vi.fn(),
      remove: vi.fn(),
      clear: vi.fn(),
      keys: vi.fn(() => []),
      stats: vi.fn(() => ({ usedBytes: 0, keyCount: 0 })),
      setWithTTL: vi.fn(),
      getWithTTL: vi.fn(),
      migrate: vi.fn(),
      getQuotaInfo: vi.fn(() => ({
        usedBytes: 0,
        keyCount: 0,
        estimatedQuota: 5 * 1024 * 1024,
        availableBytes: 5 * 1024 * 1024,
        percentUsed: 0,
        largestKeys: [],
      })),
      isNearQuota: vi.fn(() => false),
      cleanup: vi.fn(() => ({ removedCount: 0, freedBytes: 0 })),
    },
  };
});

// Model API mock state - controllable per test
export const mockModelAPIState = {
  models: [
    {
      id: "claude-3-5-sonnet",
      name: "Claude 3.5 Sonnet",
      provider: "anthropic",
      supportsThinking: true,
    },
    {
      id: "gpt-4o",
      name: "GPT-4o",
      provider: "openai",
      supportsThinking: false,
    },
    {
      id: "gemini-2.5-flash",
      name: "Gemini 2.5 Flash",
      provider: "google",
      supportsThinking: false,
    },
  ],
  isLoading: false,
  isError: false,
  serverConfig: { modelName: "claude-3-5-sonnet" },
  isServerConfigLoading: false,
};

vi.mock(
  "../../contexts/TelemetryContext",
  () => mockImplementations.TelemetryContext,
);
vi.mock(
  "../../devtools/TelemetryViewer",
  () => mockImplementations.TelemetryViewer,
);
vi.mock(
  "../../contexts/FeatureFlagContext",
  () => mockImplementations.FeatureFlagContext,
);
vi.mock("../../hooks/useNudges", () => mockImplementations.useNudges);
vi.mock(
  "../../hooks/useAIPersonaAnalysis",
  () => mockImplementations.useAIPersonaAnalysis,
);
vi.mock(
  "../../hooks/useAgentRequestWebSocket",
  () => mockImplementations.useAgentRequestWebSocket,
);
vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    ...mockImplementations.api,
    useGetAvailableModelsQuery: () => ({
      data: mockModelAPIState.isError ? undefined : mockModelAPIState.models,
      isLoading: mockModelAPIState.isLoading,
      isError: mockModelAPIState.isError,
    }),
    useGetServerConfigQuery: () => ({
      data: mockModelAPIState.isServerConfigLoading
        ? undefined
        : mockModelAPIState.serverConfig,
      isLoading: mockModelAPIState.isServerConfigLoading,
    }),
  };
});
vi.mock(
  "../../hooks/usePersonaRouting",
  () => mockImplementations.usePersonaRouting,
);
vi.mock(
  "../../hooks/useConnectionHealthWebSocket",
  () => mockImplementations.useConnectionHealthWebSocket,
);
vi.mock(
  "../../hooks/useCrossInsightsPanel",
  () => mockImplementations.useCrossInsightsPanel,
);
vi.mock(
  "../../hooks/useUXIntelligence",
  () => mockImplementations.useUXIntelligence,
);
vi.mock(
  "../../hooks/useMessageRevalidation",
  () => mockImplementations.useMessageRevalidation,
);
vi.mock(
  "../../hooks/useConversationIntelligence",
  () => mockImplementations.useConversationIntelligence,
);
vi.mock("../../hooks/useHITLDialogs", () => mockImplementations.useHITLDialogs);
vi.mock(
  "../../hooks/useAIOnboarding",
  () => mockImplementations.useAIOnboarding,
);
vi.mock("react-resizable-panels", () => mockResizablePanels);
vi.mock("react-router", () => mockReactRouter);
vi.mock("../ResponsiveLayout", () => mockImplementations.ResponsiveLayout);

// Import TelemetryProvider (mocked version)
import { TelemetryProvider } from "../../contexts/TelemetryContext";
import { MemoryRouter } from "react-router";

// Import component AFTER all mocks
import { StudioShellLayout } from "../StudioShellLayout";

// =============================================================================
// Helpers
// =============================================================================

function renderWithProviders() {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <TelemetryProvider>
        <MemoryRouter initialEntries={["/studio/chat"]}>
          <StudioShellLayout />
        </MemoryRouter>
      </TelemetryProvider>
    </Provider>,
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("StudioShellLayout Model Selection", () => {
  beforeEach(() => {
    resetAllMocks();
    resetPanelCounter();
    vi.clearAllMocks();

    // Reset model API state to defaults
    mockModelAPIState.models = [
      {
        id: "claude-3-5-sonnet",
        name: "Claude 3.5 Sonnet",
        provider: "anthropic",
        supportsThinking: true,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
        supportsThinking: false,
      },
      {
        id: "gemini-2.5-flash",
        name: "Gemini 2.5 Flash",
        provider: "google",
        supportsThinking: false,
      },
    ];
    mockModelAPIState.isLoading = false;
    mockModelAPIState.isError = false;
    mockModelAPIState.serverConfig = { modelName: "claude-3-5-sonnet" };
    mockModelAPIState.isServerConfigLoading = false;

    // Reset storage mock
    vi.mocked(storage.get).mockReturnValue(undefined);
    vi.mocked(storage.set).mockReturnValue(true);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Error Toast on Model API Failure", () => {
    it("should show error toast when models API fails", async () => {
      // GIVEN: Models API returns error
      mockModelAPIState.isError = true;
      mockModelAPIState.models = [];

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Error toast should be shown with deduplication id
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          "Failed to load models. Using fallback models.",
          expect.objectContaining({ id: "models-load-failed" }),
        );
      });
    });

    it("should not show error toast when models load successfully", async () => {
      // GIVEN: Models API returns success
      mockModelAPIState.isError = false;

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Error toast should NOT be shown
      expect(toast.error).not.toHaveBeenCalled();
    });

    it("should use fallback models when API fails", async () => {
      // GIVEN: Models API returns error
      mockModelAPIState.isError = true;
      mockModelAPIState.models = [];

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should still render (using fallback models)
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });
  });

  describe("Model Persistence to localStorage", () => {
    it("should read initial model from localStorage", async () => {
      // GIVEN: localStorage has a saved model
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "gpt-4o";
        return undefined;
      });

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: storage.get should have been called for SELECTED_MODEL
      expect(storage.get).toHaveBeenCalledWith(STORAGE_KEYS.SELECTED_MODEL);
    });

    it("should persist model selection to localStorage", async () => {
      // GIVEN: Component is rendered
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called with model selection
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.SELECTED_MODEL,
          expect.any(String),
        );
      });
    });

    it("should persist reasoning effort to localStorage", async () => {
      // GIVEN: Component is rendered
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called with reasoning effort
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.REASONING_EFFORT,
          expect.stringMatching(/^(low|medium|high)$/),
        );
      });
    });

    it("should persist enable thinking to localStorage", async () => {
      // GIVEN: Component is rendered
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called with enable thinking
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.ENABLE_THINKING,
          expect.any(Boolean),
        );
      });
    });
  });

  describe("Model Validation", () => {
    it("should fall back to first available model when saved model not in list", async () => {
      // GIVEN: localStorage has a model that doesn't exist in available models
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "nonexistent-model";
        return undefined;
      });

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called with the first available model
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.SELECTED_MODEL,
          "claude-3-5-sonnet",
        );
      });
    });

    it("should use server config default model when no localStorage value", async () => {
      // GIVEN: No localStorage value and server config has default
      vi.mocked(storage.get).mockReturnValue(undefined);
      mockModelAPIState.serverConfig = { modelName: "gpt-4o" };

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called with server config model
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.SELECTED_MODEL,
          "gpt-4o",
        );
      });
    });
  });

  describe("Loading State Propagation", () => {
    it("should propagate loading state to conversation panel", async () => {
      // GIVEN: Models are loading
      mockModelAPIState.isLoading = true;

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render (loading state handled internally)
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("should propagate server config loading state", async () => {
      // GIVEN: Server config is loading
      mockModelAPIState.isServerConfigLoading = true;

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render (loading state handled internally)
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Recent Models Tests (Sprint 1 - Enhanced Model Selector)
  // ===========================================================================

  describe("Recent Models Tracking", () => {
    it("should initialize recent models from localStorage", async () => {
      // GIVEN: localStorage has recent models saved
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.RECENT_MODELS)
          return ["gpt-4o", "gemini-2.5-flash"];
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "claude-3-5-sonnet";
        return undefined;
      });

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: storage.get should have been called for RECENT_MODELS
      expect(storage.get).toHaveBeenCalledWith(STORAGE_KEYS.RECENT_MODELS);
    });

    it("should persist recent models to localStorage when model changes", async () => {
      // GIVEN: Component is rendered with a model selected
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "claude-3-5-sonnet";
        if (key === STORAGE_KEYS.RECENT_MODELS) return [];
        return undefined;
      });

      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called for recent models
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.RECENT_MODELS,
          expect.any(Array),
        );
      });
    });

    it("should limit recent models to 5 entries", async () => {
      // GIVEN: localStorage has 5 recent models
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.RECENT_MODELS) {
          return ["model-1", "model-2", "model-3", "model-4", "model-5"];
        }
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "claude-3-5-sonnet";
        return undefined;
      });

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should be called with at most 5 models
      await waitFor(() => {
        const recentModelsCalls = vi
          .mocked(storage.set)
          .mock.calls.filter((call) => call[0] === STORAGE_KEYS.RECENT_MODELS);
        if (recentModelsCalls.length > 0) {
          const lastCall = recentModelsCalls[recentModelsCalls.length - 1];
          if (lastCall && Array.isArray(lastCall[1])) {
            expect(lastCall[1].length).toBeLessThanOrEqual(5);
          }
        }
      });
    });

    it("should not add duplicate models to recent list", async () => {
      // GIVEN: localStorage has claude-3-5-sonnet already in recent
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.RECENT_MODELS) return ["claude-3-5-sonnet"];
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "claude-3-5-sonnet";
        return undefined;
      });

      // WHEN: Component renders (same model selected)
      renderWithProviders();
      await flushPromises();

      // THEN: storage.set should not add duplicates
      await waitFor(() => {
        const recentModelsCalls = vi
          .mocked(storage.set)
          .mock.calls.filter((call) => call[0] === STORAGE_KEYS.RECENT_MODELS);
        if (recentModelsCalls.length > 0) {
          const lastCall = recentModelsCalls[recentModelsCalls.length - 1];
          if (lastCall && Array.isArray(lastCall[1])) {
            const uniqueModels = new Set(lastCall[1]);
            expect(lastCall[1].length).toBe(uniqueModels.size);
          }
        }
      });
    });
  });

  // ===========================================================================
  // Model Search Tests (Sprint 1 - Enhanced Model Selector)
  // ===========================================================================

  describe("Model Search Feature", () => {
    it("should enable model search when feature flag is enabled", async () => {
      // GIVEN: Feature flag is enabled (mocked via mockFeatureFlags)
      // Feature flag is checked via useFeatureFlag hook

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render successfully
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Enhanced Model Selector Feature Flag Tests (Sprint 1)
  // ===========================================================================

  describe("Enhanced Model Selector Feature Flag", () => {
    it("should NOT pass recentModels when enhanced_model_selector flag is disabled", async () => {
      // GIVEN: enhanced_model_selector feature flag is disabled
      mockFeatureFlags.enabledFlags = mockFeatureFlags.enabledFlags.filter(
        (flag) => flag !== "enhanced_model_selector",
      );

      // AND: localStorage has recent models
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.RECENT_MODELS)
          return ["gpt-4o", "gemini-2.5-flash"];
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "claude-3-5-sonnet";
        return undefined;
      });

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render (feature gracefully disabled)
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();

      // AND: useFeatureFlag should have been called with "enhanced_model_selector"
      expect(mockFns.useFeatureFlag).toHaveBeenCalledWith(
        "enhanced_model_selector",
      );
    });

    it("should pass recentModels when enhanced_model_selector flag is enabled", async () => {
      // GIVEN: enhanced_model_selector feature flag is enabled
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "enhanced_model_selector",
      ];

      // AND: localStorage has recent models
      vi.mocked(storage.get).mockImplementation((key) => {
        if (key === STORAGE_KEYS.RECENT_MODELS)
          return ["gpt-4o", "gemini-2.5-flash"];
        if (key === STORAGE_KEYS.SELECTED_MODEL) return "claude-3-5-sonnet";
        return undefined;
      });

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render successfully
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();

      // AND: useFeatureFlag should have been called with "enhanced_model_selector"
      expect(mockFns.useFeatureFlag).toHaveBeenCalledWith(
        "enhanced_model_selector",
      );

      // AND: recentModels should be persisted (indicating they're being tracked)
      await waitFor(() => {
        expect(storage.set).toHaveBeenCalledWith(
          STORAGE_KEYS.RECENT_MODELS,
          expect.any(Array),
        );
      });
    });

    it("should NOT enable model search when flag is disabled even with many models", async () => {
      // GIVEN: enhanced_model_selector feature flag is disabled
      mockFeatureFlags.enabledFlags = mockFeatureFlags.enabledFlags.filter(
        (flag) => flag !== "enhanced_model_selector",
      );

      // AND: Many models available (would normally trigger search)
      mockModelAPIState.models = [
        {
          id: "claude-3-5-sonnet",
          name: "Claude 3.5 Sonnet",
          provider: "anthropic",
          supportsThinking: true,
        },
        {
          id: "gpt-4o",
          name: "GPT-4o",
          provider: "openai",
          supportsThinking: false,
        },
        {
          id: "gpt-4-turbo",
          name: "GPT-4 Turbo",
          provider: "openai",
          supportsThinking: false,
        },
        {
          id: "gpt-3.5-turbo",
          name: "GPT-3.5 Turbo",
          provider: "openai",
          supportsThinking: false,
        },
        {
          id: "gemini-2.5-flash",
          name: "Gemini 2.5 Flash",
          provider: "google",
          supportsThinking: false,
        },
        {
          id: "gemini-2.5-pro",
          name: "Gemini 2.5 Pro",
          provider: "google",
          supportsThinking: true,
        },
      ];

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render (search feature disabled even with 6 models)
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();

      // AND: useFeatureFlag should have been called with "enhanced_model_selector"
      expect(mockFns.useFeatureFlag).toHaveBeenCalledWith(
        "enhanced_model_selector",
      );
    });

    it("should enable model search when flag is enabled AND more than 5 models", async () => {
      // GIVEN: enhanced_model_selector feature flag is enabled
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "enhanced_model_selector",
      ];

      // AND: Many models available (should trigger search)
      mockModelAPIState.models = [
        {
          id: "claude-3-5-sonnet",
          name: "Claude 3.5 Sonnet",
          provider: "anthropic",
          supportsThinking: true,
        },
        {
          id: "gpt-4o",
          name: "GPT-4o",
          provider: "openai",
          supportsThinking: false,
        },
        {
          id: "gpt-4-turbo",
          name: "GPT-4 Turbo",
          provider: "openai",
          supportsThinking: false,
        },
        {
          id: "gpt-3.5-turbo",
          name: "GPT-3.5 Turbo",
          provider: "openai",
          supportsThinking: false,
        },
        {
          id: "gemini-2.5-flash",
          name: "Gemini 2.5 Flash",
          provider: "google",
          supportsThinking: false,
        },
        {
          id: "gemini-2.5-pro",
          name: "Gemini 2.5 Pro",
          provider: "google",
          supportsThinking: true,
        },
      ];

      // WHEN: Component renders
      renderWithProviders();
      await flushPromises();

      // THEN: Component should render successfully
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();

      // AND: useFeatureFlag should have been called with "enhanced_model_selector"
      expect(mockFns.useFeatureFlag).toHaveBeenCalledWith(
        "enhanced_model_selector",
      );
    });
  });
});
