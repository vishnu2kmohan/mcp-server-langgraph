/**
 * NodePalette Component
 *
 * Sidebar component with draggable node types for React Flow canvas.
 * Uses Pointer Events API for cross-platform drag-and-drop support.
 *
 * Features:
 * - Drag-and-drop nodes to canvas
 * - Search/filter nodes
 * - Category grouping
 * - Click to add at center
 * - Consistent design system styling
 */

import {
  useState,
  useCallback,
  type DragEvent,
  type PointerEvent,
} from "react";
import {
  Play,
  Flag,
  Bot,
  Wrench,
  GitBranch,
  UserCheck,
  Settings,
  Search,
  GripVertical,
} from "lucide-react";

export type NodeType =
  | "start"
  | "end"
  | "llm"
  | "tool"
  | "conditional"
  | "approval"
  | "custom";

export type NodeCategory = "flow" | "processing" | "control" | "advanced";

interface NodeTemplate {
  type: NodeType;
  label: string;
  icon: React.ReactNode;
  description: string;
  category: NodeCategory;
  color: string;
}

/**
 * Design System Colors
 * Consistent color palette used across all components
 */
const COLORS = {
  // Node type colors (semantic)
  start: "bg-emerald-500 dark:bg-emerald-600",
  end: "bg-rose-500 dark:bg-rose-600",
  llm: "bg-violet-500 dark:bg-violet-600",
  tool: "bg-amber-500 dark:bg-amber-600",
  conditional: "bg-sky-500 dark:bg-sky-600",
  approval: "bg-pink-500 dark:bg-pink-600",
  custom: "bg-slate-500 dark:bg-slate-600",
  // Border colors for cards
  startBorder:
    "border-emerald-200 dark:border-emerald-700 hover:border-emerald-400 dark:hover:border-emerald-500",
  endBorder:
    "border-rose-200 dark:border-rose-700 hover:border-rose-400 dark:hover:border-rose-500",
  llmBorder:
    "border-violet-200 dark:border-violet-700 hover:border-violet-400 dark:hover:border-violet-500",
  toolBorder:
    "border-amber-200 dark:border-amber-700 hover:border-amber-400 dark:hover:border-amber-500",
  conditionalBorder:
    "border-sky-200 dark:border-sky-700 hover:border-sky-400 dark:hover:border-sky-500",
  approvalBorder:
    "border-pink-200 dark:border-pink-700 hover:border-pink-400 dark:hover:border-pink-500",
  customBorder:
    "border-slate-200 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500",
};

const NODE_TEMPLATES: NodeTemplate[] = [
  // Flow control nodes
  {
    type: "start",
    label: "Start",
    icon: <Play size={16} />,
    description: "Entry point of the workflow",
    category: "flow",
    color: COLORS.start,
  },
  {
    type: "end",
    label: "End",
    icon: <Flag size={16} />,
    description: "Exit point of the workflow",
    category: "flow",
    color: COLORS.end,
  },
  // Processing nodes
  {
    type: "llm",
    label: "LLM",
    icon: <Bot size={16} />,
    description: "Language model call",
    category: "processing",
    color: COLORS.llm,
  },
  {
    type: "tool",
    label: "Tool",
    icon: <Wrench size={16} />,
    description: "Execute a tool/function",
    category: "processing",
    color: COLORS.tool,
  },
  // Control flow nodes
  {
    type: "conditional",
    label: "Conditional",
    icon: <GitBranch size={16} />,
    description: "Branch based on condition",
    category: "control",
    color: COLORS.conditional,
  },
  {
    type: "approval",
    label: "Approval",
    icon: <UserCheck size={16} />,
    description: "Human-in-the-loop approval",
    category: "control",
    color: COLORS.approval,
  },
  // Advanced nodes
  {
    type: "custom",
    label: "Custom",
    icon: <Settings size={16} />,
    description: "Custom code execution",
    category: "advanced",
    color: COLORS.custom,
  },
];

const CATEGORY_LABELS: Record<NodeCategory, string> = {
  flow: "Flow Control",
  processing: "Processing",
  control: "Control",
  advanced: "Advanced",
};

const CATEGORY_ORDER: NodeCategory[] = [
  "flow",
  "processing",
  "control",
  "advanced",
];

export interface NodePaletteProps {
  onAddNode?: (type: NodeType, position?: { x: number; y: number }) => void;
  className?: string;
  isCollapsed?: boolean;
}

/**
 * Draggable node component using React Flow's recommended pattern
 * Uses both HTML5 drag-and-drop and Pointer Events for cross-platform support
 */
