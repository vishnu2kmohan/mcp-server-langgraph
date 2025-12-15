import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router";
import { Toaster } from "sonner";
import { Sidebar } from "./components/Layout/Sidebar";
import { CommandPalette } from "./components/Layout/CommandPalette";
import { OfflineBanner } from "./components/UI";
import { UpdatePrompt } from "./components/PWA";
import {
  OnboardingModal,
  type WorkflowTemplate,
} from "./components/Onboarding";
import { useAppDispatch } from "./store/hooks";
import { setUserInfo, setPersonaLoading } from "./store/slices/personaSlice";
import { useNotificationWebSocket } from "./hooks/useNotificationWebSocket";
import { usePWAUpdate } from "./hooks/usePWAUpdate";
import { useOnboarding } from "./hooks/useOnboarding";
import { useTheme } from "./hooks/useTheme";
import { useGetCurrentUserQuery, useGetWorkflowTemplatesQuery } from "./api";

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

  // Fetch workflow templates for onboarding (only when needed)
  const {
    data: templates,
    isLoading: isLoadingTemplates,
    error: templatesError,
    refetch: refetchTemplates,
  } = useGetWorkflowTemplatesQuery(undefined, {
    skip: !isStudioRoute || !shouldShowOnboarding,
  });

  // Handlers for onboarding
  const handleSelectTemplate = (template: WorkflowTemplate | null) => {
    completeOnboarding();
    if (template) {
      // Navigate to workflows with the template pre-selected
      navigate(`/studio/workflows?template=${template.id}`);
    }
  };

  const handleSkipOnboarding = () => {
    skipOnboarding();
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
      {/* Global onboarding modal for first-time users */}
      {isStudioRoute && (
        <OnboardingModal
          isOpen={shouldShowOnboarding}
          onClose={handleSkipOnboarding}
          onSelectTemplate={handleSelectTemplate}
          templates={templates ?? DEFAULT_TEMPLATES}
          isLoading={isLoadingTemplates && !templatesError}
          error={null}
          onRetry={refetchTemplates}
        />
      )}
    </div>
  );
}
