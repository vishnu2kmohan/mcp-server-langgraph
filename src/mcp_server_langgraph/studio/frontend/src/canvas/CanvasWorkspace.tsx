/**
 * CanvasWorkspace - Phase 1
 *
 * Main Canvas workspace component that manages the artifact display area
 * with resizable panels for preview and editing.
 */
import {
  useState,
  useCallback,
  useMemo,
  useEffect,
  Suspense,
  lazy,
} from "react";
import {
  FileCode2,
  Sparkles,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectSelectedArtifactId,
  setSelectedArtifactId,
  selectTabOrder,
  setTabOrder,
  removeFromTabOrder,
} from "../store/slices/canvasSlice";
import { CanvasArtifact } from "./CanvasArtifact";
import { CanvasTabs, type TabType } from "./CanvasTabs";
import { getVisibleTabs } from "./canvasUtils";
import { ArtifactActions } from "./ArtifactActions";
import { ArtifactTabBar } from "./ArtifactTabBar";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";
import { cn } from "../utils/cn";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { Tooltip } from "../components/UI/Tooltip";
import { Button } from "../components/UI";

// AI Components (Phase 4) - lazy-loaded for reduced bundle size
import { LazyAIEditOverlay, type Selection } from "../ai/lazy";

// Lazy-loaded preview components for different content types
const InteractiveMermaidDiagram = lazy(
  () => import("../components/Chat/InteractiveMermaidDiagram"),
);

// Canvas Intelligence hooks (Phase 4 - Sprint 4)
import {
  useCodeAnalysis,
  useDiagramAnalysis,
} from "../hooks/useCanvasIntelligence";

// =============================================================================
// Types
// =============================================================================

export interface CanvasWorkspaceProps {
  /** List of artifacts for this session */
  artifacts: CanvasArtifactType[];
  /** Callback when artifact is selected */
  onArtifactSelect?: (artifact: CanvasArtifactType) => void;
  /** Callback when content is changed */
  onContentChange?: (artifactId: string, content: string) => void;
  /** Callback when artifact is saved */
  onSave?: (artifactId: string, content: string) => void;
  /** Additional class name */
  className?: string;
  /** Enable inline editing of artifact titles */
  enableArtifactEdit?: boolean;
  /** Callback when artifact is renamed */
  onRenameArtifact?: (artifactId: string, title: string) => void;
  /** Enable hover tooltip with artifact details */
  enableArtifactHover?: boolean;
  /** User ID for AI features (format: "user:username") */
  userId?: string;
  /** Session ID for AI features */
  sessionId?: string;
  /** Current persona for RBAC-aware AI responses */
  persona?: string;
  /** Enable AI intelligence features (code analysis, diagram analysis) */
  enableAI?: boolean;
}


// =============================================================================
// Component
// =============================================================================