function DraggableNode({
  template,
  onAddNode,
}: {
  template: NodeTemplate;
  onAddNode?: (type: NodeType) => void;
}) {
  const [isDragging, setIsDragging] = useState(false);

  // HTML5 Drag and Drop - for desktop browsers
  const onDragStart = useCallback(
    (event: DragEvent) => {
      // Set the data transfer with node type
      event.dataTransfer.setData("application/reactflow", template.type);
      event.dataTransfer.effectAllowed = "move";
      setIsDragging(true);
    },
    [template.type],
  );

  const onDragEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Pointer Events - for touch devices
  const onPointerDown = useCallback((event: PointerEvent) => {
    // Only handle on touch devices (primary pointer is touch)
    if (event.pointerType !== "touch") return;

    // Capture pointer for tracking
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    setIsDragging(true);
  }, []);

  const onPointerUp = useCallback(
    (event: PointerEvent) => {
      if (!isDragging) return;

      // Release capture
      (event.target as HTMLElement).releasePointerCapture(event.pointerId);
      setIsDragging(false);

      // For touch, add node at click position (fallback)
      if (onAddNode && event.pointerType === "touch") {
        onAddNode(template.type);
      }
    },
    [isDragging, onAddNode, template.type],
  );

  // Click handler for click-to-add
  const handleClick = useCallback(() => {
    onAddNode?.(template.type);
  }, [onAddNode, template.type]);

  // Get border color based on type
  const getBorderColor = () => {
    switch (template.type) {
      case "start":
        return COLORS.startBorder;
      case "end":
        return COLORS.endBorder;
      case "llm":
        return COLORS.llmBorder;
      case "tool":
        return COLORS.toolBorder;
      case "conditional":
        return COLORS.conditionalBorder;
      case "approval":
        return COLORS.approvalBorder;
      case "custom":
        return COLORS.customBorder;
      default:
        return "border-gray-200 dark:border-gray-700";
    }
  };

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onClick={handleClick}
      className={`
        group flex items-center gap-3 p-3 rounded-lg border-2 cursor-grab
        bg-white dark:bg-gray-800 ${getBorderColor()}
        transition-all duration-150 ease-out
        hover:shadow-md hover:-translate-y-0.5
        active:cursor-grabbing active:shadow-lg active:scale-[1.02]
        ${isDragging ? "opacity-50 shadow-lg scale-[1.02]" : ""}
      `}
      title={`Drag to add ${template.label} node, or click to add at center`}
      role="button"
      aria-label={`Add ${template.label} node`}
      data-testid={`node-${template.type}`}
    >
      {/* Drag handle indicator */}
      <div className="flex-shrink-0 text-gray-400 dark:text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity">
        <GripVertical size={14} />
      </div>

      {/* Icon with colored background */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-lg ${template.color} flex items-center justify-center text-white shadow-sm`}
      >
        {template.icon}
      </div>

      {/* Label and description */}
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
          {template.label}
        </div>
        <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
          {template.description}
        </div>
      </div>
    </div>
  );
}

export function NodePalette({
  onAddNode,
  className = "",
  isCollapsed = false,
}: NodePaletteProps) {
  const [searchQuery, setSearchQuery] = useState("");

  // Filter nodes based on search query
  const filteredTemplates = NODE_TEMPLATES.filter(
    (template) =>
      template.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      template.description.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // Group by category
  const groupedTemplates = CATEGORY_ORDER.map((category) => ({
    category,
    label: CATEGORY_LABELS[category],
    templates: filteredTemplates.filter((t) => t.category === category),
  })).filter((group) => group.templates.length > 0);

  if (isCollapsed) {
    // Collapsed view - just icons
    return (
      <aside
        className={`w-16 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 p-2 flex flex-col gap-2 ${className}`}
        data-testid="node-palette"
      >
        <h2 className="sr-only">Node Types</h2>
        {NODE_TEMPLATES.map((template) => (
          <button
            key={template.type}
            onClick={() => onAddNode?.(template.type)}
            className={`
              w-12 h-12 rounded-lg ${template.color} text-white
              flex items-center justify-center
              hover:opacity-90 transition-opacity
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            `}
            title={`Add ${template.label}: ${template.description}`}
            aria-label={`Add ${template.label} node`}
          >
            {template.icon}
          </button>
        ))}
      </aside>
    );
  }

  return (
    <aside
      className={`w-72 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col ${className}`}
      data-testid="node-palette"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          Node Types
        </h2>

        {/* Search input */}
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search nodes..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg
              placeholder:text-gray-400 dark:placeholder:text-gray-500
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
              transition-colors"
            aria-label="Search node types"
          />
        </div>
      </div>

      {/* Node list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {groupedTemplates.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No nodes match your search
          </p>
        ) : (
          groupedTemplates.map((group) => (
            <div key={group.category}>
              <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                {group.label}
              </h3>
              <div className="space-y-2">
                {group.templates.map((template) => (
                  <DraggableNode
                    key={template.type}
                    template={template}
                    onAddNode={onAddNode}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer hint */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
          Drag nodes to canvas or click to add
        </p>
      </div>
    </aside>
  );
}
