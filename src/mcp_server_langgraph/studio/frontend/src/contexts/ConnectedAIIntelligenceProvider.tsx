/**
 * ConnectedAIIntelligenceProvider
 *
 * A wrapper component that connects AIIntelligenceProvider to feature flags.
 * Uses useAIIntelligenceConfig hook to bridge FeatureFlagContext to AIIntelligenceProvider.
 *
 * This component should be placed inside FeatureFlagProvider but before
 * components that need AI intelligence features.
 *
 * Usage:
 * ```tsx
 * <FeatureFlagProvider>
 *   <ConnectedAIIntelligenceProvider>
 *     <App />
 *   </ConnectedAIIntelligenceProvider>
 * </FeatureFlagProvider>
 * ```
 */

import type { ReactNode } from "react";
import { AIIntelligenceProvider } from "./AIIntelligenceContext";
import { useAIIntelligenceConfig } from "../hooks/useAIIntelligenceConfig";
import { usePersonaCacheInvalidation } from "../hooks/usePersonaCacheInvalidation";

// =============================================================================
// Types
// =============================================================================

export interface ConnectedAIIntelligenceProviderProps {
  children: ReactNode;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Connected AIIntelligenceProvider that bridges feature flags to AI config.
 *
 * Features:
 * - Automatically maps feature flags to AI features
 * - Integrates user context from Redux
 * - Provides loading state awareness
 */
export function ConnectedAIIntelligenceProvider({
  children,
}: ConnectedAIIntelligenceProviderProps) {
  const config = useAIIntelligenceConfig();

  // Enable cache invalidation on persona change when AI features are enabled
  usePersonaCacheInvalidation({ enabled: config.enabled });

  return (
    <AIIntelligenceProvider config={config}>
      {children}
    </AIIntelligenceProvider>
  );
}
