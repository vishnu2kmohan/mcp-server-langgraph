/**
 * AgentsPage
 *
 * Agent configuration page showing LangGraph agent settings,
 * available tools, and model configuration.
 *
 * Uses RTK Query for data fetching with automatic caching.
 *
 * Enhanced in Sprint 2 with persona-aware rendering and new cards:
 * - ThinkingBudgetCard (admin, developer)
 * - FeatureFlagsCard (admin, developer)
 * - OrchestratorsListCard (admin, developer) - future when backend provides data
 */

import { useState, useEffect, useMemo } from "react";
import { useSelector } from "react-redux";
import { Cpu, RefreshCw, Wrench, Check, X } from "lucide-react";
import { useGetAgentConfigQuery } from "../api";
// Direct imports to avoid Rollup circular dependency warnings
// (page chunks end up separate from UI barrel)
import { Button } from "../components/UI/Button";
import { ErrorState } from "../components/UI/ErrorState";
import { Select } from "../components/UI/Select";
import { Slider } from "../components/UI/Slider";
import { Toggle } from "../components/UI/Toggle";
import {
  ThinkingBudgetCard,
  FeatureFlagsCard,
  OrchestratorsListCard,
  TaskMappingCard,
  LLMProvidersCard,
  AgentMetricsCard,
} from "../components/Agents";
import { selectPersona, type Persona } from "../store/slices/personaSlice";

/**
 * Get page configuration based on persona
 */
function getPageConfig(persona: Persona) {
  switch (persona) {
    case "admin":
      return {
        title: "Agent Infrastructure",
        description:
          "Complete LLM provider, orchestrator, and resilience configuration",
      };
    case "developer":
      return {
        title: "Agent Configuration",
        description: "Model types, orchestrators, and available tools",
      };
    default:
      return {
        title: "AI Capabilities",
        description: "Available AI tools and features",
      };
  }
}

