/**
 * AI Handlers - Phase 4
 *
 * MSW handlers for AI API endpoints.
 * These define the API contracts for AI features.
 *
 * Endpoints:
 * - POST /api/v1/ai/interpret-command - Natural language command interpretation
 * - GET /api/v1/ai/suggestions - AI suggestions for artifact
 * - POST /api/v1/ai/fetch-url - Fetch and extract content from URL
 */

import { http, delay } from "msw";
import { apiJsonResponse, apiErrorResponse } from "../utils/apiResponse";
import type { AIInterpretation, Suggestion } from "../../ai";

// =============================================================================
// Types
// =============================================================================

interface InterpretCommandRequest {
  query: string;
}

interface FetchUrlRequest {
  url: string;
}

interface SuggestionsResponse {
  suggestions: Suggestion[];
}

interface FetchUrlResponse {
  content: string;
  title: string;
  url: string;
  fetchedAt: string;
}

interface EmptyStateSuggestionsRequest {
  context: string;
  persona?: string;
  session_id?: string;
}

// Batch composite analysis types
interface BatchCompositeRequest {
  user_id: string;
  session_id: string;
  include_persona?: boolean;
  include_disclosure?: boolean;
  include_error?: boolean;
  persona_data?: {
    assigned_persona?: string;
    recent_actions?: string[];
    feature_usage?: Record<string, number>;
  };
  disclosure_data?: {
    current_level?: DisclosureLevel;
    feature_usage?: Record<string, number>;
  };
  error_data?: { error_code?: string; error_message: string };
}

interface PersonaAnalysisResult {
  assigned_persona: string;
  detected_persona: string;
  confidence: number;
  behavior_signals: string[];
  recommendation: string | null;
  ui_adaptations: Array<{ feature: string; action: string }>;
}

interface DisclosureAnalysisResult {
  current_level: DisclosureLevel;
  recommended_level: DisclosureLevel;
  confidence: number;
  unlock_features: string[];
  personalized_message: string;
}

// BatchCompositeResponse type removed - now using inline object in apiJsonResponse

// Disclosure analysis types (Phase 6.1)
type DisclosureLevel = "beginner" | "intermediate" | "advanced" | "expert";

interface DisclosureAnalysisRequest {
  current_level?: DisclosureLevel;
}

// DisclosureAnalysisResponse interface removed - now using inline object in apiJsonResponse
// Handler returns camelCase which is transformed to snake_case by apiJsonResponse

// Nudge recommendation types (Phase 6.3) - matches generated OpenAPI types (ADR-0091)
// NudgeContext from generated-api.ts
interface NudgeContext {
  page: string;
  action?: string;
  time_on_page?: number;
}

// NudgeHistoryItem from generated-api.ts
interface NudgeHistoryItem {
  id: string;
  action: string;
  shown_at: string;
}

// NudgeRecommendRequest from generated-api.ts
interface NudgeRecommendRequest {
  user_id: string;
  current_context: NudgeContext;
  nudge_history?: NudgeHistoryItem[];
}

// Nudge and NudgeRecommendResponse types removed - now using inline objects in apiJsonResponse

/**
 * Empty state suggestion - matches RTK Query API schema
 */
interface EmptyStateSuggestion {
  title: string;
  description: string;
  action_type: "navigate" | "create" | "learn" | "import";
  action_target: string;
  icon?: string;
  priority: number;
}

interface EmptyStateSuggestionsResponse {
  suggestions: EmptyStateSuggestion[];
  context_hint?: string;
}

// Error analysis types (Phase 6.4) - matches RTK Query API schema
interface ErrorAnalysisRequest {
  error_code?: string;
  error_message: string;
}

interface RecoveryStep {
  step_number: number;
  title: string;
  description: string;
  action_type: "automatic" | "manual" | "contact_support";
  action_target?: string;
}

interface ErrorAnalysisResponse {
  error_type: string;
  recovery_steps: RecoveryStep[];
  auto_recoverable: boolean;
  suggested_action?: string;
  confidence: number;
}

// =============================================================================
// Mock Data
// =============================================================================

/**
 * Mock AI interpretation response
 */
export const mockAIInterpretation: AIInterpretation = {
  action: "navigate",
  params: { path: "/studio/compliance" },
  confidence: 0.92,
};

/**
 * Mock suggestions for code artifacts
 * Matches the Suggestion type from ai/InlineSuggestions.tsx
 */