export function CanvasWorkspace({
  artifacts,
  onArtifactSelect,
  onContentChange,
  onSave,
  className,
  enableArtifactEdit: _enableArtifactEdit = false,
  onRenameArtifact,
  enableArtifactHover: _enableArtifactHover = false,
  userId,
  sessionId,
  persona: _persona,
  enableAI = false,
}: CanvasWorkspaceProps) {
  const dispatch = useAppDispatch();
  const selectedArtifactId = useAppSelector(selectSelectedArtifactId);
  const reduxTabOrder = useAppSelector(selectTabOrder);

  // Compute effective tab order - use Redux if available, otherwise artifact order
  const effectiveTabOrder = useMemo(() => {
    if (reduxTabOrder.length > 0) {
      // Filter to only include artifacts that exist
      return reduxTabOrder.filter((id) => artifacts.some((a) => a.id === id));
    }
    // Fall back to artifact order
    return artifacts.map((a) => a.id);
  }, [reduxTabOrder, artifacts]);

  const [activeTab, setActiveTab] = useState<TabType>("code");
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState<string>("");

  // AI Edit Overlay state (Phase 4)
  const [aiEditVisible, setAiEditVisible] = useState(false);
  const [aiEditSelection, setAiEditSelection] = useState<Selection | null>(
    null,
  );

  // Feature flag for AI edit functionality
  const aiEditEnabled = useFeatureFlag("canvas_ai_palette");

  // Find selected artifact
  const selectedArtifact = useMemo(
    () => artifacts.find((a) => a.id === selectedArtifactId),
    [artifacts, selectedArtifactId],
  );

  // Determine which tabs to show based on content type
  const visibleTabs = useMemo((): TabType[] => {
    if (!selectedArtifact) return ["code"];
    return getVisibleTabs(selectedArtifact.contentType);
  }, [selectedArtifact]);

  // Determine artifact type for intelligence hooks
  const isCodeArtifact = useMemo(
    () =>
      selectedArtifact?.type === "code" ||
      selectedArtifact?.contentType === "code",
    [selectedArtifact],
  );

  const isDiagramArtifact = useMemo(
    () =>
      selectedArtifact?.type === "mermaid" ||
      selectedArtifact?.contentType === "mermaid",
    [selectedArtifact],
  );

  // Track if user has triggered AI analysis (opt-in pattern)
  const [hasTriggeredCodeAnalysis, setHasTriggeredCodeAnalysis] =
    useState(false);
  const [hasTriggeredDiagramAnalysis, setHasTriggeredDiagramAnalysis] =
    useState(false);

  // Canvas Intelligence: Code Analysis (gated by enableAI and feature flag)
  const codeAnalysis = useCodeAnalysis({
    userId: userId ?? "default-user",
    sessionId: sessionId ?? "default-session",
    code: isCodeArtifact && selectedArtifact ? selectedArtifact.content : "",
    language: selectedArtifact?.editMetadata?.language,
    enabled: enableAI && aiEditEnabled && isCodeArtifact && !!selectedArtifact,
  });

  // Canvas Intelligence: Diagram Analysis (gated by enableAI and feature flag)
  const diagramAnalysis = useDiagramAnalysis({
    userId: userId ?? "default-user",
    sessionId: sessionId ?? "default-session",
    diagramCode:
      isDiagramArtifact && selectedArtifact ? selectedArtifact.content : "",
    enabled:
      enableAI && aiEditEnabled && isDiagramArtifact && !!selectedArtifact,
  });

  // Auto-select first artifact if none selected
  useEffect(() => {
    const firstArtifact = artifacts[0];
    if (artifacts.length > 0 && !selectedArtifactId && firstArtifact) {
      dispatch(setSelectedArtifactId(firstArtifact.id));
    }
  }, [artifacts, selectedArtifactId, dispatch]);

  // Handle artifact selection
  const handleArtifactSelect = useCallback(
    (artifact: CanvasArtifactType) => {
      dispatch(setSelectedArtifactId(artifact.id));
      onArtifactSelect?.(artifact);
      setIsEditing(false);
    },
    [dispatch, onArtifactSelect],
  );

  // Handle artifact tab close
  const handleArtifactClose = useCallback(
    (artifactId: string) => {
      dispatch(removeFromTabOrder(artifactId));
    },
    [dispatch],
  );

  // Handle tab reorder
  const handleTabReorder = useCallback(
    (newOrder: string[]) => {
      dispatch(setTabOrder(newOrder));
    },
    [dispatch],
  );

  // Handle duplicate (placeholder - needs backend integration)
  const handleDuplicate = useCallback((_artifactId: string) => {
    // TODO: Implement artifact duplication
  }, []);

  // Handle export (placeholder - needs backend integration)
  const handleExport = useCallback((_artifactId: string) => {
    // TODO: Implement artifact export
  }, []);

  // Handle content change
  const handleContentChange = useCallback(
    (content: string) => {
      setEditContent(content);
      if (selectedArtifactId) {
        onContentChange?.(selectedArtifactId, content);
      }
    },
    [selectedArtifactId, onContentChange],
  );

  // Handle save
  const handleSave = useCallback(() => {
    if (selectedArtifactId && editContent) {
      onSave?.(selectedArtifactId, editContent);
    }
    setIsEditing(false);
  }, [selectedArtifactId, editContent, onSave]);

  // Handle edit mode
  const handleEdit = useCallback(() => {
    if (selectedArtifact) {
      setEditContent(selectedArtifact.content);
      setIsEditing(true);
    }
  }, [selectedArtifact]);

  // Handle cancel
  const handleCancel = useCallback(() => {
    setIsEditing(false);
    setEditContent("");
  }, []);

  // AI Edit handlers (Phase 4)
  const handleAiEditApply = useCallback(
    (newContent: string) => {
      if (selectedArtifactId) {
        onContentChange?.(selectedArtifactId, newContent);
        onSave?.(selectedArtifactId, newContent);
      }
      setAiEditVisible(false);
      setAiEditSelection(null);
    },
    [selectedArtifactId, onContentChange, onSave],
  );

  const handleAiEditCancel = useCallback(() => {
    setAiEditVisible(false);
    setAiEditSelection(null);
  }, []);

  // Handle AI edit request (Cmd+E or context menu)
  const handleRequestAiEdit = useCallback(() => {
    if (selectedArtifact) {
      // Create a mock selection (entire content) - in practice, this would
      // come from user text selection in the editor
      setAiEditSelection({
        start: { line: 1, column: 0 },
        end: { line: selectedArtifact.content.split("\n").length, column: 0 },
        content: selectedArtifact.content,
      });
      setAiEditVisible(true);
    }
  }, [selectedArtifact]);

  // Keyboard shortcut for AI edit (Cmd+E) - gated by canvas_ai_palette feature flag
  useEffect(() => {
    if (!aiEditEnabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "e" && selectedArtifact) {
        e.preventDefault();
        handleRequestAiEdit();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [selectedArtifact, handleRequestAiEdit, aiEditEnabled]);

  // Empty state
  if (artifacts.length === 0) {
    return (
      <div
        data-testid="canvas-workspace"
        className={cn(
          "flex flex-col items-center justify-center h-full",
          "bg-neutral-1",
          className,
        )}
      >
        <FileCode2
          size={48}
          className="text-neutral-11 mb-4"
        />
        <p className="text-neutral-11">No artifacts</p>
        <p className="text-sm text-neutral-11">
          Artifacts will appear here when generated
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="canvas-workspace"
      className={cn("flex flex-col h-full", className)}
    >
      {/* Artifact tabs */}
      <ArtifactTabBar
        artifacts={artifacts}
        tabOrder={effectiveTabOrder}
        selectedId={selectedArtifactId}
        onSelect={handleArtifactSelect}
        onClose={handleArtifactClose}
        onRename={onRenameArtifact ?? (() => {})}
        onDuplicate={handleDuplicate}
        onExport={handleExport}
        onReorder={handleTabReorder}
      />
      {/* Main workspace area - single pane with tab switching */}
      <div
        data-testid="panel-editor"
        className="flex-1 flex flex-col overflow-hidden"
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-5">
          <CanvasTabs
            activeTab={activeTab}
            onTabChange={setActiveTab}
            visibleTabs={visibleTabs}
            disabledTabs={isEditing ? ["preview", "data"] : []}
          />
          <div className="flex items-center gap-3">
            {/* AI Intelligence Indicator */}
            {enableAI && aiEditEnabled && selectedArtifact && (
              <div
                data-testid="ai-intelligence-indicator"
                className="flex items-center gap-1.5 text-xs"
              >
                {/* Code Analysis Indicator */}
                {isCodeArtifact && (
                  <>
                    {!hasTriggeredCodeAnalysis && !codeAnalysis.isLoading ? (
                      <Button
                        type="button"
                        data-testid="analyze-code-trigger"
                        onClick={() => {
                          setHasTriggeredCodeAnalysis(true);
                          codeAnalysis.refetch();
                        }}
                        className={cn(
                          "flex items-center gap-1 px-2 py-1 text-xs font-medium rounded",
                          "bg-primary-3 text-primary-11 hover:bg-primary-4",
                          "bg-primary-4 dark:text-primary-11 dark:hover:bg-primary-a6",
                          "transition-colors",
                        )}
                      >
                        <Sparkles size={12} aria-hidden="true" />
                        Analyze
                      </Button>
                    ) : codeAnalysis.isLoading ? (
                      <span className="flex items-center gap-1 text-neutral-11">
                        <Loader2
                          size={12}
                          className="animate-spin"
                          aria-hidden="true"
                        />
                        <span>Analyzing...</span>
                      </span>
                    ) : codeAnalysis.qualityScore !== null ? (
                      <Tooltip
                        content={
                          <div className="space-y-1 min-w-32">
                            <div className="font-medium">Code Quality</div>
                            <div className="flex items-center gap-1">
                              <span>Score:</span>
                              <span
                                className={cn(
                                  "font-medium",
                                  codeAnalysis.qualityScore >= 80
                                    ? "text-success-7"
                                    : codeAnalysis.qualityScore >= 60
                                      ? "text-warning-11"
                                      : "text-error-7",
                                )}
                              >
                                {codeAnalysis.qualityScore}/100
                              </span>
                            </div>
                            {codeAnalysis.complexity !== null && (
                              <div>Complexity: {codeAnalysis.complexity}</div>
                            )}
                            {codeAnalysis.issues.length > 0 && (
                              <div className="text-warning-11">
                                {codeAnalysis.issues.length} issue
                                {codeAnalysis.issues.length > 1 ? "s" : ""}
                              </div>
                            )}
                          </div>
                        }
                        position="bottom"
                      >
                        <span
                          className={cn(
                            "flex items-center gap-1 px-1.5 py-0.5 rounded",
                            codeAnalysis.qualityScore >= 80
                              ? "bg-success-a2 text-success-11 dark:text-success-11"
                              : codeAnalysis.qualityScore >= 60
                                ? "bg-warning-a2 text-warning-11 dark:text-warning-11"
                                : "bg-error-a2 text-error-11 dark:text-error-11",
                          )}
                        >
                          <Sparkles size={12} aria-hidden="true" />
                          <span>{codeAnalysis.qualityScore}</span>
                        </span>
                      </Tooltip>
                    ) : null}
                  </>
                )}

                {/* Diagram Analysis Indicator */}
                {isDiagramArtifact && (
                  <>
                    {!hasTriggeredDiagramAnalysis &&
                    !diagramAnalysis.isLoading ? (
                      <Button
                        type="button"
                        data-testid="analyze-diagram-trigger"
                        onClick={() => {
                          setHasTriggeredDiagramAnalysis(true);
                          diagramAnalysis.refetch();
                        }}
                        className={cn(
                          "flex items-center gap-1 px-2 py-1 text-xs font-medium rounded",
                          "bg-primary-3 text-primary-11 hover:bg-primary-4",
                          "bg-primary-4 dark:text-primary-11 dark:hover:bg-primary-a6",
                          "transition-colors",
                        )}
                      >
                        <Sparkles size={12} aria-hidden="true" />
                        Validate
                      </Button>
                    ) : diagramAnalysis.isLoading ? (
                      <span className="flex items-center gap-1 text-neutral-11">
                        <Loader2
                          size={12}
                          className="animate-spin"
                          aria-hidden="true"
                        />
                        <span>Validating...</span>
                      </span>
                    ) : diagramAnalysis.isValid !== null ? (
                      <Tooltip
                        content={
                          <div className="space-y-1 min-w-32">
                            <div className="font-medium">Diagram Analysis</div>
                            <div className="flex items-center gap-1">
                              <span>Type:</span>
                              <span className="capitalize">
                                {diagramAnalysis.diagramType || "unknown"}
                              </span>
                            </div>
                            {diagramAnalysis.nodeCount !== null && (
                              <div>Nodes: {diagramAnalysis.nodeCount}</div>
                            )}
                            {diagramAnalysis.edgeCount !== null && (
                              <div>Edges: {diagramAnalysis.edgeCount}</div>
                            )}
                            {diagramAnalysis.issues.length > 0 && (
                              <div className="text-warning-11">
                                {diagramAnalysis.issues.length} issue
                                {diagramAnalysis.issues.length > 1 ? "s" : ""}
                              </div>
                            )}
                          </div>
                        }
                        position="bottom"
                      >
                        <span
                          className={cn(
                            "flex items-center gap-1 px-1.5 py-0.5 rounded",
                            diagramAnalysis.isValid
                              ? "bg-success-a2 text-success-11 dark:text-success-11"
                              : "bg-error-a2 text-error-11 dark:text-error-11",
                          )}
                        >
                          {diagramAnalysis.isValid ? (
                            <CheckCircle size={12} aria-hidden="true" />
                          ) : (
                            <AlertTriangle size={12} aria-hidden="true" />
                          )}
                          <span>
                            {diagramAnalysis.isValid ? "Valid" : "Invalid"}
                          </span>
                        </span>
                      </Tooltip>
                    ) : null}
                  </>
                )}
              </div>
            )}
            {selectedArtifact && (
              <ArtifactActions
                artifact={selectedArtifact}
                compact
                disabled={isEditing}
              />
            )}
          </div>
        </div>

        {/* Tab-based content area - single pane */}
        <div className="flex-1 overflow-auto p-4">
          {/* Code View */}
          {selectedArtifact && activeTab === "code" && (
            <div data-testid="code-view">
              <CanvasArtifact
                artifact={selectedArtifact}
                editable
                isEditing={isEditing}
                showLineNumbers
                onChange={handleContentChange}
                onSave={handleSave}
                onCancel={handleCancel}
                onEdit={handleEdit}
                ariaLabel={`${selectedArtifact.title || "Artifact"} - Code`}
              />
            </div>
          )}

          {/* Preview View */}
          {selectedArtifact && activeTab === "preview" && (
            <div data-testid="preview-view">
              {selectedArtifact.contentType === "mermaid" ? (
                <Suspense
                  fallback={
                    <div className="flex items-center justify-center h-32">
                      <Loader2 className="animate-spin text-neutral-11" />
                    </div>
                  }
                >
                  <InteractiveMermaidDiagram code={selectedArtifact.content} />
                </Suspense>
              ) : (
                <CanvasArtifact
                  artifact={selectedArtifact}
                  editable={false}
                  showLineNumbers={false}
                  ariaLabel={`${selectedArtifact.title || "Artifact"} - Preview`}
                />
              )}
            </div>
          )}

          {/* Data View */}
          {selectedArtifact && activeTab === "data" && (
            <div data-testid="data-view">
              <pre className="text-sm text-neutral-11 whitespace-pre-wrap font-mono bg-neutral-1 p-4 rounded-lg overflow-auto">
                {selectedArtifact.contentType === "json"
                  ? JSON.stringify(
                      JSON.parse(selectedArtifact.content),
                      null,
                      2,
                    )
                  : selectedArtifact.content}
              </pre>
            </div>
          )}
        </div>
      </div>
      {/* AI Edit Overlay (Phase 4) - gated by canvas_ai_palette feature flag */}
      {/* Lazy-loaded to reduce initial bundle size */}
      {aiEditEnabled && aiEditSelection && (
        <Suspense fallback={null}>
          <LazyAIEditOverlay
            selection={aiEditSelection}
            isVisible={aiEditVisible}
            onApply={handleAiEditApply}
            onCancel={handleAiEditCancel}
            className="top-1/4 left-1/2 -translate-x-1/2"
          />
        </Suspense>
      )}
    </div>
  );
}