export function AgentsPage() {
  // Get current persona for persona-aware rendering
  const persona = useSelector(selectPersona);

  // Fetch agent config using RTK Query
  const { data: config, isLoading, error, refetch } = useGetAgentConfigQuery();

  // Persona-specific page config
  const pageConfig = useMemo(() => getPageConfig(persona), [persona]);

  // Local state for form controls (for UI responsiveness)
  const [localTemperature, setLocalTemperature] = useState(0.7);
  const [localVerification, setLocalVerification] = useState(false);

  // Sync local state with fetched config
  useEffect(() => {
    if (config) {
      setLocalTemperature(config.temperature);
      setLocalVerification(config.verificationEnabled);
    }
  }, [config]);

  const handleRefresh = () => {
    refetch();
  };

  const handleTemperatureChange = (value: number) => {
    setLocalTemperature(value);
  };

  const handleVerificationToggle = (checked: boolean) => {
    setLocalVerification(checked);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-9" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center">
        <ErrorState
          title="Failed to load agent configuration"
          message="Unable to fetch agent settings. Please try again."
          onRetry={handleRefresh}
          variant="fullscreen"
        />
      </div>
    );
  }

  // Use config data or defaults
  const model = config?.model ?? "";
  const provider = config?.provider ?? "";
  const tools = config?.tools ?? [];

  return (
    <div className="h-screen flex flex-col bg-neutral-1">
      {/* Header */}
      <header className="px-6 py-4 bg-neutral-2 border-b border-neutral-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-12">
              {pageConfig.title}
            </h1>
            <p className="text-sm text-neutral-11">
              {pageConfig.description}
            </p>
          </div>
          <Button
            variant="secondary"
            className="flex px-4 py-2 bg-neutral-3 rounded-lg hover:bg-neutral-30 dark:hover:bg-neutral-9"
            onClick={handleRefresh}
          >
            <RefreshCw size={16} />
            Refresh
          </Button>
        </div>
      </header>
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Model Configuration Card */}
          <div className="bg-neutral-2 rounded-lg border border-neutral-6 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Cpu size={24} className="text-primary-9" />
              <h2 className="text-xl font-semibold text-neutral-12">
                Model Configuration
              </h2>
            </div>

            <div className="space-y-4">
              {/* Model Selection */}
              <div>
                <label
                  htmlFor="model-select"
                  className="block text-sm font-medium text-neutral-11 mb-2"
                >
                  Model
                </label>
                <Select
                  className="px-3 py-2 bg-neutral-2 text-neutral-12 cursor-not-allowed"
                  id="model-select"
                  value={model}
                  disabled
                >
                  <option value={model}>{model}</option>
                </Select>
                {provider && (
                  <p className="mt-1 text-sm text-neutral-11">
                    Provider: {provider}
                  </p>
                )}
              </div>

              {/* Temperature Slider */}
              <Slider
                id="temperature-slider"
                value={localTemperature}
                onChange={handleTemperatureChange}
                min={0}
                max={1}
                step={0.1}
                label="Temperature"
                showValue
                formatValue={(v) => v.toFixed(1)}
                marks={[
                  { value: 0, label: "Precise (0.0)" },
                  { value: 1, label: "Creative (1.0)" },
                ]}
              />

              {/* Verification Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <label
                    htmlFor="verification-toggle"
                    className="text-sm font-medium text-neutral-11"
                  >
                    Enable Verification
                  </label>
                  <p className="text-xs text-neutral-11 mt-1">
                    Verify agent responses before executing
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Toggle
                    id="verification-toggle"
                    checked={localVerification}
                    onChange={handleVerificationToggle}
                    aria-label="Enable Verification"
                  />
                  {localVerification ? (
                    <Check size={16} className="text-success-9" />
                  ) : (
                    <X size={16} className="text-neutral-6" />
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Tools Card */}
          <div className="bg-neutral-2 rounded-lg border border-neutral-6 p-6">
            <div className="flex items-center gap-3 mb-4">
              <Wrench size={24} className="text-insight-9" />
              <h2 className="text-xl font-semibold text-neutral-12">
                Available Tools
              </h2>
              <span className="px-2 py-1 text-xs bg-insight-2 text-insight-11 rounded-full">
                {tools.length} tools available
              </span>
            </div>

            {tools.length === 0 ? (
              <p className="text-neutral-11">
                No tools available
              </p>
            ) : (
              <div className="space-y-2">
                {tools.map((tool) => (
                  <div
                    key={tool.name}
                    className="p-3 border border-neutral-6 rounded-lg hover:border-primary-9 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <Wrench size={16} className="text-insight-9" />
                      <div>
                        <h3 className="font-medium text-neutral-12">
                          {tool.name}
                        </h3>
                        {tool.description && (
                          <p className="text-sm text-neutral-11">
                            {tool.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Sprint 2: Enhanced Cards (persona-aware, components handle visibility) */}

          {/* Thinking Budget Card */}
          <ThinkingBudgetCard data={config?.thinkingBudgetDefaults} />

          {/* LLM Providers Card (shows supported providers) */}
          <LLMProvidersCard providers={config?.providers ?? []} />

          {/* Feature Flags Card */}
          <FeatureFlagsCard data={config?.featureFlagsSnapshot} />

          {/* Orchestrators List Card (shows registered orchestrators) */}
          <OrchestratorsListCard
            orchestrators={config?.orchestrators ?? []}
            featureFlags={config?.featureFlagsSnapshot ?? {}}
          />

          {/* Phase 6: Task Mapping Card (shows orchestrator-to-task mapping) */}
          <TaskMappingCard
            orchestrators={config?.orchestrators ?? []}
            featureFlags={config?.featureFlagsSnapshot ?? {}}
          />

          {/* Agent Metrics Card (orchestration, HITL, cost metrics - admin/developer only) */}
          <AgentMetricsCard />
        </div>
      </div>
    </div>
  );
}

export default AgentsPage;