export const mockSuggestions: Suggestion[] = [
  {
    id: "suggestion-1",
    type: "completion",
    content: `try {\n  // existing code\n} catch (error) {\n  console.error("Error:", error);\n  throw error;\n}`,
    confidence: 0.92,
  },
  {
    id: "suggestion-2",
    type: "refactor",
    content: `function processData(data: unknown) {\n  // Extracted logic here\n  return data;\n}`,
    confidence: 0.88,
  },
  {
    id: "suggestion-3",
    type: "fix",
    content: `if (value !== null && value !== undefined) {\n  // Safe to use value\n}`,
    confidence: 0.95,
  },
  {
    id: "suggestion-4",
    type: "explain",
    content:
      "This function iterates over the input array and transforms each element using the provided callback function, returning a new array with the transformed values.",
    confidence: 0.85,
  },
];

/**
 * Mock empty state suggestions by context - matches RTK Query API schema
 */
const mockEmptyStateSuggestions: Record<string, EmptyStateSuggestion[]> = {
  workflows: [
    {
      title: "Create your first workflow",
      description: "Start with a template to get up and running quickly",
      action_type: "create",
      action_target: "/studio/workflows/new?template=basic-chatbot",
      icon: "plus",
      priority: 1,
    },
    {
      title: "Import an existing workflow",
      description: "Bring in workflows from other projects or tools",
      action_type: "import",
      action_target: "/studio/workflows/import",
      icon: "upload",
      priority: 2,
    },
    {
      title: "Explore example workflows",
      description: "Learn from curated examples and templates",
      action_type: "learn",
      action_target: "/studio/workflows?filter=examples",
      icon: "book",
      priority: 3,
    },
  ],
  sessions: [
    {
      title: "Start a new conversation",
      description: "Begin an interactive chat session",
      action_type: "create",
      action_target: "/studio/chat/new",
      icon: "message-square",
      priority: 1,
    },
    {
      title: "View recent activity",
      description: "Continue from where you left off",
      action_type: "navigate",
      action_target: "/studio/chat?filter=recent",
      icon: "clock",
      priority: 2,
    },
  ],
  projects: [
    {
      title: "Create a new project",
      description: "Organize your workflows and sessions",
      action_type: "create",
      action_target: "/studio/projects/new",
      icon: "folder-plus",
      priority: 1,
    },
    {
      title: "Browse project templates",
      description: "Start from proven project structures",
      action_type: "learn",
      action_target: "/studio/projects/templates",
      icon: "layout-template",
      priority: 2,
    },
  ],
  traces: [
    {
      title: "Run a workflow to see traces",
      description: "Execute a workflow to generate observability data",
      action_type: "navigate",
      action_target: "/studio/workflows",
      icon: "play",
      priority: 1,
    },
    {
      title: "View trace examples",
      description: "See example traces to understand the format",
      action_type: "learn",
      action_target: "/studio/observability?demo=true",
      icon: "eye",
      priority: 2,
    },
  ],
  messages: [
    {
      title: "Start chatting",
      description: "Type a message to begin your conversation",
      action_type: "navigate",
      action_target: "/studio/chat/new",
      icon: "message-circle",
      priority: 1,
    },
  ],
  chat: [
    {
      title: "Start a new chat",
      description: "Begin an interactive conversation with the AI",
      action_type: "create",
      action_target: "/studio/chat/new",
      icon: "message-square-plus",
      priority: 1,
    },
    {
      title: "View chat history",
      description: "Browse your previous conversations",
      action_type: "navigate",
      action_target: "/studio/chat",
      icon: "history",
      priority: 2,
    },
  ],
};

/**
 * Get context-specific suggestions
 */
function getEmptyStateSuggestions(
  context: string,
  _persona?: string,
): EmptyStateSuggestion[] {
  // Return context-specific suggestions, fallback to generic
  const contextSuggestions = mockEmptyStateSuggestions[context];
  const workflowsSuggestions = mockEmptyStateSuggestions["workflows"];
  return contextSuggestions ?? workflowsSuggestions ?? [];
}

/**
 * Error classification patterns (Phase 6.4) - matches RTK Query API schema
 * Maps error patterns to error types and recovery steps
 */
interface ErrorPattern {
  test: (errorCode: string, message: string) => boolean;
  error_type: string;
  recovery_steps: RecoveryStep[];
  auto_recoverable: boolean;
  suggested_action?: string;
  confidence: number;
}

