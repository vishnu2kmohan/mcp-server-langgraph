import {
  useState,
  useEffect,
  useCallback,
  lazy,
  Suspense,
  type ReactNode,
} from "react";
import { Outlet, useLocation, useNavigate } from "react-router";
import { Toaster } from "sonner";
import { LeftSidebar } from "./components/Layout/LeftSidebar";
import { CommandPalette } from "./components/Layout/CommandPalette";
import { AppShell } from "./components/Layout/AppShell";
import { RightSidebar } from "./components/Layout/RightSidebar";
import { BottomPanel } from "./components/Layout/BottomPanel";
import { MainDock } from "./components/Layout/MainDock";
import { ChatDocument } from "./components/Chat/ChatDocument";
import { WorkflowDocument } from "./components/Workflow";
import { ProjectDocument } from "./components/Project";
import type { TabState } from "./store/slices/workspaceSlice";
import { OfflineBanner } from "./components/UI";
import { UpdatePrompt } from "./components/PWA";
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
const SettingsDocument = lazy(() =>
  import("./components/Settings").then((m) => ({
    default: m.SettingsDocument,
  })),
);
const CostDocument = lazy(() =>
  import("./components/Insights").then((m) => ({ default: m.CostDocument })),
);
const ObservabilityDocument = lazy(() =>
  import("./components/Insights").then((m) => ({
    default: m.ObservabilityDocument,
  })),
);
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

// Loading fallback for lazy-loaded components (defined outside component to avoid recreating on each render)
const LazyFallback = (
  <div className="flex h-full items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-500" />
  </div>
);

