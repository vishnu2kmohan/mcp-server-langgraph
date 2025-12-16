import { useState, useEffect, useCallback } from "react";
import { Outlet, useLocation, useNavigate } from "react-router";
import { Toaster } from "sonner";
import { Sidebar } from "./components/Layout/Sidebar";
import { CommandPalette } from "./components/Layout/CommandPalette";
import { OfflineBanner } from "./components/UI";
import { UpdatePrompt } from "./components/PWA";
import {
  OnboardingWizard,
  GuidedTour,
  type WorkflowTemplate,
  type OnboardingResult,
  type TourStep,
  type TourCompleteResult,
  type TourSkipResult,
} from "./components/Onboarding";
import { SUSSurvey, type SUSSurveyResult } from "./components/Feedback";
import { useAppDispatch } from "./store/hooks";
import { setUserInfo, setPersonaLoading } from "./store/slices/personaSlice";
import { initializeAuth } from "./store/slices/authSlice";
import { useNotificationWebSocket } from "./hooks/useNotificationWebSocket";
import { usePWAUpdate } from "./hooks/usePWAUpdate";
import { useOnboarding } from "./hooks/useOnboarding";
import { useTheme } from "./hooks/useTheme";
import { useGetCurrentUserQuery, useGetWorkflowTemplatesQuery } from "./api";

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

  // Apply theme to document (defaults to dark, respects user preference)
  useTheme();

  // PWA update management
  const { needsUpdate, isUpdating, updateApp, dismissUpdate } = usePWAUpdate();

  // Onboarding for first-time users (only in studio routes)
  const {
    shouldShowModal: shouldShowOnboarding,
    complete: completeOnboarding,
    skip: skipOnboarding,
  } = useOnboarding();

  // Guided tour state (Priority 2.2 - triggers after onboarding)
  const [showGuidedTour, setShowGuidedTour] = useState(false);

  // Check if user has completed the tour before
  const hasTourCompleted = useCallback(() => {
    return localStorage.getItem("agent-studio-tour-completed") === "true";
  }, []);

  // Handle tour completion
  const handleTourComplete = useCallback((_result: TourCompleteResult) => {
    localStorage.setItem("agent-studio-tour-completed", "true");
    setShowGuidedTour(false);
  }, []);

  // Handle tour skip
  const handleTourSkip = useCallback((_result: TourSkipResult) => {
    localStorage.setItem("agent-studio-tour-completed", "true");
    setShowGuidedTour(false);
  }, []);

  // SUS Survey state (Priority 1.4 - triggers after 3rd session or 7 days)
  const [showSUSSurvey, setShowSUSSurvey] = useState(false);

  // Check if SUS survey should be shown
  useEffect(() => {
    if (!isStudioRoute) return;

    // Skip if already completed or dismissed
    const surveyCompleted =
      localStorage.getItem("agent-studio-sus-completed") === "true";
    const surveyDismissed = localStorage.getItem("agent-studio-sus-dismissed");
    if (surveyCompleted) return;

    // Skip if dismissed within the last 7 days
    if (surveyDismissed) {
      const dismissedAt = parseInt(surveyDismissed, 10);
      const daysSinceDismiss =
        (Date.now() - dismissedAt) / (1000 * 60 * 60 * 24);
      if (daysSinceDismiss < 7) return;
    }

    // Track session count
    const sessionCount = parseInt(
      localStorage.getItem("agent-studio-session-count") || "0",
      10,
    );
    localStorage.setItem(
      "agent-studio-session-count",
      String(sessionCount + 1),
    );

    // Track first visit
    let firstVisit = localStorage.getItem("agent-studio-first-visit");
    if (!firstVisit) {
      firstVisit = Date.now().toString();
      localStorage.setItem("agent-studio-first-visit", firstVisit);
    }

    // Calculate days since first visit
    const daysSinceFirstVisit =
      (Date.now() - parseInt(firstVisit, 10)) / (1000 * 60 * 60 * 24);

    // Show survey after 3rd session OR 7 days (whichever comes first)
    if (sessionCount >= 3 || daysSinceFirstVisit >= 7) {
      // Delay survey display to not interrupt user immediately
      const timer = setTimeout(() => {
        setShowSUSSurvey(true);
      }, 5000); // 5 second delay
      return () => clearTimeout(timer);
    }
  }, [isStudioRoute]);

  // Handle SUS survey submission
  const handleSUSSubmit = useCallback((result: SUSSurveyResult) => {
    localStorage.setItem("agent-studio-sus-completed", "true");
    setShowSUSSurvey(false);
    // TODO: Send result to backend analytics endpoint
    console.log("SUS Survey submitted:", result);
  }, []);

  // Handle SUS survey dismissal
  const handleSUSDismiss = useCallback(() => {
    localStorage.setItem("agent-studio-sus-dismissed", Date.now().toString());
    setShowSUSSurvey(false);
  }, []);

  // Fetch workflow templates for onboarding (only when needed)
  const { data: templates } = useGetWorkflowTemplatesQuery(undefined, {
    skip: !isStudioRoute || !shouldShowOnboarding,
  });

  // Handler for OnboardingWizard completion
  const handleOnboardingComplete = (_result: OnboardingResult) => {
    completeOnboarding();

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

  // Update persona state when user data is fetched
  useEffect(() => {
    if (!isStudioRoute) return;

    if (userData) {
      // Dispatch setUserInfo action to update persona state in Redux
      // Use persona from API (computed by backend) for consistent RBAC
      dispatch(
        setUserInfo({
          username: userData.username || "Unknown",
          email: userData.email,
          roles: userData.roles || [],
          persona: userData.persona,
        }),
      );
    } else if (userError) {
      // Error fetching - stop loading, default to user persona
      console.warn(
        "Failed to fetch user info for persona detection:",
        userError,
      );
      dispatch(setPersonaLoading(false));
    }
  }, [isStudioRoute, userData, userError, dispatch]);

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <OfflineBanner />
      {isStudioRoute ? (
        <div className="flex">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <Outlet />
          </main>
          <CommandPalette />
        </div>
      ) : (
        <Outlet />
      )}
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
      {/* Global onboarding wizard for first-time users */}
      {isStudioRoute && (
        <OnboardingWizard
          isOpen={shouldShowOnboarding}
          onComplete={handleOnboardingComplete}
          onSkip={handleOnboardingSkip}
          templates={templates ?? DEFAULT_TEMPLATES}
        />
      )}
      {/* Guided tour after onboarding (Priority 2.2) */}
      {isStudioRoute && (
        <GuidedTour
          isActive={showGuidedTour}
          steps={TOUR_STEPS}
          onComplete={handleTourComplete}
          onSkip={handleTourSkip}
        />
      )}
      {/* SUS Survey modal (Priority 1.4) */}
      {showSUSSurvey && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
          <SUSSurvey onSubmit={handleSUSSubmit} onDismiss={handleSUSDismiss} />
        </div>
      )}
    </div>
  );
}