const errorPatterns: ErrorPattern[] = [
  {
    test: (code, msg) =>
      code.includes("TIMEOUT") ||
      msg.toLowerCase().includes("timeout") ||
      msg.toLowerCase().includes("timed out"),
    error_type: "network_timeout",
    recovery_steps: [
      {
        step_number: 1,
        title: "Wait briefly",
        description:
          "The server is experiencing high load. Wait a few seconds before retrying.",
        action_type: "manual",
      },
      {
        step_number: 2,
        title: "Retry the request",
        description: "Click retry to attempt the operation again.",
        action_type: "automatic",
        action_target: "retry",
      },
    ],
    auto_recoverable: true,
    suggested_action: "retry",
    confidence: 0.92,
  },
  {
    test: (code, msg) =>
      code.includes("NETWORK") ||
      msg.toLowerCase().includes("network") ||
      msg.toLowerCase().includes("connection"),
    error_type: "network_connection",
    recovery_steps: [
      {
        step_number: 1,
        title: "Check your connection",
        description: "Verify your internet connection is working properly.",
        action_type: "manual",
      },
      {
        step_number: 2,
        title: "Retry connection",
        description: "Once connected, click retry to continue.",
        action_type: "automatic",
        action_target: "retry",
      },
    ],
    auto_recoverable: false,
    suggested_action: "check_connection",
    confidence: 0.88,
  },
  {
    test: (code, msg) =>
      code.includes("AUTH") ||
      msg.toLowerCase().includes("session") ||
      msg.toLowerCase().includes("expired") ||
      msg.toLowerCase().includes("unauthorized"),
    error_type: "authentication",
    recovery_steps: [
      {
        step_number: 1,
        title: "Session expired",
        description:
          "Your session has expired. You need to log in again to continue.",
        action_type: "manual",
        action_target: "/login",
      },
    ],
    auto_recoverable: false,
    suggested_action: "login",
    confidence: 0.95,
  },
  {
    test: (code, msg) =>
      code.includes("VALIDATION") ||
      msg.toLowerCase().includes("invalid") ||
      msg.toLowerCase().includes("validation"),
    error_type: "validation",
    recovery_steps: [
      {
        step_number: 1,
        title: "Check your input",
        description: "Review the data you entered and correct any errors.",
        action_type: "manual",
      },
      {
        step_number: 2,
        title: "Submit again",
        description: "After correcting the input, try submitting again.",
        action_type: "manual",
      },
    ],
    auto_recoverable: false,
    suggested_action: "fix_input",
    confidence: 0.88,
  },
  {
    test: (_code, msg) =>
      msg.toLowerCase().includes("permission") ||
      msg.toLowerCase().includes("forbidden") ||
      msg.toLowerCase().includes("access denied"),
    error_type: "authorization",
    recovery_steps: [
      {
        step_number: 1,
        title: "Insufficient permissions",
        description: "You don't have permission to perform this action.",
        action_type: "manual",
      },
      {
        step_number: 2,
        title: "Contact administrator",
        description:
          "Request the necessary permissions from your administrator.",
        action_type: "contact_support",
      },
    ],
    auto_recoverable: false,
    confidence: 0.9,
  },
  {
    test: (_code, msg) =>
      msg.toLowerCase().includes("rate limit") ||
      msg.toLowerCase().includes("too many requests"),
    error_type: "rate_limit",
    recovery_steps: [
      {
        step_number: 1,
        title: "Rate limit exceeded",
        description:
          "You've made too many requests. Please wait before trying again.",
        action_type: "manual",
      },
      {
        step_number: 2,
        title: "Wait and retry",
        description: "Wait a minute, then retry your request.",
        action_type: "automatic",
        action_target: "retry_delayed",
      },
    ],
    auto_recoverable: true,
    suggested_action: "wait",
    confidence: 0.93,
  },
];

/**
 * Analyze an error and return classification with recovery steps
 * Returns response matching RTK Query API schema
 */
function analyzeError(request: ErrorAnalysisRequest): ErrorAnalysisResponse {
  const errorCode = request.error_code || "";
  const errorMessage = request.error_message || "";

  // Find matching pattern
  for (const pattern of errorPatterns) {
    if (pattern.test(errorCode, errorMessage)) {
      return {
        error_type: pattern.error_type,
        recovery_steps: pattern.recovery_steps,
        auto_recoverable: pattern.auto_recoverable,
        suggested_action: pattern.suggested_action,
        confidence: pattern.confidence,
      };
    }
  }

  // Default: unknown error
  return {
    error_type: "unknown",
    recovery_steps: [
      {
        step_number: 1,
        title: "Unexpected error",
        description:
          "An unexpected error occurred. Try again or contact support if the issue persists.",
        action_type: "manual",
      },
      {
        step_number: 2,
        title: "Contact support",
        description:
          "If the problem continues, please contact our support team.",
        action_type: "contact_support",
      },
    ],
    auto_recoverable: false,
    suggested_action: "contact_support",
    confidence: 0.5,
  };
}

/**
 * Disclosure level recommendations (Phase 6.1)
 */
const disclosureRecommendations: Record<
  DisclosureLevel,
  { recommendedLevel: DisclosureLevel; features: string[]; message: string }