import { useAppDispatch } from "./store/hooks";
import { setUserInfo, setPersonaLoading } from "./store/slices/personaSlice";
import { initializeAuth } from "./store/slices/authSlice";
import { loadWorkspaceFromStorage } from "./store/slices/workspaceSlice";
import { useNotificationWebSocket } from "./hooks/useNotificationWebSocket";
import { usePWAUpdate } from "./hooks/usePWAUpdate";
import { useOnboarding } from "./hooks/useOnboarding";
import { useTheme } from "./hooks/useTheme";
import { useRouteTabSync } from "./hooks/useRouteTabSync";
import { useTabNavigation } from "./hooks/useTabNavigation";
import {
  useGetCurrentUserQuery,
  useGetWorkflowTemplatesQuery,
  useCreateSessionMutation,
  useCreateProjectMutation,
} from "./api";
import { useFeatureFlags } from "./contexts/FeatureFlagContext";
import { addTab, setActiveTabId } from "./store/slices/workspaceSlice";

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

  // Load workspace layout state from localStorage on startup
  // This restores panel sizes, collapsed states, tabs, and focus mode
  useEffect(() => {
    dispatch(loadWorkspaceFromStorage());
  }, [dispatch]);

  // Connect to notification WebSocket for studio/admin routes
  useNotificationWebSocket({ enabled: isStudioRoute });

  // Apply theme to document (defaults to dark, respects user preference)
  useTheme();

  // Sync routes with workspace tabs (only in studio routes)
  // This creates/activates tabs when navigating to different sections
  useRouteTabSync();

  // Tab navigation for MainDock (bidirectional sync)
  const handleTabNavigate = useTabNavigation();

  // Feature flags for conditional rendering of chat features
  const { isEnabled } = useFeatureFlags();
  const enableUrlContentFetch = isEnabled("url_content_fetch");
  const enableSlashCommands = isEnabled("slash_commands");
  const enableStylePresets = isEnabled("style_presets");

  // Tab content renderer - maps tab types to document components
  const renderTabContent = useCallback(
    (tab: TabState): ReactNode => {
      switch (tab.type) {
        case "chat":
          return (
            <ChatDocument
              sessionId={tab.entityId || ""}
              enableUrlFetch={enableUrlContentFetch}
              enableSlashCommands={enableSlashCommands}
              showStylePresets={enableStylePresets}
            />
          );
        case "workflow":
          return <WorkflowDocument workflowId={tab.entityId || ""} />;
        case "project":
          return <ProjectDocument projectId={tab.entityId || ""} />;
        case "settings":
          return (
            <Suspense fallback={LazyFallback}>
              <SettingsDocument />
            </Suspense>
          );
        case "cost":
          return (
            <Suspense fallback={LazyFallback}>
              <CostDocument />
            </Suspense>
          );
        case "observability":
          return (
            <Suspense fallback={LazyFallback}>
              <ObservabilityDocument />
            </Suspense>
          );
        default:
          return <div className="p-4 text-gray-500">Unknown tab type</div>;
      }
    },
    [enableUrlContentFetch, enableSlashCommands, enableStylePresets],
  );

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

  // Mutations for creating new resources
  const [createSession] = useCreateSessionMutation();
  const [createProject] = useCreateProjectMutation();

  // Handler for creating a new chat session
  const handleNewChat = useCallback(async () => {
    try {
      const session = await createSession({ name: "New Chat" }).unwrap();
      // Add new tab for the session
      dispatch(
        addTab({
          id: `chat-${session.id}`,
          type: "chat",
          title: session.name || "New Chat",
          entityId: session.id,
        }),
      );
      // Set as active and navigate
      dispatch(setActiveTabId(`chat-${session.id}`));
      navigate(`/studio/chat/${session.id}`);
    } catch (error) {
      console.error("Failed to create chat session:", error);
    }
  }, [createSession, dispatch, navigate]);

  // Handler for creating a new project
  const handleNewProject = useCallback(async () => {
    try {
      const project = await createProject({ name: "New Project" }).unwrap();
      // Add new tab for the project
      dispatch(
        addTab({
          id: `project-${project.id}`,
          type: "project",
          title: project.name,
          entityId: project.id,
        }),
      );
      // Set as active and navigate
      dispatch(setActiveTabId(`project-${project.id}`));
      navigate(`/studio/projects/${project.id}`);
    } catch (error) {
      console.error("Failed to create project:", error);
    }
  }, [createProject, dispatch, navigate]);

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
      // Error fetching - try to extract persona from JWT token
      console.warn(
        "Failed to fetch user info for persona detection:",
        userError,
      );

      // Attempt to decode the JWT token to get roles/persona
      const token = localStorage.getItem("access_token");
      if (token) {
        try {
          const parts = token.split(".");
          if (parts.length === 3) {
            const payload = JSON.parse(
              atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")),
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

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900">
      <OfflineBanner />
      {isStudioRoute ? (
        <>
          <AppShell
            leftSidebar={
              <LeftSidebar
                onNewChat={handleNewChat}
                onNewProject={handleNewProject}
              />
            }
            rightSidebar={<RightSidebar />}
            bottomPanel={<BottomPanel />}
          >
            <MainDock
              renderContent={renderTabContent}
              onTabNavigate={handleTabNavigate}
            />
          </AppShell>
          <CommandPalette />
        </>
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
      {/* Global onboarding wizard for first-time users (lazy-loaded) */}
      {isStudioRoute && shouldShowOnboarding && (
        <Suspense fallback={null}>
          <OnboardingWizard
            isOpen={shouldShowOnboarding}
            onComplete={handleOnboardingComplete}
            onSkip={handleOnboardingSkip}
            templates={templates ?? DEFAULT_TEMPLATES}
          />
        </Suspense>
      )}
      {/* Guided tour after onboarding (Priority 2.2, lazy-loaded) */}
      {isStudioRoute && showGuidedTour && (
        <Suspense fallback={null}>
          <GuidedTour
            isActive={showGuidedTour}
            steps={TOUR_STEPS}
            onComplete={handleTourComplete}
            onSkip={handleTourSkip}
          />
        </Suspense>
      )}
      {/* SUS Survey modal (Priority 1.4, lazy-loaded) */}
      {showSUSSurvey && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50">
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
