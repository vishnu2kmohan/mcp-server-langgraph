/**
 * InlineConnectionCard
 *
 * In-chat connection setup card that appears when auth_required events are received.
 * Allows users to configure OAuth2 or API Key connections inline without leaving chat.
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  Link,
  X,
  ChevronDown,
  ChevronUp,
  Loader2,
  Key,
  ExternalLink,
  RefreshCw,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/UI";
import { useAppDispatch } from "../../store/hooks";
import {
  startConnectionSetup,
  updateConnectionSetupStatus,
  completeConnectionSetup,
} from "../../store/slices/chatConnectionSlice";
import {
  useListConnectionTemplatesQuery,
  useCreateConnectionMutation,
  useTestConnectionMutation,
  useStartOAuth2FlowMutation,
} from "../../api";
import { accordionVariants } from "../../design-system/micro-interactions";
import { useMotionSafeVariants } from "../../hooks/useMotionSafe";

/**
 * Props for InlineConnectionCard
 */
export interface InlineConnectionCardProps {
  /** Template ID for the suggested connection */
  templateId: string | null;
  /** Qualified tool name that triggered the auth requirement */
  toolName: string;
  /** User-friendly message explaining the auth requirement */
  message: string;
  /** Existing connection ID that needs re-authentication, if any */
  connectionId: string | null;
  /** Original message ID to retry after auth, if any */
  retryMessageId: string | null;
  /** Callback when the card is dismissed */
  onDismiss: () => void;
  /** Callback to retry the original message after connection is established */
  onRetry?: (messageId: string) => void;
  /** Test ID for testing */
  "data-testid"?: string;
}

/**
 * Connection setup status for UI display
 */
type SetupStatus =
  | "collapsed"
  | "expanded"
  | "authenticating"
  | "testing"
  | "complete"
  | "error";

/**
 * InlineConnectionCard Component
 *
 * Displays inline connection setup UI in chat when authentication is required.
 */