> = {
  beginner: {
    recommendedLevel: "intermediate",
    features: ["workflow_builder", "custom_templates"],
    message: "You've mastered the basics! Ready to explore workflows?",
  },
  intermediate: {
    recommendedLevel: "advanced",
    features: ["custom_agents", "api_integrations"],
    message: "Great progress! Unlock advanced features like custom agents.",
  },
  advanced: {
    recommendedLevel: "expert",
    features: ["admin_controls", "security_settings"],
    message: "You're an expert user. Access admin and security features.",
  },
  expert: {
    recommendedLevel: "expert",
    features: [],
    message: "You have access to all features!",
  },
};

/**
 * Nudge catalog (Phase 6.3) - matches generated OpenAPI types (ADR-0091)
 */
interface NudgeCatalogEntry {
  id: string;
  type: string;
  message: string;
  priority: string;
  show_after_ms: number;
  target_element?: string | null;
  confidence: number;
  context_match: string[]; // contexts this nudge applies to
}

const nudgeCatalog: NudgeCatalogEntry[] = [
  {
    id: "nudge-keyboard-shortcut",
    type: "tooltip",
    message: "Pro tip: Press Cmd+K for quick search",
    priority: "medium",
    show_after_ms: 5000,
    target_element: null,
    confidence: 0.85,
    context_match: ["chat", "workflows", "projects"],
  },
  {
    id: "nudge-feature-discovery",
    type: "tooltip",
    message: "Build your first workflow to automate tasks",
    priority: "high",
    show_after_ms: 10000,
    target_element: null,
    confidence: 0.92,
    context_match: ["workflows", "chat"],
  },
  {
    id: "nudge-canvas-hint",
    type: "tooltip",
    message: "Toggle the canvas panel to see visual representations",
    priority: "low",
    show_after_ms: 3000,
    target_element: "canvas-toggle",
    confidence: 0.78,
    context_match: ["chat", "sessions"],
  },
  {
    id: "nudge-observability-intro",
    type: "tooltip",
    message: "Explore traces and logs in the Observability tab",
    priority: "medium",
    show_after_ms: 8000,
    target_element: null,
    confidence: 0.82,
    context_match: ["workflows", "traces"],
  },
];

/**
 * Route mapping for navigation interpretations
 */
const ROUTE_KEYWORDS: Record<string, string> = {
  compliance: "/studio/compliance",
  observability: "/studio/observability",
  settings: "/studio/settings",
  help: "/studio/help",
  chat: "/studio/chat",
  workflows: "/studio/workflows",
  connections: "/studio/connections",
  artifacts: "/studio/artifacts",
};

/**
 * Interpret a natural language query into an action
 */
function interpretQuery(query: string): AIInterpretation {
  const lowerQuery = query.toLowerCase();

  // Check for navigation intent
  if (
    lowerQuery.includes("go to") ||
    lowerQuery.includes("show") ||
    lowerQuery.includes("open") ||
    lowerQuery.includes("navigate")
  ) {
    for (const [keyword, path] of Object.entries(ROUTE_KEYWORDS)) {
      if (lowerQuery.includes(keyword)) {
        return {
          action: "navigate",
          params: { path },
          confidence: 0.9,
        };
      }
    }
  }

  // Check for search intent
  if (
    lowerQuery.includes("find") ||
    lowerQuery.includes("search") ||
    lowerQuery.includes("look for")
  ) {
    return {
      action: "search",
      params: { query: query.replace(/find|search|look for/gi, "").trim() },
      confidence: 0.85,
    };
  }

  // Check for toggle intent
  if (
    lowerQuery.includes("toggle") ||
    lowerQuery.includes("hide") ||
    lowerQuery.includes("show")
  ) {
    if (lowerQuery.includes("canvas")) {
      return {
        action: "toggle-panel",
        params: { panel: "canvas" },
        confidence: 0.88,
      };
    }
    if (lowerQuery.includes("sidebar") || lowerQuery.includes("session")) {
      return {
        action: "toggle-panel",
        params: { panel: "sidebar" },
        confidence: 0.88,
      };
    }
  }

  // Check for new chat intent
  if (
    lowerQuery.includes("new chat") ||
    lowerQuery.includes("start chat") ||
    lowerQuery.includes("new conversation")
  ) {
    return {
      action: "new-chat",
      params: {},
      confidence: 0.95,
    };
  }

  // Default: search action with low confidence
  return {
    action: "search",
    params: { query },
    confidence: 0.5,
  };
}

/**
 * Validate URL format
 */
function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

// =============================================================================
// MSW Handlers
// =============================================================================

