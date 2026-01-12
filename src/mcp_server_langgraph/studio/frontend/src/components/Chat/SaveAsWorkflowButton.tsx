/**
 * SaveAsWorkflowButton
 *
 * Button component for bootstrapping a workflow from a chat session.
 * Uses RTK Query for API calls with automatic caching.
 */

import { useState, useEffect } from "react";
import { Save, Loader2, CheckCircle, ExternalLink } from "lucide-react";
import { useBootstrapWorkflowMutation } from "../../api";
import type { BootstrapWorkflowResponseCamelCase } from "../../types/api";

import { Button } from "@/components/UI";

interface SaveAsWorkflowButtonProps {
  sessionId: string;
  disabled?: boolean;
}

export function SaveAsWorkflowButton({
  sessionId,
  disabled = false,
}: SaveAsWorkflowButtonProps) {
  const [bootstrapWorkflow, { isLoading }] = useBootstrapWorkflowMutation();
  const [success, setSuccess] =
    useState<BootstrapWorkflowResponseCamelCase | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        setSuccess(null);
      }, 5000);

      return () => clearTimeout(timer);
    }
    return undefined;
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 5000);

      return () => clearTimeout(timer);
    }
    return undefined;
  }, [error]);

  const handleSaveAsWorkflow = async () => {
    if (disabled || isLoading) return;

    setError(null);
    setSuccess(null);

    try {
      const result = await bootstrapWorkflow(sessionId).unwrap();
      setSuccess(result);
    } catch (err) {
      // RTK Query error handling - handles both string and Pydantic validation error formats
      let errorMessage = "Failed to create workflow";

      if (err && typeof err === "object" && "data" in err) {
        const data = err.data as {
          detail?: string | Array<{ msg?: string; type?: string }>;
          message?: string;
        };

        if (typeof data.detail === "string") {
          // FastAPI HTTPException format: { detail: "error message" }
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail) && data.detail.length > 0) {
          // Pydantic validation error format: { detail: [{type, loc, msg, input}] }
          const messages = data.detail
            .map((e) => e.msg || e.type || "Validation error")
            .join("; ");
          errorMessage = messages || "Validation error";
        } else if (data.message) {
          // Alternative error format: { message: "error" }
          errorMessage = data.message;
        }
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }

      setError(errorMessage);
    }
  };

  return (
    <div className="relative">
      <Button
        variant="secondary"
        className="flex px-3 py-1.5 text-sm bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600"
        onClick={handleSaveAsWorkflow}
        disabled={disabled || isLoading}
      >
        {isLoading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : success ? (
          <CheckCircle size={16} className="text-success-500" />
        ) : (
          <Save size={16} />
        )}
        {isLoading ? "Saving..." : success ? "Saved!" : "Save as Workflow"}
      </Button>
      {/* Success Message */}
      {success && (
        <div className="absolute top-full right-0 mt-2 p-4 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg shadow-lg min-w-[300px] z-10">
          <div className="flex items-start gap-3">
            <CheckCircle size={20} className="text-success-500 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-success-900 dark:text-success-100">
                Workflow Created
              </p>
              <p className="text-sm text-success-700 dark:text-success-300 mt-1">
                {success.name}
              </p>
              <a
                href={`/studio/workflows?id=${success.workflowId}`}
                className="inline-flex items-center gap-1 mt-2 text-sm text-success-600 dark:text-success-400 hover:underline"
              >
                View Workflow
                <ExternalLink size={14} />
              </a>
            </div>
          </div>
        </div>
      )}
      {/* Error Message */}
      {error && (
        <div className="absolute top-full right-0 mt-2 p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg shadow-lg min-w-[300px] z-10">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <p className="font-medium text-error-900 dark:text-error-100">
                Failed to Create Workflow
              </p>
              <p className="text-sm text-error-700 dark:text-error-300 mt-1">
                {error}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SaveAsWorkflowButton;
