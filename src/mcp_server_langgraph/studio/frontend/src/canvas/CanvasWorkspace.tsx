/**
 * CanvasWorkspace - Phase 1
 *
 * Main Canvas workspace component that manages the artifact display area
 * with resizable panels for preview and editing.
 */
import { useState, useCallback, useMemo, useEffect, Suspense } from "react";
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { FileCode2, Clock, Code, User, Bot } from "lucide-react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  selectSelectedArtifactId,
  setSelectedArtifactId,
} from "../store/slices/canvasSlice";
import { CanvasArtifact } from "./CanvasArtifact";
import { CanvasTabs, type TabType } from "./CanvasTabs";
import { ArtifactActions } from "./ArtifactActions";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";
import { cn } from "../utils/cn";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import { InlineEdit } from "../components/UI/InlineEdit";
import { Tooltip } from "../components/UI/Tooltip";

// AI Components (Phase 4) - lazy-loaded for reduced bundle size
import { LazyAIEditOverlay, type Selection } from "../ai/lazy";

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
    <div className="flex gap-1 p-2 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
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
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Code size={12} />
              <span className="capitalize">{artifact.type}</span>
              {language && (
                <>
                  <span className="text-gray-600">•</span>
                  <span className="capitalize">{language}</span>
                </>
              )}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <FileCode2 size={12} />
              <span>
                {lineCount} line{lineCount === 1 ? "" : "s"}
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Clock size={12} />
              <span>Created {formatArtifactDate(artifact.createdAt)}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              {isAI ? (
                <>
                  <Bot size={12} className="text-purple-400" />
                  <span className="text-purple-400">AI Generated</span>
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
          <button
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
                "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700",
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
                className="w-1.5 h-1.5 rounded-full bg-purple-500"
              />
            )}
          </button>
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
// Resize Handle Component
// =============================================================================

function ResizeHandle() {
  return (
    <PanelResizeHandle
      data-testid="resize-handle"
      className={cn(
        "w-1 hover:w-2 transition-all",
        "bg-transparent hover:bg-primary-500/30",
        "cursor-col-resize",
      )}
    />
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
          "bg-gray-50 dark:bg-gray-800",
          className,
        )}
      >
        <FileCode2 size={48} className="text-gray-400 mb-4" />
        <p className="text-gray-500 dark:text-gray-400">No artifacts</p>
        <p className="text-sm text-gray-400 dark:text-gray-500">
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

      {/* Main workspace area */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup data-testid="panel-group" direction="horizontal">
          {/* Preview/Editor panel */}
          <Panel
            id="editor"
            data-testid="panel-editor"
            defaultSize={60}
            minSize={30}
          >
            <div className="flex flex-col h-full">
              {/* Toolbar */}
              <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                <CanvasTabs
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  disabledTabs={isEditing ? ["preview", "data"] : []}
                />
                {selectedArtifact && (
                  <ArtifactActions
                    artifact={selectedArtifact}
                    compact
                    disabled={isEditing}
                  />
                )}
              </div>

              {/* Content area */}
              <div className="flex-1 overflow-auto p-4">
                {selectedArtifact && (
                  <CanvasArtifact
                    artifact={selectedArtifact}
                    editable
                    isEditing={isEditing}
                    showLineNumbers
                    onChange={handleContentChange}
                    onSave={handleSave}
                    onCancel={handleCancel}
                    onEdit={handleEdit}
                    ariaLabel={`${selectedArtifact.title || "Artifact"} - Editor`}
                  />
                )}
              </div>
            </div>
          </Panel>

          <ResizeHandle />

          {/* Preview panel (for split view) */}
          <Panel
            id="preview"
            data-testid="panel-preview"
            defaultSize={40}
            minSize={20}
          >
            <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
              <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  Preview
                </span>
              </div>
              <div className="flex-1 overflow-auto p-4">
                {selectedArtifact && (
                  <CanvasArtifact
                    artifact={selectedArtifact}
                    editable={false}
                    showLineNumbers={false}
                    ariaLabel={`${selectedArtifact.title || "Artifact"} - Preview`}
                  />
                )}
              </div>
            </div>
          </Panel>
        </PanelGroup>
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
