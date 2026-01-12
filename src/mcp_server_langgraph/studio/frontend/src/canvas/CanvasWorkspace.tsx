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
  Clock,
  Code,
  User,
  Bot,
  Sparkles,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectSelectedArtifactId,
  setSelectedArtifactId,
} from "../store/slices/canvasSlice";
import { CanvasArtifact } from "./CanvasArtifact";
import { CanvasTabs, type TabType } from "./CanvasTabs";
import { getVisibleTabs } from "./canvasUtils";
import { ArtifactActions } from "./ArtifactActions";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";
import { cn } from "../utils/cn";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { InlineEdit } from "../components/UI/InlineEdit";
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
// Artifact Tabs Component
// =============================================================================

interface ArtifactTabBarProps {
  artifacts: CanvasArtifactType[];
  selectedId: string | null;
  onSelect: (artifact: CanvasArtifactType) => void;
  enableEdit?: boolean;
  onRename?: (artifactId: string, title: string) => void;
  enableHover?: boolean;
}

/** Format date to relative time */
function formatArtifactDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "yesterday";
  return date.toLocaleDateString();
}

/** Get line count from content */
function getLineCount(content: string): number {
  return content.split("\n").length;
}

function ArtifactTabBar({
  artifacts,
  selectedId,
  onSelect,
  enableEdit = false,
  onRename,
  enableHover = false,
}: ArtifactTabBarProps) {
  return (
    <div className="flex gap-1 p-2 border-b border-neutral-200 dark:border-neutral-700 overflow-x-auto">
      {artifacts.map((artifact) => {
        const isActive = artifact.id === selectedId;
        const isAI =
          artifact.editMetadata?.editedBy === "ai-generation" ||
          artifact.editMetadata?.editedBy === "ai-suggestion";
        const displayTitle =
          artifact.title || `Artifact ${artifact.id.slice(0, 6)}`;

        const handleRename = (newTitle: string) => {
          if (onRename) {
            onRename(artifact.id, newTitle);
          }
        };

        // Build hover tooltip content
        const lineCount = getLineCount(artifact.content);
        const language =
          artifact.editMetadata?.language || artifact.contentType;
        const hoverContent = (
          <div className="space-y-1.5 min-w-40 max-w-56">
            <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-400">
              <Code size={12} />
              <span className="capitalize">{artifact.type}</span>
              {language && (
                <>
                  <span className="text-neutral-600 dark:text-neutral-300">
                    •
                  </span>
                  <span className="capitalize">{language}</span>
                </>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-400">
              <FileCode2 size={12} />
              <span>
                {lineCount} line{lineCount === 1 ? "" : "s"}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-400">
              <Clock size={12} />
              <span>Created {formatArtifactDate(artifact.createdAt)}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-neutral-400 dark:text-neutral-400">
              {isAI ? (
                <>
                  <Bot size={12} className="text-insight-400" />
                  <span className="text-insight-400">AI Generated</span>
                </>
              ) : (
                <>
                  <User size={12} />
                  <span>User Created</span>
                </>
              )}
            </div>
          </div>
        );

        const tabButton = (
          <Button
            key={artifact.id}
            data-testid={`artifact-tab-${artifact.id}`}
            type="button"
            onClick={() => onSelect(artifact)}
            className={cn(
              "artifact-tab flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap",
              "transition-colors",
              isActive &&
                "active bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300",
              !isActive &&
                "text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
            )}
          >
            <FileCode2 size={14} />
            {enableEdit ? (
              <InlineEdit
                value={displayTitle}
                onSave={handleRename}
                placeholder="Artifact title"
                aria-label={`Rename artifact ${displayTitle}`}
                className="max-w-32"
              />
            ) : (
              <span className="max-w-32 truncate">{displayTitle}</span>
            )}
            {isAI && (
              <span
                data-testid="ai-badge"
                className="w-1.5 h-1.5 rounded-full bg-insight-500"
              />
            )}
          </Button>
        );

        return enableHover ? (
          <Tooltip
            key={artifact.id}
            content={hoverContent}
            position="bottom"
            delay={200}
          >
            {tabButton}
          </Tooltip>
        ) : (
          tabButton
        );
      })}
    </div>
  );
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
  enableArtifactEdit = false,
  onRenameArtifact,
  enableArtifactHover = false,
  userId,
  sessionId,
  persona: _persona,
  enableAI = false,
}: CanvasWorkspaceProps) {
  const dispatch = useAppDispatch();
  const selectedArtifactId = useAppSelector(selectSelectedArtifactId);

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
          "bg-neutral-50 dark:bg-neutral-800",
          className,
        )}
      >
        <FileCode2
          size={48}
          className="text-neutral-400 dark:text-neutral-400 mb-4"
        />
        <p className="text-neutral-500 dark:text-neutral-400">No artifacts</p>
        <p className="text-sm text-neutral-400 dark:text-neutral-400">
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
        selectedId={selectedArtifactId}
        onSelect={handleArtifactSelect}
        enableEdit={enableArtifactEdit}
        onRename={onRenameArtifact}
        enableHover={enableArtifactHover}
      />
      {/* Main workspace area - single pane with tab switching */}
      <div
        data-testid="panel-editor"
        className="flex-1 flex flex-col overflow-hidden"
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700">
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
                          "bg-primary-100 text-primary-700 hover:bg-primary-200",
                          "dark:bg-primary-900/30 dark:text-primary-300 dark:hover:bg-primary-900/50",
                          "transition-colors",
                        )}
                      >
                        <Sparkles size={12} aria-hidden="true" />
                        Analyze
                      </Button>
                    ) : codeAnalysis.isLoading ? (
                      <span className="flex items-center gap-1 text-neutral-400 dark:text-neutral-400">
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
                                    ? "text-success-400"
                                    : codeAnalysis.qualityScore >= 60
                                      ? "text-warning-400"
                                      : "text-error-400",
                                )}
                              >
                                {codeAnalysis.qualityScore}/100
                              </span>
                            </div>
                            {codeAnalysis.complexity !== null && (
                              <div>Complexity: {codeAnalysis.complexity}</div>
                            )}
                            {codeAnalysis.issues.length > 0 && (
                              <div className="text-warning-400">
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
                              ? "bg-success-500/10 text-success-600 dark:text-success-400"
                              : codeAnalysis.qualityScore >= 60
                                ? "bg-warning-500/10 text-warning-600 dark:text-warning-400"
                                : "bg-error-500/10 text-error-600 dark:text-error-400",
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
                          "bg-primary-100 text-primary-700 hover:bg-primary-200",
                          "dark:bg-primary-900/30 dark:text-primary-300 dark:hover:bg-primary-900/50",
                          "transition-colors",
                        )}
                      >
                        <Sparkles size={12} aria-hidden="true" />
                        Validate
                      </Button>
                    ) : diagramAnalysis.isLoading ? (
                      <span className="flex items-center gap-1 text-neutral-400 dark:text-neutral-400">
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
                              <div className="text-warning-400">
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
                              ? "bg-success-500/10 text-success-600 dark:text-success-400"
                              : "bg-error-500/10 text-error-600 dark:text-error-400",
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
                      <Loader2 className="animate-spin text-neutral-400 dark:text-neutral-400" />
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
              <pre className="text-sm text-neutral-600 dark:text-neutral-400 whitespace-pre-wrap font-mono bg-neutral-50 dark:bg-neutral-800 p-4 rounded-lg overflow-auto">
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
