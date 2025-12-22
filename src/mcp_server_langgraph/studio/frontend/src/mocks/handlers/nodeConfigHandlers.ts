/**
 * Node Config Handlers - Phase 4
 *
 * MSW handlers for Node Config Assistant API endpoints.
 * These define the API contracts for node configuration help features.
 *
 * Endpoints:
 * - POST /api/v1/ai/node-config/help - Get help for node configuration
 */

import { http, HttpResponse, delay } from "msw";
import type { NodeConfigHelpRequest, NodeConfigHelpResponse } from "../../types/api";

// =============================================================================
// Mock Data
// =============================================================================

/**
 * Mock node config help response
 */
export const mockNodeConfigHelpResponse: NodeConfigHelpResponse = {
  answer:
    "Temperature controls the randomness of the model's output. A value of 0 makes the output deterministic, while higher values (up to 2) increase creativity but may reduce coherence. For most tasks, 0.7 is a good starting point.",
  suggested_config: {
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 0.9,
  },
  examples: [
    "For code generation, use temperature 0.2-0.4 for more focused output",
    "For creative writing, use temperature 0.8-1.0 for more varied responses",
    "For factual Q&A, use temperature 0-0.3 for consistent answers",
  ],
};

/**
 * Node-type specific help responses
 */
const NODE_TYPE_HELP: Record<string, Partial<NodeConfigHelpResponse>> = {
  llm: {
    answer:
      "LLM nodes allow you to configure language model parameters. Key settings include model selection, temperature for output randomness, and max_tokens for response length limits.",
    suggested_config: {
      model: "gpt-4",
      temperature: 0.7,
      max_tokens: 1000,
    },
    examples: [
      "Set temperature to 0 for deterministic responses",
      "Use max_tokens to limit response length and control costs",
      "Consider top_p as an alternative to temperature for sampling",
    ],
  },
  prompt: {
    answer:
      "Prompt nodes let you define template prompts with variable substitution. Use {variable_name} syntax to inject dynamic values at runtime.",
    suggested_config: {
      template: "You are a helpful assistant. {context}\n\nUser: {input}\nAssistant:",
      input_variables: ["context", "input"],
    },
    examples: [
      "Use {variable} syntax for string interpolation",
      "Define input_variables to validate required fields",
      "Consider partial_variables for static context",
    ],
  },
  tool: {
    answer:
      "Tool nodes connect external functions to your workflow. Configure the tool schema, description, and any required authentication.",
    suggested_config: {
      name: "search_tool",
      description: "Search for information",
    },
    examples: [
      "Provide clear descriptions for LLM tool selection",
      "Define parameter schemas for validation",
      "Handle errors gracefully in tool implementations",
    ],
  },
  memory: {
    answer:
      "Memory nodes maintain conversation history and context. Configure buffer size and memory type based on your use case.",
    suggested_config: {
      memory_type: "buffer",
      max_messages: 10,
    },
    examples: [
      "Use buffer memory for simple conversation tracking",
      "Use summary memory for long conversations",
      "Consider entity memory for extracting structured data",
    ],
  },
  router: {
    answer:
      "Router nodes direct workflow execution based on conditions. Configure routing rules and destination nodes.",
    suggested_config: {
      routes: [],
      default_route: "fallback",
    },
    examples: [
      "Define clear conditions for each route",
      "Always provide a default/fallback route",
      "Use intent classification for natural language routing",
    ],
  },
  retriever: {
    answer:
      "Retriever nodes fetch relevant context from vector stores or knowledge bases. Configure search parameters and result limits.",
    suggested_config: {
      top_k: 4,
      similarity_threshold: 0.7,
    },
    examples: [
      "Adjust top_k based on context window size",
      "Use similarity_threshold to filter irrelevant results",
      "Consider metadata filtering for targeted retrieval",
    ],
  },
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Generate contextual help response based on node type and question
 */
function generateHelpResponse(
  nodeType: string,
  nodeConfig: Record<string, unknown>,
  question: string,
  context?: string
): NodeConfigHelpResponse {
  // Get node-type specific help or use default
  const typeHelp = NODE_TYPE_HELP[nodeType] || {};

  // Build base response
  const baseResponse: NodeConfigHelpResponse = {
    answer: typeHelp.answer || mockNodeConfigHelpResponse.answer,
    suggested_config: typeHelp.suggested_config || mockNodeConfigHelpResponse.suggested_config,
    examples: typeHelp.examples || mockNodeConfigHelpResponse.examples,
  };

  // Customize response based on question keywords
  const lowerQuestion = question.toLowerCase();

  // If asking about specific settings, customize the response
  if (lowerQuestion.includes("temperature")) {
    baseResponse.answer =
      "Temperature controls the randomness of model outputs. Values range from 0 (deterministic) to 2 (highly random). For most applications, 0.7 provides a good balance between creativity and coherence.";
    baseResponse.suggested_config = { ...baseResponse.suggested_config, temperature: 0.7 };
  }

  if (lowerQuestion.includes("optimal") || lowerQuestion.includes("best")) {
    // Always include suggested_config for optimization questions
    baseResponse.suggested_config = {
      ...baseResponse.suggested_config,
      ...nodeConfig,
    };
  }

  if (
    lowerQuestion.includes("how do i") ||
    lowerQuestion.includes("how to") ||
    lowerQuestion.includes("template") ||
    lowerQuestion.includes("variable")
  ) {
    // Always include examples for how-to questions
    baseResponse.examples = typeHelp.examples || mockNodeConfigHelpResponse.examples;
  }

  // Add context awareness
  if (context) {
    baseResponse.answer = `Based on your context (${context}): ${baseResponse.answer}`;
  }

  return baseResponse;
}

// =============================================================================
// MSW Handlers
// =============================================================================

export const nodeConfigHandlers = [
  /**
   * POST /api/v1/ai/node-config/help - Get help for node configuration
   */
  http.post("/api/v1/ai/node-config/help", async ({ request }) => {
    await delay(100);

    const body = (await request.json()) as Partial<NodeConfigHelpRequest>;

    // Validate required fields
    if (!body.node_type) {
      return HttpResponse.json(
        { error: "Missing required field: node_type" },
        { status: 400 }
      );
    }

    if (!body.question) {
      return HttpResponse.json(
        { error: "Missing required field: question" },
        { status: 400 }
      );
    }

    if (!body.node_config) {
      return HttpResponse.json(
        { error: "Missing required field: node_config" },
        { status: 400 }
      );
    }

    // Generate contextual response
    const response = generateHelpResponse(
      body.node_type,
      body.node_config,
      body.question,
      body.context
    );

    return HttpResponse.json(response);
  }),
];
