/**
 * ExecutionTraceTab Component
 *
 * Displays workflow node execution traces in DevTools.
 * Shows step-by-step execution with input/output data.
 */
import { useState, useCallback, useMemo } from "react";
import {
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  Play,
  SkipForward,
  Workflow,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import {
  useWorkflowExecution,
  type ExecutionStep,
} from "../hooks/useWorkflowExecution";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";
import type { ExecutionTraceTabProps } from "../types";

import { Button } from "@/components/UI";

// =============================================================================
// Subcomponents
// =============================================================================

interface StepStatusIconProps {
  status: ExecutionStep["status"];
  stepId: string;
}

function StepStatusIcon({ status, stepId }: StepStatusIconProps) {
  const iconProps = { size: 14, "aria-hidden": true };

  return (
    <span data-testid={`step-status-${stepId}`}>
      {status === "completed" && (
        <CheckCircle {...iconProps} className="text-success-9" />
      )}
      {status === "running" && (
        <Play {...iconProps} className="text-primary-9 animate-pulse" />
      )}
      {status === "pending" && (
        <Clock
          {...iconProps}
          className="text-neutral-9"
        />
      )}
      {status === "error" && (
        <AlertCircle {...iconProps} className="text-error-9" />
      )}
      {status === "skipped" && (
        <SkipForward
          {...iconProps}
          className="text-neutral-9"
        />
      )}
    </span>
  );
}

interface ExecutionStepRowProps {
  step: ExecutionStep;
  isCurrent: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

function ExecutionStepRow({
  step,
  isCurrent,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpand,
}: ExecutionStepRowProps) {
  return (
    <div
      data-testid={`execution-step-${step.id}`}
      data-current={isCurrent}
      className={cn(
        "flex items-center gap-2 px-2 py-1.5 cursor-pointer",
        "border-b border-neutral-5",
        "hover:bg-neutral-a6",
        isSelected && "bg-primary-1 dark:bg-primary-a3",
        isCurrent &&
          "bg-warning-3 bg-warning-3 border-l-2 border-l-warning-500",
      )}
      onClick={onSelect}
    >
      {/* Expand button */}
      <Button
        variant="secondary"
        className="p-0.5 hover:bg-neutral-3 rounded"
        data-testid={`expand-step-${step.id}`}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggleExpand();
        }}
        aria-expanded={isExpanded}
        aria-label={
          isExpanded ? `Collapse ${step.nodeName}` : `Expand ${step.nodeName}`
        }
      >
        {isExpanded ? (
          <ChevronDown
            size={12}
            className="text-neutral-10"
          />
        ) : (
          <ChevronRight
            size={12}
            className="text-neutral-10"
          />
        )}
      </Button>
      {/* Status icon */}
      <StepStatusIcon status={step.status} stepId={step.id} />
      {/* Step name */}
      <span className="flex-1 text-sm text-neutral-11">
        {step.nodeName}
      </span>
      {/* Duration */}
      {step.duration > 0 && (
        <span className="text-xs text-neutral-10">
          {step.duration}ms
        </span>
      )}
    </div>
  );
}

interface StepDetailsProps {
  step: ExecutionStep;
}

