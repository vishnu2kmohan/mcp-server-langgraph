/**
 * SaveAsWorkflowButton
 *
 * Button component for bootstrapping a workflow from a chat session.
 * Calls the bootstrap API and shows success/error feedback.
 */

import { useState, useEffect } from 'react';
import { Save, Loader2, CheckCircle, ExternalLink } from 'lucide-react';

interface SaveAsWorkflowButtonProps {
  sessionId: string;
  disabled?: boolean;
}

interface BootstrapResponse {
  workflow_id: string;
  name: string;
}

interface BootstrapError {
  detail: string;
}

export function SaveAsWorkflowButton({ sessionId, disabled = false }: SaveAsWorkflowButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState<BootstrapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        setSuccess(null);
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [error]);

  const handleSaveAsWorkflow = async () => {
    if (disabled || isLoading) return;

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(
        `/api/v1/sessions/${sessionId}/bootstrap-workflow`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        const errorData: BootstrapError = await response.json();
        throw new Error(errorData.detail || 'Failed to create workflow');
      }

      const data: BootstrapResponse = await response.json();
      setSuccess(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create workflow');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={handleSaveAsWorkflow}
        disabled={disabled || isLoading}
        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isLoading ? (
          <Loader2 size={16} className="animate-spin" />
        ) : success ? (
          <CheckCircle size={16} className="text-green-500" />
        ) : (
          <Save size={16} />
        )}
        {isLoading ? 'Saving...' : success ? 'Saved!' : 'Save as Workflow'}
      </button>

      {/* Success Message */}
      {success && (
        <div className="absolute top-full right-0 mt-2 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg shadow-lg min-w-[300px] z-10">
          <div className="flex items-start gap-3">
            <CheckCircle size={20} className="text-green-500 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-green-900 dark:text-green-100">
                Workflow Created
              </p>
              <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                {success.name}
              </p>
              <a
                href={`/studio/workflows?id=${success.workflow_id}`}
                className="inline-flex items-center gap-1 mt-2 text-sm text-green-600 dark:text-green-400 hover:underline"
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
        <div className="absolute top-full right-0 mt-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg shadow-lg min-w-[300px] z-10">
          <div className="flex items-start gap-3">
            <div className="flex-1">
              <p className="font-medium text-red-900 dark:text-red-100">
                Failed to Create Workflow
              </p>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
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
