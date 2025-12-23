/**
 * Studio Handlers - StudioOrchestrator MSW Support
 *
 * MSW handlers for Studio AI endpoints, supporting the unified
 * StudioOrchestrator pattern for all intelligence types.
 *
 * Endpoints:
 * - POST /api/v1/studio/analyze - Unified analysis for all 8 task categories
 * - GET /api/v1/studio/templates - List available templates
 * - POST /api/v1/studio/suggestions - Studio suggestions
 */

import { http, HttpResponse, delay } from "msw";

// =============================================================================
// Types
// =============================================================================

type TaskCategory =
  | "session"
  | "conversation"
  | "canvas"
  | "diagram"
  | "trace"
  | "hitl"
  | "command"
  | "ux";

interface StudioTask {
  category: TaskCategory;
  type: string;
  data?: Record<string, unknown>;
}

interface StudioAnalyzeRequest {
  user_id: string;
  session_id?: string;
  persona?: string;
  tasks: StudioTask[];
  context?: Record<string, unknown>;
}

interface StudioAnalyzeResponse {
  user_id: string;
  session_id: string;
  analyses: Record<string, unknown>;
  cross_insights: string[];
  failed_analyses: string[];
  total_cost: string;
}

interface StudioTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  content: string;
}

// =============================================================================
// Mock Data Generators
// =============================================================================

const generateSessionSummary = () => ({
  summary: "User discussed project architecture and implementation patterns.",
  key_topics: ["architecture", "design patterns", "implementation"],
  message_count: 15,
  sentiment: "neutral",
});

const generateSessionGroups = () => ({
  groups: [
    {
      topic: "Frontend Development",
      session_ids: ["s1", "s2", "s3"],
      confidence: 0.85,
    },
    {
      topic: "API Integration",
      session_ids: ["s4", "s5"],
      confidence: 0.78,
    },
  ],
  ungrouped: ["s6"],
});

const generateSessionSimilarity = (sessionId?: string) => ({
  source_session_id: sessionId || "session-123",
  similar_sessions: [
    {
      session_id: "session-456",
      similarity_score: 0.92,
      common_topics: ["React", "hooks"],
    },
    {
      session_id: "session-789",
      similarity_score: 0.78,
      common_topics: ["React"],
    },
  ],
});

const generateIntentDetection = (query?: string) => ({
  intent: query?.includes("create") ? "create" : "query",
  confidence: 0.87,
  sub_intents: ["file_operation", "code_generation"],
});

const generateContextOptimization = () => ({
  suggestions: [
    "Remove messages older than 10 turns",
    "Summarize repeated context",
  ],
  usage_percent: 75,
  recommended_action: "trim_old_messages",
});

const generateGoalTracking = () => ({
  primary_goal: "Implement authentication system",
  sub_goals: ["Setup OAuth", "Add session management", "Create login UI"],
  progress_percent: 45,
  blockers: [],
});

const generateArtifactTypeSuggestion = (content?: string) => ({
  suggested_type: content?.includes("graph") ? "mermaid" : "code",
  confidence: 0.91,
  alternatives: ["markdown", "json"],
});

const generateCodeAnalysis = () => ({
  quality_score: 85,
  complexity: "medium",
  issues: [
    { type: "style", message: "Consider using const instead of let" },
  ],
  suggestions: ["Add error handling", "Extract repeated logic"],
});

const generateDiffExplanation = () => ({
  summary: "Added new function and refactored existing code",
  changes: [
    { type: "addition", description: "New helper function added" },
    { type: "modification", description: "Refactored main logic" },
  ],
  breaking_changes: false,
});

const generateDiagramAnalysis = (diagram?: string) => ({
  diagram_type: diagram?.includes("sequenceDiagram") ? "sequence" : "flowchart",
  is_valid: true,
  node_count: 5,
  edge_count: 4,
  issues: [],
});

const generateDiagramToCode = () => ({
  code: `class NodeA:
    def process(self):
        return NodeB().handle()

class NodeB:
    def handle(self):
        return "processed"`,
  language: "python",
  confidence: 0.82,
  explanation: "Generated Python classes from flowchart nodes",
});

const generateTraceSummary = () => ({
  summary: "Completed 5 LLM calls with 2 tool invocations in 3.2 seconds",
  total_duration_ms: 3200,
  step_count: 7,
  tool_call_count: 2,
  llm_call_count: 5,
});

const generateTraceAnomaly = () => ({
  anomalies: [
    { type: "slow_step", step_id: "step-3", severity: "warning" },
  ],
  bottlenecks: ["step-3"],
  health_score: 0.85,
});

