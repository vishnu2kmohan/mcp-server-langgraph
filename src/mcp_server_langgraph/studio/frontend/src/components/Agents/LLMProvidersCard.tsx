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
    <div className="bg-neutral-1 rounded-lg border border-neutral-5 p-6">
      <div className="flex items-center gap-3 mb-4">
        <Cloud size={24} className="text-info-9" />
        <h2 className="text-xl font-semibold text-neutral-12">LLM Providers</h2>
        <span className="px-2 py-1 text-xs bg-info-3 bg-info-4 text-info-10 dark:text-info-11 rounded-full">
          {providers.length} providers
        </span>
      </div>

      <div className="space-y-3">
        {providers.map((provider) => (
          <div
            key={provider.name}
            className="p-4 border border-neutral-5 rounded-lg hover:border-info-9 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium text-neutral-12">
                    {provider.displayName}
                  </h3>
                  {provider.requiresApiKey ? (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-warning-3 dark:bg-warning-a4 text-warning-10 dark:text-warning-9 rounded">
                      <Key size={12} />
                      API Key Required
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-success-3 bg-success-4 text-success-11 dark:text-success-7 rounded">
                      <KeyRound size={12} />
                      No API Key
                    </span>
                  )}
                </div>
                <p className="text-sm text-neutral-10 mt-1">
                  {provider.description}
                </p>
              </div>
            </div>

            <div className="mt-3">
              <div className="text-xs text-neutral-10 mb-1">
                Supported Model Types:
              </div>
              <div className="flex flex-wrap gap-1">
                {provider.supportedModelTypes.map((modelType) => (
                  <span
                    key={modelType}
                    className="px-2 py-0.5 text-xs bg-neutral-2 text-neutral-11 rounded"
                  >
                    {modelType}
                  </span>
                ))}
              </div>
            </div>

            {provider.apiKeyEnvVar && (
              <div className="mt-2 text-xs text-neutral-9">
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
