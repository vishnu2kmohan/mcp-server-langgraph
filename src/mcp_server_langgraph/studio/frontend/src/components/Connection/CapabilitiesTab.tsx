/**
 * CapabilitiesTab Component
 *
 * A tab component for displaying MCP capabilities (tools, resources, prompts)
 * in the consolidated Connections page. Wraps the AggregatedCapabilitiesPanel
 * and adds MCP action buttons and status indicators.
 *
 * @see ADR-0102 - Connections Page Redesign
 */

import { useState, useCallback, Suspense } from "react";
import { motion, useReducedMotion } from "motion/react";
import { Play, Eye, TestTube, Loader2 } from "lucide-react";
import { cn } from "@/utils/cn";
import { tabContentVariants } from "@/design-system/micro-interactions";
import { Button } from "@/components/UI";
import {
  LazyAggregatedCapabilitiesPanel,
  LazyToolInvocationDialog,
  LazyResourceViewer,
  LazyPromptTester,
} from "@/components/MCP";
import { useAppSelector } from "@/store/hooks";
import { selectPersona } from "@/store/slices/personaSlice";
import { useMCPConnection } from "@/contexts/MCPConnectionContext";

// ============================================================================
// Types
// ============================================================================

export interface CapabilitiesTabProps {
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export function CapabilitiesTab({ className }: CapabilitiesTabProps) {
  const prefersReducedMotion = useReducedMotion();

  // Persona for admin-only actions
  const persona = useAppSelector(selectPersona);
  const isAdmin = persona === "admin";

  // MCP connection status (from shared context, not a direct hook call)
  const {
    status: mcpWsStatus,
    isInitialized: mcpWsInitialized,
    serverInfo: mcpServerInfo,
    error: mcpWsError,
  } = useMCPConnection();

  // Dialog states
  const [isToolDialogOpen, setIsToolDialogOpen] = useState(false);
  const [isResourceViewerOpen, setIsResourceViewerOpen] = useState(false);
  const [isPromptTesterOpen, setIsPromptTesterOpen] = useState(false);

  // Pre-selected items from panel actions
  const [selectedTool, setSelectedTool] = useState<string | undefined>();
  const [selectedResource, setSelectedResource] = useState<
    string | undefined
  >();
  const [selectedPrompt, setSelectedPrompt] = useState<string | undefined>();

  // Panel action handlers
  const handleToolInvoke = useCallback((qualifiedName: string) => {
    setSelectedTool(qualifiedName);
    setIsToolDialogOpen(true);
  }, []);

  const handleResourceView = useCallback((qualifiedName: string) => {
    setSelectedResource(qualifiedName);
    setIsResourceViewerOpen(true);
  }, []);

  const handlePromptTest = useCallback((qualifiedName: string) => {
    setSelectedPrompt(qualifiedName);
    setIsPromptTesterOpen(true);
  }, []);

  // Close handlers
  const handleCloseToolDialog = useCallback(() => {
    setIsToolDialogOpen(false);
    setSelectedTool(undefined);
  }, []);

  const handleCloseResourceViewer = useCallback(() => {
    setIsResourceViewerOpen(false);
    setSelectedResource(undefined);
  }, []);

  const handleClosePromptTester = useCallback(() => {
    setIsPromptTesterOpen(false);
    setSelectedPrompt(undefined);
  }, []);

  // Motion variants
  const variants = prefersReducedMotion ? undefined : tabContentVariants;

  // WebSocket status indicator class
  const wsStatusClass = cn(
    "w-2.5 h-2.5 rounded-full",
    mcpWsStatus === "connected"
      ? "bg-success-9"
      : mcpWsStatus === "connecting" || mcpWsStatus === "reconnecting"
        ? "bg-warning-9 animate-pulse"
        : "bg-neutral-4",
  );

  // WebSocket status tooltip
  const wsStatusTooltip =
    mcpWsInitialized && mcpServerInfo
      ? `MCP Server: ${mcpServerInfo.name} v${mcpServerInfo.version}`
      : mcpWsError
        ? `MCP WebSocket: ${mcpWsError}`
        : `MCP WebSocket: ${mcpWsStatus}`;

  return (
    <motion.div
      className={cn("space-y-4", className)}
      variants={variants}
      initial="hidden"
      animate="visible"
    >
      {/* Header with Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-neutral-12">
            MCP Capabilities
          </h2>
          {/* MCP WebSocket Status Indicator */}
          <span
            data-testid="mcp-ws-status"
            aria-label={`MCP live sync: ${mcpWsStatus}`}
            title={wsStatusTooltip}
            className={wsStatusClass}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsToolDialogOpen(true)}
            aria-label="Invoke Tool"
            className="flex items-center gap-1.5"
          >
            <Play className="h-4 w-4" />
            <span className="hidden sm:inline">Invoke Tool</span>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsResourceViewerOpen(true)}
            aria-label="View Resource"
            className="flex items-center gap-1.5"
          >
            <Eye className="h-4 w-4" />
            <span className="hidden sm:inline">View Resource</span>
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsPromptTesterOpen(true)}
            aria-label="Test Prompt"
            className="flex items-center gap-1.5"
          >
            <TestTube className="h-4 w-4" />
            <span className="hidden sm:inline">Test Prompt</span>
          </Button>
        </div>
      </div>

      {/* Aggregated Capabilities Panel */}
      <Suspense
        fallback={
          <div className="flex items-center justify-center p-8 bg-neutral-1 rounded-lg border border-neutral-5">
            <div className="flex items-center gap-3 text-neutral-10">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Loading capabilities...</span>
            </div>
          </div>
        }
      >
        <LazyAggregatedCapabilitiesPanel
          showAdminActions={isAdmin}
          onToolInvoke={handleToolInvoke}
          onResourceView={handleResourceView}
          onPromptTest={handlePromptTest}
        />
      </Suspense>

      {/* Tool Invocation Dialog */}
      <LazyToolInvocationDialog
        open={isToolDialogOpen}
        onClose={handleCloseToolDialog}
        preselectedToolName={selectedTool}
      />

      {/* Resource Viewer Dialog */}
      <LazyResourceViewer
        open={isResourceViewerOpen}
        onClose={handleCloseResourceViewer}
        preselectedResourceUri={selectedResource}
      />

      {/* Prompt Tester Dialog */}
      <LazyPromptTester
        open={isPromptTesterOpen}
        onClose={handleClosePromptTester}
        preselectedPromptName={selectedPrompt}
      />
    </motion.div>
  );
}

export default CapabilitiesTab;