function StepDetails({ step }: StepDetailsProps) {
  return (
    <div
      data-testid={`step-details-${step.id}`}
      className="px-4 py-2 bg-neutral-1 text-xs"
    >
      <div className="grid grid-cols-1 gap-3">
        {/* Input */}
        {step.input && (
          <div data-testid={`step-input-${step.id}`}>
            <span className="text-neutral-10 font-medium">
              Input:
            </span>
            <pre className="mt-1 p-2 bg-neutral-2 rounded text-neutral-11 overflow-x-auto">
              {JSON.stringify(step.input, null, 2)}
            </pre>
          </div>
        )}

        {/* Output */}
        {step.output && (
          <div data-testid={`step-output-${step.id}`}>
            <span className="text-neutral-10 font-medium">
              Output:
            </span>
            <pre className="mt-1 p-2 bg-neutral-2 rounded text-neutral-11 overflow-x-auto">
              {JSON.stringify(step.output, null, 2)}
            </pre>
          </div>
        )}

        {/* Error */}
        {step.error && (
          <div className={STATUS_TEXT_COLORS.error}>
            <span className="font-medium">Error:</span>
            <p className="mt-1">{step.error}</p>
          </div>
        )}

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-2 text-neutral-10">
          <div>
            <span>Node ID:</span>
            <span className="ml-2 text-neutral-11">
              {step.nodeId}
            </span>
          </div>
          <div>
            <span>Status:</span>
            <span className="ml-2 text-neutral-11 capitalize">
              {step.status}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ExecutionTraceTab({
  workflowId,
  onNodeHighlight,
}: ExecutionTraceTabProps) {
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

  const { steps, isLoading, error, refetch, currentStepId } =
    useWorkflowExecution({ workflowId });

  // Filter steps by timeline window for time-travel debugging
  const filteredSteps = useMemo(() => {
    if (!steps) return [];
    if (!timeline.timeWindow) return steps;

    return steps.filter((step) => {
      const stepEnd = (step.startTime ?? 0) + (step.duration ?? 0);
      return (
        (step.startTime ?? 0) <= timeline.timeWindow!.end &&
        stepEnd >= timeline.timeWindow!.start
      );
    });
  }, [steps, timeline.timeWindow]);

  // Handle step selection
  const handleStepSelect = useCallback(
    (step: ExecutionStep) => {
      if (selectedStepId === step.id) {
        setSelectedStepId(null);
        onNodeHighlight?.(null);
      } else {
        setSelectedStepId(step.id);
        onNodeHighlight?.(step.nodeId);
      }
    },
    [selectedStepId, onNodeHighlight],
  );

  // Handle step expand/collapse
  const toggleStepExpand = useCallback((stepId: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="execution-trace-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="execution-trace-loading"
          className="flex-1 flex items-center justify-center"
        >
          <Loader2 className="w-8 h-8 animate-spin text-primary-9" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="execution-trace-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="execution-trace-error"
          className={cn(
            "flex-1 flex flex-col items-center justify-center",
            STATUS_TEXT_COLORS.error,
          )}
        >
          <AlertCircle size={32} className="mb-2" />
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  // Empty state (use filteredSteps for time-travel filtered view)
  if (filteredSteps.length === 0) {
    return (
      <div
        data-testid="execution-trace-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="execution-trace-empty"
          className="flex-1 flex flex-col items-center justify-center text-neutral-9"
        >
          <Workflow size={32} className="mb-2 opacity-50" />
          <p className="text-sm">No execution data available</p>
          <p className="text-xs mt-1">
            Run the workflow to see execution traces
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="execution-trace-tab"
      className="flex flex-col h-full bg-neutral-1"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
        {/* Workflow indicator */}
        <div className="flex items-center gap-1.5">
          <Workflow
            size={14}
            className="text-neutral-10"
            aria-hidden="true"
          />
          <h3 className="text-xs text-neutral-11">
            Execution
          </h3>
          <span className="text-xs text-neutral-10 ml-1 px-1.5 py-0.5 bg-neutral-2 rounded">
            {workflowId}
          </span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Step count */}
        <span className="text-xs text-neutral-10">
          {filteredSteps.filter((s) => s.status === "completed").length}/
          {filteredSteps.length} steps
          {timeline.timeWindow && filteredSteps.length !== steps.length && (
            <span className="ml-1 text-neutral-9">
              ({steps.length} total)
            </span>
          )}
        </span>

        {/* Refresh button */}
        <Button size="icon"
          variant="secondary"
          className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
          data-testid="refresh-execution-button"
          type="button"
          onClick={refetch}
          aria-label="Refresh execution"
        >
          <RefreshCw size={14} />
        </Button>
      </div>
      {/* Steps list - filtered by timeline window for time-travel debugging */}
      <div className="flex-1 overflow-y-auto">
        {filteredSteps.map((step) => (
          <div key={step.id}>
            <ExecutionStepRow
              step={step}
              isCurrent={currentStepId === step.id}
              isSelected={selectedStepId === step.id}
              isExpanded={expandedSteps.has(step.id)}
              onSelect={() => handleStepSelect(step)}
              onToggleExpand={() => toggleStepExpand(step.id)}
            />
            {expandedSteps.has(step.id) && <StepDetails step={step} />}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ExecutionTraceTab;
