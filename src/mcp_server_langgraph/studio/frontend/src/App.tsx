import {
  useState,
  useEffect,
  useCallback,
  lazy,
  Suspense,
  useRef,
} from "react";
import { Outlet, useLocation, useNavigate } from "react-router";
import { Toaster } from "sonner";
import {
  OfflineBanner,
  ConflictResolutionDialog,
} from "./components/OfflineBanner";
import { UpdatePrompt } from "./components/PWA";
import { useOffline } from "./hooks/useOffline";
import { useOfflineQueue } from "./hooks/useOfflineQueue";
import type {
  WorkflowTemplate,
  OnboardingResult,
  TourStep,
  TourCompleteResult,
  TourSkipResult,
} from "./components/Onboarding";
import type { SUSSurveyResult } from "./components/Feedback";

// Lazy-loaded components for better bundle splitting
// These are only loaded when needed (modal/conditional rendering)
const OnboardingWizard = lazy(() =>
  import("./components/Onboarding").then((m) => ({
    default: m.OnboardingWizard,
  })),
);
const GuidedTour = lazy(() =>
  import("./components/Onboarding").then((m) => ({ default: m.GuidedTour })),
);
const SUSSurvey = lazy(() =>
  import("./components/Feedback").then((m) => ({ default: m.SUSSurvey })),
);

import { useAppDispatch } from "./store/hooks";
import {
  setUserInfo,
  hydrateFromServer,
  setPersonaLoading,
  type SubPersona,
} from "./store/slices/personaSlice";
import { initializeAuth } from "./store/slices/authSlice";
import { useNotificationWebSocket } from "./hooks/useNotificationWebSocket";
import { useAlertWebSocket } from "./hooks/useAlertWebSocket";
import { useAlertSoundIntegration } from "./hooks/useAlertSoundIntegration";
import { usePWAUpdate } from "./hooks/usePWAUpdate";
import { useOnboarding } from "./hooks/useOnboarding";
import { useTheme } from "./hooks/useTheme";
import { useAccessibility } from "./hooks/useAccessibility";
import { useErrorReporting } from "./hooks/useErrorReporting";
import {
  useGetCurrentUserQuery,
  useGetWorkflowTemplatesQuery,
  useSubmitFeedbackMutation,
} from "./api";
import { useFeatureFlags } from "./contexts/FeatureFlagContext";
import { storage, STORAGE_KEYS, getAuthToken } from "./utils/storage";
import { registerServiceWorker } from "./utils/serviceWorker";

/**
 * Default tour steps for first-time users (Priority 2.2)
 */
const TOUR_STEPS: TourStep[] = [
  {
    target: "#sidebar-navigation",
    title: "Navigate Your Workspace",
    content:
      "Use the sidebar to navigate between Chat, Workflows, and other sections of Agent Studio.",
    position: "right",
  },
  {
    target: "#command-palette-trigger",
    title: "Quick Search",
    content:
      "Press Cmd+K (or Ctrl+K) to open the command palette and quickly find anything in Agent Studio.",
    position: "bottom",
  },
  {
    target: "#new-session-button",
    title: "Start a Conversation",
    content:
      "Click here to start a new chat session with an AI agent. Your conversations are saved automatically.",
    position: "bottom",
  },
  {
    target: "#notification-bell",
    title: "Stay Informed",
    content:
      "Check notifications for important updates, system alerts, and activity in your workspace.",
    position: "left",
  },
];

/**
 * Default workflow templates for onboarding (fallback when API unavailable)
 */
const DEFAULT_TEMPLATES: WorkflowTemplate[] = [
  {
    id: "chatbot",
    name: "Conversational Chatbot",
    description:
      "A simple chatbot that can answer questions and have conversations.",
    category: "conversational",
    tags: ["chat", "qa"],
  },
  {
    id: "agent",
    name: "ReAct Agent",
    description: "An agent that can reason and take actions using tools.",
    category: "agent",
    tags: ["tools", "reasoning"],
  },
  {
    id: "rag",
    name: "RAG Pipeline",
    description: "Retrieval-Augmented Generation for document Q&A.",
    category: "pipeline",
    tags: ["rag", "documents"],
  },
  {
    id: "multi-agent",
    name: "Multi-Agent System",
    description: "Multiple agents collaborating to solve complex tasks.",
    category: "collaboration",
    tags: ["multi-agent", "orchestration"],
  },
];

