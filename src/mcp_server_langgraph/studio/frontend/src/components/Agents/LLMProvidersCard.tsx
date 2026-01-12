/**
 * LLMProvidersCard
 *
 * Displays a list of supported LLM providers with their capabilities.
 * Shows provider name, description, supported model types, and API key requirements.
 *
 * Visible only to admin and developer personas.
 */

import { useSelector } from "react-redux";
import { Cloud, Key, KeyRound } from "lucide-react";
import { selectPersona } from "../../store/slices/personaSlice";
import type { ProviderInfo } from "../../types/api";

interface LLMProvidersCardProps {
  providers: ProviderInfo[];
}

export function LLMProvidersCard({ providers }: LLMProvidersCardProps) {
  const persona = useSelector(selectPersona);

  // Only show for admin and developer personas
  if (!["admin", "developer"].includes(persona)) {
    return null;
  }

  // Don't render if no providers
  if (!providers || providers.length === 0) {
    return null;
  }

  return (
    <div className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
      <div className="flex items-center gap-3 mb-4">
        <Cloud size={24} className="text-info-500" />
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
          LLM Providers
        </h2>
        <span className="px-2 py-1 text-xs bg-info-100 dark:bg-info-900/30 text-info-700 dark:text-info-400 rounded-full">
          {providers.length} providers
        </span>
      </div>

      <div className="space-y-3">
        {providers.map((provider) => (
          <div
            key={provider.name}
            className="p-4 border border-neutral-200 dark:border-neutral-700 rounded-lg hover:border-info-500 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                    {provider.displayName}
                  </h3>
                  {provider.requiresApiKey ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400 rounded">
                      <Key size={12} />
                      API Key Required
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400 rounded">
                      <KeyRound size={12} />
                      No API Key
                    </span>
                  )}
                </div>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
                  {provider.description}
                </p>
              </div>
            </div>

            <div className="mt-3">
              <div className="text-xs text-neutral-500 dark:text-neutral-400 mb-1">
                Supported Model Types:
              </div>
              <div className="flex flex-wrap gap-1">
                {provider.supportedModelTypes.map((modelType) => (
                  <span
                    key={modelType}
                    className="px-2 py-0.5 text-xs bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 rounded"
                  >
                    {modelType}
                  </span>
                ))}
              </div>
            </div>

            {provider.apiKeyEnvVar && (
              <div className="mt-2 text-xs text-neutral-400 dark:text-neutral-400">
                Env: <code className="font-mono">{provider.apiKeyEnvVar}</code>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default LLMProvidersCard;