const generateCostProjection = () => ({
  current_cost: "0.0234",
  projected_cost: "0.0450",
  budget_remaining: "4.9550",
  cost_by_model: {
    "gpt-4": "0.0200",
    "gpt-3.5-turbo": "0.0034",
  },
});

const generateTokenPrediction = () => ({
  current_tokens: 15000,
  projected_tokens: 45000,
  max_tokens: 128000,
  optimization_savings: 5000,
});

const generateRiskAssessment = (actionType?: string) => {
  const isHighRisk = actionType === "file_delete" || actionType === "system_command";
  return {
    risk_score: isHighRisk ? 0.85 : 0.25,
    risk_level: isHighRisk ? "high" : "low",
    risk_factors: isHighRisk
      ? ["Destructive operation", "Irreversible action"]
      : ["Standard operation"],
    recommendation: isHighRisk ? "require_review" : "approve",
  };
};

const generateDecisionHistory = () => ({
  similar_decisions: [
    { action: "file_write", decision: "approved", timestamp: new Date().toISOString() },
    { action: "file_write", decision: "approved", timestamp: new Date().toISOString() },
  ],
  approval_rate: 0.95,
  suggested_action: "approve",
});

const generateCommandInterpret = (query?: string) => ({
  interpreted_command: query?.includes("create") ? "create_file" : "query",
  parameters: query?.includes("Python")
    ? { language: "python", name: "new_file.py" }
    : {},
  confidence: 0.88,
});

const generateInlineSuggestions = (language?: string) => ({
  suggestions: [
    { text: "def function_name():", confidence: 0.9 },
    { text: "class ClassName:", confidence: 0.85 },
  ],
  language: language || "python",
  cursor_context: "start_of_definition",
});

const generateAiEdit = (instruction?: string) => ({
  edited_content: `def hello():
    """A greeting function."""
    return "Hello, World!"`,
  changes: [
    { type: "addition", line: 2, content: '"""A greeting function."""' },
  ],
  instruction_understood: instruction || "add docstring",
});

const generateNavPrediction = () => ({
  predicted_items: [
    { id: "chat", score: 0.95 },
    { id: "workflows", score: 0.72 },
    { id: "settings", score: 0.45 },
  ],
  current_context: "dashboard",
});

const generateContextualHelp = (context?: string) => ({
  help_topics: [
    { title: "Getting Started", relevance: 0.9 },
    { title: "Keyboard Shortcuts", relevance: 0.8 },
  ],
  quick_actions: ["Create new session", "Import workflow"],
  suggested_reading: ["User Guide", "API Reference"],
  context: context || "general",
});

const generateLearningPath = () => ({
  current_level: "intermediate",
  progress_percentage: 65,
  next_steps: [
    { title: "Advanced Workflows", difficulty: "hard" },
    { title: "Custom Tools", difficulty: "medium" },
  ],
  completed_topics: ["Basic Chat", "Sessions", "Simple Workflows"],
});

// =============================================================================
// Task Handler Mapping
// =============================================================================

const taskHandlers: Record<string, (task: StudioTask) => unknown> = {
  // Session Intelligence
  "session:session_summarize": () => generateSessionSummary(),
  "session:session_group": () => generateSessionGroups(),
  "session:session_similarity": (task) =>
    generateSessionSimilarity(task.data?.session_id as string),

  // Conversation Intelligence
  "conversation:intent_detect": (task) =>
    generateIntentDetection(task.data?.query as string),
  "conversation:context_optimize": () => generateContextOptimization(),
  "conversation:goal_track": () => generateGoalTracking(),

  // Canvas Intelligence
  "canvas:artifact_suggest_type": (task) =>
    generateArtifactTypeSuggestion(task.data?.content as string),
  "canvas:code_analyze": () => generateCodeAnalysis(),
  "canvas:diff_explain": () => generateDiffExplanation(),

  // Diagram Intelligence
  "diagram:diagram_analyze": (task) =>
    generateDiagramAnalysis(task.data?.diagram as string),
  "diagram:diagram_to_code": () => generateDiagramToCode(),

  // Trace Intelligence
  "trace:trace_summarize": () => generateTraceSummary(),
  "trace:trace_anomaly": () => generateTraceAnomaly(),
  "trace:cost_project": () => generateCostProjection(),
  "trace:token_predict": () => generateTokenPrediction(),

  // HITL Intelligence
  "hitl:risk_assess": (task) =>
    generateRiskAssessment(task.data?.action_type as string),
  "hitl:decision_history": () => generateDecisionHistory(),

  // Command Intelligence
  "command:command_interpret": (task) =>
    generateCommandInterpret(task.data?.query as string),
  "command:inline_suggest": (task) =>
    generateInlineSuggestions(task.data?.language as string),
  "command:ai_edit_generate": (task) =>
    generateAiEdit(task.data?.instruction as string),

  // UX Intelligence
  "ux:nav_prediction": () => generateNavPrediction(),
  "ux:contextual_help": (task) =>
    generateContextualHelp(task.data?.context as string),
  "ux:learning_path": () => generateLearningPath(),
};