/**
 * Root application component.
 *
 * Provides:
 * - Global toast notifications
 * - Sidebar navigation for studio routes
 * - Outlet for nested routes
 * - User info fetching on mount (username, email, roles for persona detection)
 */
export function App() {
  const location = useLocation();
  const navigate = useNavigate();

  // Feature flags for UX enhancements
  const { isEnabled } = useFeatureFlags();

  // Check if on studio/admin route (for features like notifications, onboarding)
  const isStudioRoute =
    location.pathname.startsWith("/studio") ||
    location.pathname.startsWith("/admin");

  const dispatch = useAppDispatch();

  // Initialize authentication on app startup
  // This restores the user session from localStorage tokens
  useEffect(() => {
    dispatch(initializeAuth());
  }, [dispatch]);

  // Connect to notification WebSocket for studio/admin routes
  useNotificationWebSocket({ enabled: isStudioRoute });

  // Check if on admin route (for alert WebSocket - ADR-0026)
  const isAdminRoute = location.pathname.startsWith("/admin");

  // Connect to alert WebSocket for admin routes (real-time infrastructure alerts)
  useAlertWebSocket({ enabled: isAdminRoute });

  // Play sound for critical alerts (integrates with alertSlice)
  useAlertSoundIntegration();

  // Apply theme to document (defaults to dark, respects user preference)
  useTheme();

  // Global accessibility settings - respects system preferences and persists user choices
  // Features: reduced motion, high contrast, font size, screen reader announcements
  const { reducedMotion: _reducedMotion, announce } = useAccessibility();

  // Global error reporting - captures unhandled errors and sends to backend telemetry
  // Phase 5.3: App-level error reporting for observability
  useErrorReporting({
    captureWindowErrors: true,
    captureUnhandledRejections: true,
    enabled: true,
  });

  // Offline resilience hooks (Sprint 3 - Phase 2.3)
  const isOffline = useOffline();
  const {
    pendingCount,
    isSyncing,
    sync,
    lastSyncResult,
    conflicts,
    resolveConflict,
    resolveAllConflicts,
  } = useOfflineQueue();

  // UX Enhancement Feature Flags
  const enableOnboardingWizard = isEnabled("onboarding_wizard");
  const enableGuidedTour = isEnabled("guided_tour");
  const enableSusSurvey = isEnabled("sus_survey");

  // PWA update management
  const { needsUpdate, isUpdating, updateApp, dismissUpdate } = usePWAUpdate();

  // Onboarding for first-time users (only in studio routes)
  const {
    showOnboarding: shouldShowOnboarding,
    completeOnboarding,
    skipOnboarding,
  } = useOnboarding();

  // Guided tour state (Priority 2.2 - triggers after onboarding)
  const [showGuidedTour, setShowGuidedTour] = useState(false);

  // Check if user has completed the tour before
  const hasTourCompleted = useCallback(() => {
    return storage.get<boolean>(STORAGE_KEYS.TOUR_COMPLETED, false) === true;
  }, []);

  // Handle tour completion
  const handleTourComplete = useCallback(
    (_result: TourCompleteResult) => {
      storage.set(STORAGE_KEYS.TOUR_COMPLETED, true);
      setShowGuidedTour(false);
      announce("Tour complete. You can now start using Agent Studio.");
    },
    [announce],
  );

  // Handle tour skip
  const handleTourSkip = useCallback(
    (_result: TourSkipResult) => {
      storage.set(STORAGE_KEYS.TOUR_COMPLETED, true);
      setShowGuidedTour(false);
      announce(
        "Tour skipped. You can access the tour later from the help menu.",
      );
    },
    [announce],
  );

  // SUS Survey state (Priority 1.4 - triggers after 3rd session or 7 days)
  const [showSUSSurvey, setShowSUSSurvey] = useState(false);

  // Check if SUS survey should be shown
  useEffect(() => {
    if (!isStudioRoute) return;

    // Skip if already completed or dismissed
    const surveyCompleted =
      storage.get<boolean>(STORAGE_KEYS.SUS_COMPLETED, false) === true;
    const surveyDismissed = storage.get<number>(STORAGE_KEYS.SUS_DISMISSED);
    if (surveyCompleted) return;

    // Skip if dismissed within the last 7 days
    if (surveyDismissed) {
      const daysSinceDismiss =
        (Date.now() - surveyDismissed) / (1000 * 60 * 60 * 24);
      if (daysSinceDismiss < 7) return undefined;
    }

    // Track session count
    const sessionCount =
      storage.get<number>(STORAGE_KEYS.SESSION_COUNT, 0) ?? 0;
    storage.set(STORAGE_KEYS.SESSION_COUNT, sessionCount + 1);

    // Track first visit
    let firstVisit = storage.get<number>(STORAGE_KEYS.FIRST_VISIT);
    if (!firstVisit) {
      firstVisit = Date.now();
      storage.set(STORAGE_KEYS.FIRST_VISIT, firstVisit);
    }

    // Calculate days since first visit
    const daysSinceFirstVisit =
      (Date.now() - firstVisit) / (1000 * 60 * 60 * 24);

    // Show survey after 3rd session OR 7 days (whichever comes first)
    if (sessionCount >= 3 || daysSinceFirstVisit >= 7) {
      // Delay survey display to not interrupt user immediately
      const timer = setTimeout(() => {
        setShowSUSSurvey(true);
      }, 5000); // 5 second delay
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isStudioRoute]);

  // Handle SUS survey submission - placeholder, actual handler is defined after mutation is initialized
  // This is just to satisfy React hooks order, actual implementation is handleSUSSubmitFn below

  // Handle SUS survey dismissal
  const handleSUSDismiss = useCallback(() => {
    storage.set(STORAGE_KEYS.SUS_DISMISSED, Date.now());
    setShowSUSSurvey(false);
  }, []);

  // Fetch workflow templates for onboarding (only when needed)
  const { data: templates } = useGetWorkflowTemplatesQuery(undefined, {
    skip: !isStudioRoute || !shouldShowOnboarding,
  });

  // Handler for OnboardingWizard completion
  const handleOnboardingComplete = (_result: OnboardingResult) => {
    completeOnboarding();

    // Screen reader announcement for accessibility
    announce("Onboarding complete. Welcome to Agent Studio.");

    // Trigger guided tour if not completed before (Priority 2.2)
    if (!hasTourCompleted()) {
      setShowGuidedTour(true);
    }

    // Always navigate to Chat after onboarding - Chat is the primary interaction point
    // If a template was selected, it can be accessed from the Workflows page later
    navigate("/studio/chat");
  };

  const handleOnboardingSkip = () => {
    skipOnboarding();
    // Also offer tour after skipping onboarding
    if (!hasTourCompleted()) {
      setShowGuidedTour(true);
    }
  };

  // Fetch user info via RTK Query for studio/admin routes
  // Skip query if not on a studio/admin route
  const { data: userData, error: userError } = useGetCurrentUserQuery(
    undefined,
    { skip: !isStudioRoute },
  );

  // Mutations for creating new resources
  const [submitFeedback] = useSubmitFeedbackMutation();

  // Handle SUS survey submission - submits to backend analytics
  const handleSUSSubmit = useCallback(
    async (result: SUSSurveyResult) => {
      storage.set(STORAGE_KEYS.SUS_COMPLETED, true);
      setShowSUSSurvey(false);

      // Submit SUS score to backend via the feedback endpoint
      // Map SUS score (0-100) to NPS scale (0-10) for consistency with backend metrics
      // Add detailed SUS data in the comment for analytics purposes
      try {
        await submitFeedback({
          nps_score: Math.round(result.score / 10), // Convert 0-100 to 0-10
          comment: JSON.stringify({
            type: "sus_survey",
            sus_score: result.score,
            responses: result.responses,
            timestamp: result.timestamp,
          }),
        }).unwrap();
      } catch (error) {
        // Silently fail - survey completion is already tracked locally
        // and we don't want to interrupt user experience
        console.error("Failed to submit SUS survey:", error);
      }
    },
    [submitFeedback],
  );

  // Update persona state when user data is fetched
  useEffect(() => {
    if (!isStudioRoute) return;

    if (userData) {
      // Dispatch hydrateFromServer to update persona state with all Sprint 4 fields
      // This includes visibleModules, featureFlags, subPersona, apiVersion
      // Use persona from API (computed by backend) for consistent RBAC
      // NOTE: API response is transformed by transformSnakeToCamel, so use camelCase
      dispatch(
        hydrateFromServer({
          username: userData.username || "Unknown",
          email: userData.email,
          roles: userData.roles || [],
          persona: userData.persona,
          // Sprint 4 extended fields from server (camelCase after transform)
          subPersona: userData.subPersona as SubPersona | null | undefined,
          visibleModules: userData.visibleModules,
          featureFlags: userData.featureFlags,
          apiVersion: userData.apiVersion,
        }),
      );
    } else if (userError) {
      // Error fetching - try to extract persona from JWT token
      console.warn(
        "Failed to fetch user info for persona detection:",
        userError,
      );

      // Attempt to decode the JWT token to get roles/persona
      const token = getAuthToken();
      if (token) {
        try {
          const parts = token.split(".");
          const payloadPart = parts[1];
          if (parts.length === 3 && payloadPart) {
            const payload = JSON.parse(
              atob(payloadPart.replace(/-/g, "+").replace(/_/g, "/")),
            );

            // Extract roles
            let roles: string[] = [];
            if (payload.realm_access?.roles) {
              roles = payload.realm_access.roles;
            } else if (Array.isArray(payload.roles)) {
              roles = payload.roles;
            }

            // Derive persona from roles
            let persona: "admin" | "developer" | "user" = "user";
            if (roles.includes("admin")) {
              persona = "admin";
            } else if (roles.includes("developer")) {
              persona = "developer";
            }

            dispatch(
              setUserInfo({
                username:
                  payload.preferred_username || payload.username || "Unknown",
                email: payload.email,
                roles,
                persona,
              }),
            );
            return;
          }
        } catch (e) {
          console.warn("Failed to decode JWT for persona:", e);
        }
      }

      // Fallback: stop loading with default persona
      dispatch(setPersonaLoading(false));
    }
  }, [isStudioRoute, userData, userError, dispatch]);

  // Track if SW has been registered to prevent duplicate registrations
  const swRegisteredRef = useRef(false);

  // Register service worker AFTER authentication is confirmed
  // This avoids precaching ~130+ assets for unauthenticated users on /login
  useEffect(() => {
    // Only register in production mode
    if (!import.meta.env.PROD) return;

    // Only register after successful user authentication
    if (!userData) return;

    // Only register once
    if (swRegisteredRef.current) return;

    swRegisteredRef.current = true;
    registerServiceWorker().catch((error) => {
      console.warn("Service worker registration failed:", error);
    });
  }, [userData]);

  return (
    <div className="min-h-screen bg-neutral-1">
      <OfflineBanner
        isOffline={isOffline}
        pendingCount={pendingCount}
        onSync={sync}
        isSyncing={isSyncing}
        lastSyncTime={lastSyncResult?.timestamp}
      />
      {/* Conflict resolution dialog for offline sync conflicts */}
      <ConflictResolutionDialog
        conflicts={conflicts}
        onResolve={resolveConflict}
        onResolveAll={resolveAllConflicts}
      />
      {/* All routes render via router - StudioShellLayout for /studio/* */}
      <Outlet />
      <Toaster
        position="bottom-right"
        richColors
        toastOptions={{
          duration: 4000,
          classNames: {
            toast: "font-sans",
          },
        }}
      />
      <UpdatePrompt
        needsUpdate={needsUpdate}
        isUpdating={isUpdating}
        onUpdate={updateApp}
        onDismiss={dismissUpdate}
      />
      {/* Global onboarding wizard for first-time users (lazy-loaded, feature-flagged) */}
      {enableOnboardingWizard && isStudioRoute && shouldShowOnboarding && (
        <Suspense fallback={null}>
          <OnboardingWizard
            isOpen={shouldShowOnboarding}
            onComplete={handleOnboardingComplete}
            onSkip={handleOnboardingSkip}
            templates={templates ?? DEFAULT_TEMPLATES}
          />
        </Suspense>
      )}
      {/* Guided tour after onboarding (Priority 2.2, lazy-loaded, feature-flagged) */}
      {enableGuidedTour && isStudioRoute && showGuidedTour && (
        <Suspense fallback={null}>
          <GuidedTour
            isActive={showGuidedTour}
            steps={TOUR_STEPS}
            onComplete={handleTourComplete}
            onSkip={handleTourSkip}
          />
        </Suspense>
      )}
      {/* SUS Survey modal (Priority 1.4, lazy-loaded, feature-flagged) */}
      {enableSusSurvey && showSUSSurvey && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-neutral-a6">
          <Suspense fallback={null}>
            <SUSSurvey
              onSubmit={handleSUSSubmit}
              onDismiss={handleSUSDismiss}
            />
          </Suspense>
        </div>
      )}
    </div>
  );
}
