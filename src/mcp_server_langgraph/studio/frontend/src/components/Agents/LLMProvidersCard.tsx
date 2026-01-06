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
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center gap-3 mb-4">
        <Cloud size={24} className="text-cyan-500" />
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          LLM Providers
        </h2>
        <span className="px-2 py-1 text-xs bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-400 rounded-full">
          {providers.length} providers
        </span>
      </div>

      <div className="space-y-3">
        {providers.map((provider) => (
          <div
            key={provider.name}
            className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-cyan-500 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">
                    {provider.displayName}
                  </h3>
                  {provider.requiresApiKey ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 rounded">
                      <Key size={12} />
                      API Key Required
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                      <KeyRound size={12} />
                      No API Key
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {provider.description}
                </p>
              </div>
            </div>

            <div className="mt-3">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                Supported Model Types:
              </div>
              <div className="flex flex-wrap gap-1">
                {provider.supportedModelTypes.map((modelType) => (
                  <span
                    key={modelType}
                    className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
                  >
                    {modelType}
                  </span>
                ))}
              </div>
            </div>

            {provider.apiKeyEnvVar && (
              <div className="mt-2 text-xs text-gray-400 dark:text-gray-500">
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