export const aiHandlers = [
  /**
   * POST /api/v1/ai/interpret-command - Natural language command interpretation
   */
  http.post("/api/v1/ai/interpret-command", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as InterpretCommandRequest;

    if (!body.query) {
      return apiErrorResponse("Missing required field: query", 400);
    }

    const interpretation = interpretQuery(body.query);
    return apiJsonResponse(interpretation);
  }),

  /**
   * GET /api/v1/ai/suggestions - AI suggestions for artifact
   */
  http.get("/api/v1/ai/suggestions", async ({ request }) => {
    await delay(150);

    const url = new URL(request.url);
    const artifactId = url.searchParams.get("artifactId");

    if (!artifactId) {
      return apiErrorResponse("Missing required query parameter: artifactId", 400);
    }

    // Return mock suggestions
    const response: SuggestionsResponse = {
      suggestions: mockSuggestions,
    };

    return apiJsonResponse(response);
  }),

  /**
   * POST /api/v1/ai/fetch-url - Fetch and extract content from URL
   */
  http.post("/api/v1/ai/fetch-url", async ({ request }) => {
    await delay(200);

    const body = (await request.json()) as FetchUrlRequest;

    if (!body.url) {
      return apiErrorResponse("Missing required field: url", 400);
    }

    if (!isValidUrl(body.url)) {
      return apiErrorResponse("Invalid URL format", 422);
    }

    // Return mock content
    const response: FetchUrlResponse = {
      content: `# Content from ${body.url}\n\nThis is mock content fetched from the provided URL. In production, this would contain the actual extracted content from the webpage.`,
      title: `Page: ${new URL(body.url).hostname}`,
      url: body.url,
      fetchedAt: new Date().toISOString(),
    };

    return apiJsonResponse(response);
  }),

  /**
   * POST /api/v1/ai/empty-state/suggestions - AI-powered empty state suggestions
   */
  http.post("/api/v1/ai/empty-state/suggestions", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as EmptyStateSuggestionsRequest;

    const suggestions = getEmptyStateSuggestions(body.context, body.persona);

    const response: EmptyStateSuggestionsResponse = {
      suggestions,
    };

    return apiJsonResponse(response);
  }),

  /**
   * POST /api/v1/ai/errors/analyze - AI-powered error analysis (Phase 6.4)
   * Returns response matching RTK Query API schema
   */
  http.post("/api/v1/ai/errors/analyze", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as ErrorAnalysisRequest;

    if (!body.error_message) {
      return apiErrorResponse("Missing required field: error_message", 400);
    }

    const analysis = analyzeError(body);
    return apiJsonResponse(analysis);
  }),

  /**
   * POST /api/v1/ai/disclosure/analyze - AI-powered disclosure level analysis (Phase 6.1)
   * Handles any disclosure level string, mapping unknown levels to beginner
   */
  http.post("/api/v1/ai/disclosure/analyze", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as DisclosureAnalysisRequest;
    const inputLevel = body.current_level || "beginner";

    // Map input level to valid disclosure level
    const levelMap: Record<string, DisclosureLevel> = {
      basic: "beginner",
      beginner: "beginner",
      intermediate: "intermediate",
      advanced: "advanced",
      expert: "expert",
    };
    const currentLevel = levelMap[inputLevel.toLowerCase()] || "beginner";
    const recommendation = disclosureRecommendations[currentLevel];

    return apiJsonResponse({
      currentLevel: inputLevel, // Return the input level as-is for flexibility
      recommendedLevel: recommendation.recommendedLevel,
      confidence: currentLevel === "expert" ? 0.95 : 0.85,
      unlockFeatures: recommendation.features,
      personalizedMessage: recommendation.message,
    });
  }),

  /**
   * POST /api/v1/ai/nudges/recommend - AI-powered nudge recommendations (Phase 6.3)
   * Returns response matching generated OpenAPI NudgeRecommendResponse (ADR-0091)
   */
  http.post("/api/v1/ai/nudges/recommend", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as NudgeRecommendRequest;
    // Extract page from current_context (generated schema format)
    const context = body.current_context?.page || "chat";

    // Find a nudge matching the current context
    const matchingNudge = nudgeCatalog.find((nudge) =>
      nudge.context_match.includes(context),
    );

    // Use the matching nudge or default to first one
    const selectedNudge = matchingNudge || nudgeCatalog[0];

    // Return response in camelCase (will be transformed to snake_case by apiJsonResponse)
    return apiJsonResponse({
      shouldShow: true,
      confidence: selectedNudge.confidence,
      nudge: {
        id: selectedNudge.id,
        type: selectedNudge.type,
        message: selectedNudge.message,
        priority: selectedNudge.priority,
        showAfterMs: selectedNudge.show_after_ms,
        targetElement: selectedNudge.target_element,
      },
    });
  }),

  /**
   * POST /api/v1/ai/onboarding/personalize - AI-powered onboarding personalization (Phase 6.5)
   * Returns response matching generated OpenAPI OnboardingPersonalizeResponse (ADR-0091)
   */
  http.post("/api/v1/ai/onboarding/personalize", async ({ request }) => {
    await delay(100);

    // OnboardingPersonalizeRequest from generated-api.ts
    interface OnboardingRequest {
      user_id: string;
      initial_actions?: string[];
      signup_context?: {
        referrer?: string;
        utm_source?: string;
      } | null;
    }

    const body = (await request.json()) as OnboardingRequest;
    const initialActions = body.initial_actions || [];
    const hasDevActions = initialActions.some(
      (a) => a.includes("workflow") || a.includes("api") || a.includes("debug"),
    );
    const hasAnalyticsActions = initialActions.some(
      (a) => a.includes("trace") || a.includes("metric") || a.includes("log"),
    );

    // Personalize based on initial actions
    if (hasDevActions) {
      return apiJsonResponse({
        detectedIntent: "build_workflows",
        confidence: 0.88,
        recommendedPath: [
          { step: "api_overview", guided: true, focus: "api" },
          { step: "workflow_builder_intro", guided: true, focus: "workflows" },
          { step: "advanced_configuration", guided: false },
          { step: "observability_setup", guided: true, focus: "traces" },
        ],
        skipSteps: ["basic_intro", "what_is_ai", "simple_examples"],
        personaPrediction: "alice-builder",
      });
    }

    if (hasAnalyticsActions) {
      return apiJsonResponse({
        detectedIntent: "analyze_data",
        confidence: 0.82,
        recommendedPath: [
          { step: "welcome_tour", guided: true },
          { step: "trace_exploration", guided: true, focus: "traces" },
          { step: "metrics_dashboard", guided: true, focus: "metrics" },
          { step: "custom_reports", guided: false },
        ],
        skipSteps: ["basic_intro"],
        personaPrediction: "alice-analyst",
      });
    }

    // Default: beginner experience
    return apiJsonResponse({
      detectedIntent: "explore_features",
      confidence: 0.75,
      recommendedPath: [
        { step: "welcome_tour", guided: true },
        { step: "basic_intro", guided: true },
        { step: "first_chat", guided: true, focus: "chat" },
        { step: "explore_features", guided: false },
        { step: "help_resources", guided: false },
      ],
      skipSteps: [],
      personaPrediction: "bob",
    });
  }),

  /**
   * GET /api/v1/ai/metrics/insights - AI-generated HEART metrics insights (Phase 6.6)
   */
  http.get("/api/v1/ai/metrics/insights", async () => {
    await delay(150);

    return apiJsonResponse({
      insights: [
        {
          type: "anomaly",
          dimension: "retention",
          message: "D7 retention dropped 12% for alice-builder personas",
          severity: "warning",
          suggestedActions: [
            "Check workflow builder UX",
            "Review recent changes",
          ],
          detectedAt: new Date().toISOString(),
        },
        {
          type: "trend",
          dimension: "adoption",
          message: "AI suggestions adoption up 25% after nudge system launch",
          sentiment: "positive",
        },
        {
          type: "pattern",
          dimension: "engagement",
          message:
            "Power users (admin, developer) show 3x higher session duration",
          sentiment: "neutral",
        },
        {
          type: "trend",
          dimension: "happiness",
          message: "User satisfaction increased after onboarding improvements",
          sentiment: "positive",
        },
      ],
      predictions: [
        {
          metric: "30DayRetention",
          current: 0.65,
          predicted: 0.72,
          confidence: 0.78,
          drivers: ["improved_onboarding", "nudge_system"],
        },
        {
          metric: "weeklyActiveUsers",
          current: 450,
          predicted: 520,
          confidence: 0.85,
          drivers: ["new_features", "marketing_campaign"],
        },
        {
          metric: "taskSuccessRate",
          current: 0.82,
          predicted: 0.88,
          confidence: 0.72,
          drivers: ["error_recovery_improvements", "better_guidance"],
        },
      ],
    });
  }),

  /**
   * POST /api/v1/ai/persona/analyze - AI-powered persona behavior analysis (Phase 6.7)
   */
  http.post("/api/v1/ai/persona/analyze", async ({ request }) => {
    await delay(100);

    interface PersonaAnalysisRequest {
      user_id: string;
      assigned_persona?: string;
      recent_actions?: string[];
      feature_usage?: Record<string, number>;
    }

    const body = (await request.json()) as PersonaAnalysisRequest;
    const recentActions = body.recent_actions || [];
    const featureUsage = body.feature_usage || {};
    const assignedPersona = body.assigned_persona || "bob";

    // Analyze behavior patterns
    const hasDevActions = recentActions.some(
      (a) =>
        a.includes("workflow") || a.includes("trace") || a.includes("debug"),
    );
    const highWorkflowUsage = (featureUsage.workflow_builder || 0) > 20;
    const highTraceUsage = (featureUsage.traces || 0) > 15;

    // Detect actual persona from behavior
    if (hasDevActions && highWorkflowUsage) {
      return apiJsonResponse({
        assignedPersona: assignedPersona,
        detectedPersona: "alice-builder",
        confidence: 0.88,
        behaviorSignals: [
          "Frequent workflow editing",
          "Advanced trace analysis",
          "Long session durations",
        ],
        recommendation:
          "Consider upgrading to developer role for enhanced features",
        uiAdaptations: [
          { feature: "workflow_builder", action: "unlock" },
          { feature: "advanced_traces", action: "promote" },
        ],
      });
    }

    if (hasDevActions || highTraceUsage) {
      return apiJsonResponse({
        assignedPersona: assignedPersona,
        detectedPersona: "alice-analyst",
        confidence: 0.75,
        behaviorSignals: [
          "Frequent trace exploration",
          "Advanced filter usage",
        ],
        recommendation: null,
        uiAdaptations: [{ feature: "observability", action: "unlock" }],
      });
    }

    // Default: persona matches behavior
    return apiJsonResponse({
      assignedPersona: assignedPersona,
      detectedPersona: assignedPersona,
      confidence: 0.95,
      behaviorSignals: ["Chat-focused usage", "Standard interaction patterns"],
      recommendation: null,
      uiAdaptations: [],
    });
  }),

  /**
   * POST /api/v1/ai/composite/analyze - Single composite analysis endpoint
   * Runs persona, disclosure, and error analyses in parallel (when requested)
   * Returns combined results with cross-insights
   */
  http.post("/api/v1/ai/composite/analyze", async ({ request }) => {
    await delay(150);

    const body = (await request.json()) as BatchCompositeRequest;

    // Validate required fields
    if (!body.user_id) {
      return apiErrorResponse("Missing required field: user_id", 400);
    }

    if (!body.session_id) {
      return apiErrorResponse("Missing required field: session_id", 400);
    }

    // Build response based on requested analyses
    let personaResult: PersonaAnalysisResult | null = null;
    let disclosureResult: DisclosureAnalysisResult | null = null;
    let errorResult: ErrorAnalysisResponse | null = null;
    const crossInsights: string[] = [];

    // Run persona analysis if requested
    if (body.include_persona) {
      const personaData = body.persona_data || {};
      const assignedPersona = personaData.assigned_persona || "bob";
      const recentActions = personaData.recent_actions || [];
      const featureUsage = personaData.feature_usage || {};

      const hasDevActions = recentActions.some(
        (a) =>
          a.includes("workflow") || a.includes("trace") || a.includes("debug"),
      );
      const highWorkflowUsage = (featureUsage.workflow_builder || 0) > 20;

      if (hasDevActions && highWorkflowUsage) {
        personaResult = {
          assigned_persona: assignedPersona,
          detected_persona: "alice-builder",
          confidence: 0.88,
          behavior_signals: [
            "Frequent workflow editing",
            "Advanced trace analysis",
          ],
          recommendation: "Consider upgrading to developer role",
          ui_adaptations: [{ feature: "workflow_builder", action: "unlock" }],
        };
      } else {
        personaResult = {
          assigned_persona: assignedPersona,
          detected_persona: assignedPersona,
          confidence: 0.9,
          behavior_signals: ["Standard interaction patterns"],
          recommendation: null,
          ui_adaptations: [],
        };
      }
    }

    // Run disclosure analysis if requested
    if (body.include_disclosure) {
      const disclosureData = body.disclosure_data || {};
      const currentLevel: DisclosureLevel =
        disclosureData.current_level || "beginner";
      const recommendation = disclosureRecommendations[currentLevel];

      disclosureResult = {
        current_level: currentLevel,
        recommended_level: recommendation.recommendedLevel,
        confidence: currentLevel === "expert" ? 0.95 : 0.85,
        unlock_features: recommendation.features,
        personalized_message: recommendation.message,
      };
    }

    // Run error analysis if requested
    if (body.include_error && body.error_data?.error_message) {
      errorResult = analyzeError({
        error_code: body.error_data.error_code,
        error_message: body.error_data.error_message,
      });
    }

    // Generate cross-insights based on combined results
    if (personaResult && disclosureResult) {
      if (
        personaResult.detected_persona !== personaResult.assigned_persona &&
        disclosureResult.current_level !== disclosureResult.recommended_level
      ) {
        crossInsights.push(
          `Potential mismatch: detected persona "${personaResult.detected_persona}" suggests upgrade to "${disclosureResult.recommended_level}" level`,
        );
      }
      crossInsights.push("Combined persona and disclosure analysis complete");
    }

    // Calculate overall confidence
    const confidences: number[] = [];
    if (personaResult) confidences.push(personaResult.confidence);
    if (disclosureResult) confidences.push(disclosureResult.confidence);
    if (errorResult) confidences.push(errorResult.confidence);

    const overallConfidence =
      confidences.length > 0
        ? confidences.reduce((a, b) => a + b, 0) / confidences.length
        : 0.5;

    return apiJsonResponse({
      userId: body.user_id,
      sessionId: body.session_id,
      personaResult: personaResult,
      disclosureResult: disclosureResult,
      errorResult: errorResult,
      crossInsights: crossInsights,
      confidence: overallConfidence,
    });
  }),

  /**
   * POST /api/v1/ai/composite/batch - Batch composite analysis endpoint
   * Runs persona, disclosure, and error analyses in parallel (when requested)
   */
  http.post("/api/v1/ai/composite/batch", async ({ request }) => {
    await delay(150);

    const body = (await request.json()) as BatchCompositeRequest;

    // Validate required fields
    if (!body.user_id) {
      return apiErrorResponse("Missing required field: user_id", 400);
    }

    if (!body.session_id) {
      return apiErrorResponse("Missing required field: session_id", 400);
    }

    // Build response based on requested analyses
    let personaResult: PersonaAnalysisResult | null = null;
    let disclosureResult: DisclosureAnalysisResult | null = null;
    let errorResult: ErrorAnalysisResponse | null = null;
    const crossInsights: string[] = [];

    // Run persona analysis if requested
    if (body.include_persona) {
      const personaData = body.persona_data || {};
      const assignedPersona = personaData.assigned_persona || "bob";
      const recentActions = personaData.recent_actions || [];
      const featureUsage = personaData.feature_usage || {};

      const hasDevActions = recentActions.some(
        (a) =>
          a.includes("workflow") || a.includes("trace") || a.includes("debug"),
      );
      const highWorkflowUsage = (featureUsage.workflow_builder || 0) > 20;

      if (hasDevActions && highWorkflowUsage) {
        personaResult = {
          assigned_persona: assignedPersona,
          detected_persona: "alice-builder",
          confidence: 0.88,
          behavior_signals: [
            "Frequent workflow editing",
            "Advanced trace analysis",
          ],
          recommendation: "Consider upgrading to developer role",
          ui_adaptations: [{ feature: "workflow_builder", action: "unlock" }],
        };
      } else {
        personaResult = {
          assigned_persona: assignedPersona,
          detected_persona: assignedPersona,
          confidence: 0.9,
          behavior_signals: ["Standard interaction patterns"],
          recommendation: null,
          ui_adaptations: [],
        };
      }
    }

    // Run disclosure analysis if requested
    if (body.include_disclosure) {
      const disclosureData = body.disclosure_data || {};
      const currentLevel: DisclosureLevel =
        disclosureData.current_level || "beginner";
      const recommendation = disclosureRecommendations[currentLevel];

      disclosureResult = {
        current_level: currentLevel,
        recommended_level: recommendation.recommendedLevel,
        confidence: currentLevel === "expert" ? 0.95 : 0.85,
        unlock_features: recommendation.features,
        personalized_message: recommendation.message,
      };
    }

    // Run error analysis if requested
    if (body.include_error && body.error_data?.error_message) {
      errorResult = analyzeError({
        error_code: body.error_data.error_code,
        error_message: body.error_data.error_message,
      });
    }

    // Generate cross-insights based on combined results
    if (personaResult && disclosureResult) {
      // Check for persona/disclosure mismatch
      if (
        personaResult.detected_persona !== personaResult.assigned_persona &&
        disclosureResult.current_level !== disclosureResult.recommended_level
      ) {
        crossInsights.push(
          `Potential mismatch: detected persona "${personaResult.detected_persona}" suggests upgrade to "${disclosureResult.recommended_level}" level`,
        );
      }
      crossInsights.push("Combined persona and disclosure analysis complete");
    }

    // Calculate overall confidence
    const confidences: number[] = [];
    if (personaResult) confidences.push(personaResult.confidence);
    if (disclosureResult) confidences.push(disclosureResult.confidence);
    if (errorResult) confidences.push(errorResult.confidence);

    const overallConfidence =
      confidences.length > 0
        ? confidences.reduce((a, b) => a + b, 0) / confidences.length
        : 0.5;

    return apiJsonResponse({
      userId: body.user_id,
      sessionId: body.session_id,
      personaResult: personaResult,
      disclosureResult: disclosureResult,
      errorResult: errorResult,
      crossInsights: crossInsights,
      confidence: overallConfidence,
    });
  }),
];