// =============================================================================
// Cross-Insights Generator
// =============================================================================

const generateCrossInsights = (tasks: StudioTask[]): string[] => {
  const insights: string[] = [];

  const hasSession = tasks.some((t) => t.category === "session");
  const hasConversation = tasks.some((t) => t.category === "conversation");
  const hasCanvas = tasks.some((t) => t.category === "canvas");
  const hasTrace = tasks.some((t) => t.category === "trace");

  if (hasSession && hasConversation) {
    insights.push("Session goals align with current conversation intent");
  }
  if (hasCanvas && hasTrace) {
    insights.push("Artifact complexity correlates with trace duration");
  }
  if (tasks.length > 1) {
    insights.push("Multiple analysis types provide comprehensive context");
  }

  return insights;
};

// =============================================================================
// Response Builder
// =============================================================================

export const createStudioAnalyzeResponse = (
  request: StudioAnalyzeRequest,
): StudioAnalyzeResponse => {
  const analyses: Record<string, unknown> = {};
  const failedAnalyses: string[] = [];

  for (const task of request.tasks) {
    const handlerKey = `${task.category}:${task.type}`;
    const handler = taskHandlers[handlerKey];

    if (handler) {
      analyses[task.type] = handler(task);
    } else {
      failedAnalyses.push(handlerKey);
    }
  }

  const crossInsights = generateCrossInsights(request.tasks);

  // Calculate mock cost based on task count
  const baseCost = 0.001;
  const totalCost = (request.tasks.length * baseCost).toFixed(4);

  return {
    user_id: request.user_id,
    session_id: request.session_id || "",
    analyses,
    cross_insights: crossInsights,
    failed_analyses: failedAnalyses,
    total_cost: totalCost,
  };
};

// =============================================================================
// Mock Templates
// =============================================================================

const mockTemplates: StudioTemplate[] = [
  {
    id: "tpl-1",
    name: "Code Review",
    description: "Template for code review sessions",
    category: "development",
    content: "Review the following code for best practices...",
  },
  {
    id: "tpl-2",
    name: "Bug Investigation",
    description: "Template for investigating bugs",
    category: "debugging",
    content: "Analyze the following error and suggest fixes...",
  },
  {
    id: "tpl-3",
    name: "Documentation",
    description: "Template for generating documentation",
    category: "documentation",
    content: "Generate documentation for the following code...",
  },
];

// =============================================================================
// MSW Handlers
// =============================================================================

export const studioHandlers = [
  // POST /api/v1/studio/analyze - Unified analysis endpoint
  http.post("/api/v1/studio/analyze", async ({ request }) => {
    await delay(50);

    const body = (await request.json()) as StudioAnalyzeRequest;

    // Validation
    if (!body.user_id) {
      return HttpResponse.json(
        { detail: "user_id is required" },
        { status: 400 },
      );
    }

    if (!body.tasks || body.tasks.length === 0) {
      return HttpResponse.json(
        { detail: "tasks array is required and cannot be empty" },
        { status: 400 },
      );
    }

    const response = createStudioAnalyzeResponse(body);
    return HttpResponse.json(response);
  }),

  // GET /api/v1/studio/templates - List templates
  http.get("/api/v1/studio/templates", async () => {
    await delay(50);
    return HttpResponse.json({ templates: mockTemplates });
  }),

  // POST /api/v1/studio/suggestions - Studio suggestions
  http.post("/api/v1/studio/suggestions", async ({ request }) => {
    await delay(50);

    const body = (await request.json()) as { context?: string; user_id?: string };

    const suggestions = [
      {
        type: "action",
        text: "Create new workflow",
        relevance: 0.9,
      },
      {
        type: "navigation",
        text: "View recent sessions",
        relevance: 0.8,
      },
      {
        type: "help",
        text: "Learn about keyboard shortcuts",
        relevance: 0.7,
      },
    ];

    return HttpResponse.json({
      suggestions,
      context: body.context || "general",
    });
  }),
];

export default studioHandlers;