export function InlineConnectionCard({
  templateId,
  toolName: _toolName,
  message,
  connectionId,
  retryMessageId,
  onDismiss,
  onRetry,
  "data-testid": testId,
}: InlineConnectionCardProps) {
  const dispatch = useAppDispatch();
  const safeAccordionVariants = useMotionSafeVariants(accordionVariants);

  // Local UI state
  const [status, setStatus] = useState<SetupStatus>("collapsed");
  const [error, setError] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string>("");
  const [_newConnectionId, setNewConnectionId] = useState<string | null>(null);

  // Fetch template info
  const { data: templatesData } = useListConnectionTemplatesQuery({});
  const template = templatesData?.templates?.find((t) => t.id === templateId);

  // Mutations
  const [createConnection, { isLoading: isCreating }] =
    useCreateConnectionMutation();
  const [testConnection, { isLoading: isTesting }] =
    useTestConnectionMutation();
  const [startOAuth, { isLoading: isStartingOAuth }] =
    useStartOAuth2FlowMutation();

  const isLoading = isCreating || isTesting || isStartingOAuth;
  const isReAuth = !!connectionId;

  /**
   * Handle OAuth2 popup flow
   */
  const handleOAuth = useCallback(async () => {
    setStatus("authenticating");
    setError(null);

    try {
      // Start connection setup in Redux
      dispatch(
        startConnectionSetup({
          templateId: templateId ?? "", connectionId: connectionId ?? undefined,
        }),
      );

      let connId = connectionId;

      // If no existing connection, create one first
      if (!connId && template) {
        const newConn = await createConnection({
          name: `${template.name} Connection`,
          url: template.default_url,
          authType: template.auth_type,
          oauth2Scopes: template.oauth2_scopes,
        }).unwrap();
        connId = newConn.id;
        setNewConnectionId(newConn.id);
      }

      if (!connId) {
        throw new Error("Failed to create connection");
      }

      // Start OAuth flow
      const { authorization_url } = await startOAuth(connId).unwrap();

      // Open popup
      const popup = window.open(
        authorization_url,
        "oauth-popup",
        "width=600,height=700,popup=true,scrollbars=yes",
      );

      // Check if popup was blocked
      if (!popup || popup.closed) {
        // Fallback to full-page redirect
        window.location.href = authorization_url;
        return;
      }

      // Listen for postMessage from popup
      const handleMessage = async (event: MessageEvent) => {
        if (event.origin !== window.location.origin) return;
        if (event.data.type !== "oauth-callback") return;

        window.removeEventListener("message", handleMessage);

        if (event.data.success) {
          // Test connection
          setStatus("testing");
          dispatch(updateConnectionSetupStatus({ status: "testing" }));

          try {
            await testConnection(connId!).unwrap();
            setStatus("complete");
            dispatch(completeConnectionSetup());

            // Auto-retry if we have a message ID
            if (retryMessageId && onRetry) {
              setTimeout(() => {
                onRetry(retryMessageId);
                onDismiss();
              }, 1500);
            } else {
              // Auto-dismiss after success
              setTimeout(() => onDismiss(), 2000);
            }
          } catch (testErr) {
            setError(
              testErr instanceof Error ? testErr.message : "Connection test failed",
            );
            setStatus("error");
            dispatch(
              updateConnectionSetupStatus({
                status: "error",
                error: "Connection test failed",
              }),
            );
          }
        } else {
          setError(event.data.error || "OAuth authentication failed");
          setStatus("error");
          dispatch(
            updateConnectionSetupStatus({
              status: "error",
              error: event.data.error,
            }),
          );
        }

        popup?.close();
      };

      window.addEventListener("message", handleMessage);

      // Cleanup on popup close without callback
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          window.removeEventListener("message", handleMessage);
          // Only set error if still authenticating
          if (status === "authenticating") {
            setError("OAuth popup closed without completing");
            setStatus("error");
          }
        }
      }, 500);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to start authentication",
      );
      setStatus("error");
      dispatch(
        updateConnectionSetupStatus({
          status: "error",
          error: err instanceof Error ? err.message : "Unknown error",
        }),
      );
    }
  }, [
    connectionId,
    template,
    templateId,
    retryMessageId,
    onRetry,
    onDismiss,
    dispatch,
    createConnection,
    startOAuth,
    testConnection,
    status,
  ]);

  /**
   * Handle API Key submission
   */
  const handleApiKeySubmit = useCallback(async () => {
    if (!apiKey.trim() || !template) return;

    setStatus("authenticating");
    setError(null);

    try {
      dispatch(
        startConnectionSetup({
          templateId: templateId ?? "" }),
      );

      // Create connection with API key
      const newConn = await createConnection({
        name: `${template.name} Connection`,
        url: template.default_url,
        authType: "api_key",
        apiKey: apiKey,
      }).unwrap();

      setNewConnectionId(newConn.id);

      // Test connection
      setStatus("testing");
      dispatch(updateConnectionSetupStatus({ status: "testing" }));

      await testConnection(newConn.id).unwrap();

      setStatus("complete");
      dispatch(completeConnectionSetup());

      // Auto-retry or dismiss
      if (retryMessageId && onRetry) {
        setTimeout(() => {
          onRetry(retryMessageId);
          onDismiss();
        }, 1500);
      } else {
        setTimeout(() => onDismiss(), 2000);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create connection",
      );
      setStatus("error");
      dispatch(
        updateConnectionSetupStatus({
          status: "error",
          error: err instanceof Error ? err.message : "Unknown error",
        }),
      );
    }
  }, [
    apiKey,
    template,
    templateId,
    retryMessageId,
    onRetry,
    onDismiss,
    dispatch,
    createConnection,
    testConnection,
  ]);

  /**
   * Toggle expansion
   */
  const toggleExpand = useCallback(() => {
    setStatus((prev) => (prev === "collapsed" ? "expanded" : "collapsed"));
    setError(null);
  }, []);

  // Get display name
  const displayName = template?.name ?? templateId ?? "Connection";

  return (
    <motion.div
      className="mx-4 my-2 rounded-lg border border-primary-6 bg-primary-3 overflow-hidden"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      data-testid={testId}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-3 flex items-center justify-center">
            <Link className="w-4 h-4 text-primary-11" />
          </div>
          <div>
            <p className="font-medium text-neutral-12">
              {isReAuth ? `Reconnect ${displayName}` : `${displayName} Connection Required`}
            </p>
            <p className="text-sm text-neutral-11">
              {message}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {status === "collapsed" && (
            <Button
              type="button"
              variant="secondary"
              onClick={toggleExpand}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-primary-11 bg-primary-3 rounded-md hover:bg-primary-5 transition-colors"
              aria-label="Configure connection"
            >
              Configure
              <ChevronDown className="w-4 h-4" />
            </Button>
          )}
          <Button size="icon"
            type="button"
            variant="ghost"
            onClick={onDismiss}
            className="p-1.5 text-neutral-10 hover:text-neutral-11 rounded transition-colors"
            aria-label="Dismiss"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Expandable content */}
      <AnimatePresence>
        {status !== "collapsed" && (
          <motion.div
            variants={safeAccordionVariants}
            initial="collapsed"
            animate="expanded"
            exit="collapsed"
            className="border-t border-primary-6"
          >
            <div className="px-4 py-4">
              {/* Error state */}
              {status === "error" && error && (
                <div className="mb-4 p-3 rounded-md bg-error-3 border border-error-6">
                  <div className="flex items-center gap-2 text-error-11">
                    <AlertCircle className="w-4 h-4" />
                    <span className="text-sm">{error}</span>
                  </div>
                </div>
              )}

              {/* Complete state */}
              {status === "complete" && (
                <div className="p-3 rounded-md bg-success-3 border border-success-6">
                  <div className="flex items-center gap-2 text-success-11">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-sm">
                      Connected successfully!{}
                      {retryMessageId ? "Retrying your request..." : "" }
                    </span>
                  </div>
                </div>
              )}

              {/* Loading states */}
              {(status === "authenticating" || status === "testing") && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-6 h-6 text-primary-10 animate-spin" />
                  <span className="ml-2 text-neutral-11">
                    {status === "authenticating"
                      ? "Connecting..."
                      : "Testing connection..."}
                  </span>
                </div>
              )}

              {/* Auth method selection */}
              {status === "expanded" && template && (
                <div className="space-y-4">
                  {/* OAuth2 option */}
                  {template.auth_type === "oauth2" && (
                    <Button
                      type="button"
                      variant="primary"
                      onClick={handleOAuth}
                      disabled={isLoading}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-10 hover:bg-primary-11 text-neutral-12 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Sign in with {displayName}
                    </Button>
                  )}

                  {/* API Key option */}
                  {template.auth_type === "api_key" && (
                    <div className="space-y-3">
                      <label className="block">
                        <span className="text-sm font-medium text-neutral-11">
                          API Key
                        </span>
                        <input
                          type="password"
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                          placeholder="Enter your API key"
                          className="mt-1 block w-full px-3 py-2 border border-neutral-6 rounded-md shadow-sm bg-neutral-2 text-neutral-12 placeholder-neutral-9 focus:ring-primary-7 focus:border-primary-9"
                          aria-label="API Key"
                        />
                      </label>
                      <Button
                        type="button"
                        variant="primary"
                        onClick={handleApiKeySubmit}
                        disabled={!apiKey.trim() || isLoading}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary-10 hover:bg-primary-11 text-neutral-12 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <Key className="w-4 h-4" />
                        Connect
                      </Button>
                    </div>
                  )}

                  {/* For templates supporting both */}
                  {template.auth_type === "oauth2" && (
                    <div className="text-center">
                      <span className="text-sm text-neutral-10">
                        or configure with API key
                      </span>
                    </div>
                  )}

                  {/* Documentation link */}
                  {template.documentation_url && (
                    <a
                      href={template.documentation_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-center gap-1 text-sm text-primary-11 hover:underline"
                    >
                      View documentation
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}

                  {/* Collapse button */}
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={toggleExpand}
                    className="w-full flex items-center justify-center gap-1 px-4 py-2 text-neutral-11 hover:text-neutral-12 transition-colors"
                    aria-label="Back"
                  >
                    <ChevronUp className="w-4 h-4" />
                    Back
                  </Button>
                </div>
              )}

              {/* Error retry */}
              {status === "error" && (
                <div className="flex justify-center gap-2 mt-4">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setStatus("expanded")}
                    className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-primary-11 bg-primary-3 rounded-md hover:bg-primary-5 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Try again
                  </Button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
