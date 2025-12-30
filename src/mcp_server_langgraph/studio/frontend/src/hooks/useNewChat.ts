/**
 * useNewChat Hook
 *
 * Hook for creating a new chat session and navigating to it.
 * Used by StudioShellLayout and other components that need to create new chats.
 *
 * Usage:
 * ```tsx
 * function SessionNav() {
 *   const { createNewChat, isCreating, error } = useNewChat();
 *
 *   return (
 *     <button onClick={() => createNewChat()} disabled={isCreating}>
 *       New Chat
 *     </button>
 *   );
 * }
 * ```
 */
import { useState, useCallback } from "react";
import { useNavigate, useRevalidator } from "react-router";
import { useSessionTelemetry } from "../contexts/TelemetryContext";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { setIntendedRoute } from "../utils/intendedRoute";

// =============================================================================
// Types
// =============================================================================

interface UseNewChatOptions {
  /** Base path for navigation (default: "/studio/chat") */
  basePath?: string;
}

interface CreateNewChatOptions {
  /** Custom name for the session (default: "New Chat") */
  name?: string;
}

interface UseNewChatResult {
  /** Create a new chat session and navigate to it */
  createNewChat: (options?: CreateNewChatOptions) => Promise<void>;
  /** Whether a session is currently being created */
  isCreating: boolean;
  /** Error message if creation failed */
  error: string | null;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for creating new chat sessions.
 *
 * @param options - Configuration options
 * @returns Object with createNewChat function, isCreating, and error states
 */
export function useNewChat(options: UseNewChatOptions = {}): UseNewChatResult {
  const { basePath = "/studio/chat" } = options;
  const navigate = useNavigate();
  const revalidator = useRevalidator();

  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get telemetry from context
  const sessionTelemetry = useSessionTelemetry();

  // Handle auth failure by navigating to login
  const handleAuthFailure = useCallback(() => {
    setIntendedRoute(
      window.location.pathname + window.location.search + window.location.hash,
    );
    navigate("/login", { replace: true });
  }, [navigate]);

  const createNewChat = useCallback(
    async (createOptions: CreateNewChatOptions = {}) => {
      const { name = "New Chat" } = createOptions;
      const startTime = Date.now();

      // Clear previous error and set loading
      setError(null);
      setIsCreating(true);

      try {
        const response = await authenticatedFetch("/api/v1/sessions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name }),
          onAuthFailure: handleAuthFailure,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to create session");
        }

        const session = await response.json();

        // Track successful creation
        sessionTelemetry.trackSessionCreation({
          sessionId: session.id,
          sessionName: name,
          success: true,
          durationMs: Date.now() - startTime,
        });

        // Revalidate route data to update session list in nav
        revalidator.revalidate();

        // Navigate to the new session
        navigate(`${basePath}/${session.id}`);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to create session";

        // Track failed creation
        sessionTelemetry.trackSessionCreation({
          success: false,
          durationMs: Date.now() - startTime,
          error: errorMessage,
        });

        setError(errorMessage);
      } finally {
        setIsCreating(false);
      }
    },
    [basePath, navigate, revalidator, sessionTelemetry, handleAuthFailure],
  );

  return {
    createNewChat,
    isCreating,
    error,
  };
}
