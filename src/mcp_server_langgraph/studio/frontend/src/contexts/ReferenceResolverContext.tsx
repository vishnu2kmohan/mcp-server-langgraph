/**
 * ReferenceResolverContext
 *
 * Provides batch resolution of markdown references.
 * Wraps a message's content and resolves all references in a single API call.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useResolveReferencesMutation } from '@/api';
import type {
  ParsedReference,
  ResolvedReference,
  ReferenceResolverContextValue,
  ReferenceResolveRequest,
} from '@/types/references';
import { getReferenceKey } from '@/types/references';

/**
 * Default context value (used when not wrapped in provider).
 */
const defaultContextValue: ReferenceResolverContextValue = {
  resolvedRefs: new Map(),
  isLoading: false,
  error: undefined,
  resolve: async () => {},
};

/**
 * Context for reference resolution.
 */
const ReferenceResolverContext = createContext<ReferenceResolverContextValue>(
  defaultContextValue
);

/**
 * Hook to access reference resolver context.
 */
// eslint-disable-next-line react-refresh/only-export-components -- Hook export alongside context provider is standard pattern
export function useReferenceResolver(): ReferenceResolverContextValue {
  return useContext(ReferenceResolverContext);
}

export interface ReferenceResolverProviderProps {
  /** Unique identifier for this message (for caching) */
  messageId: string;
  /** Parsed references to resolve */
  references: ParsedReference[];
  /** Child components */
  children: ReactNode;
}

/**
 * Provider component that resolves references in batch.
 *
 * Usage:
 * ```tsx
 * <ReferenceResolverProvider messageId={msg.id} references={parsedRefs}>
 *   <MarkdownContent>{msg.content}</MarkdownContent>
 * </ReferenceResolverProvider>
 * ```
 */
export function ReferenceResolverProvider({
  messageId,
  references,
  children,
}: ReferenceResolverProviderProps) {
  const [resolvedRefs, setResolvedRefs] = useState<Map<string, ResolvedReference>>(
    new Map()
  );
  const [resolveRefs, { isLoading, error }] = useResolveReferencesMutation();

  // Resolve references when they change
  useEffect(() => {
    if (references.length === 0) {
      return;
    }

    // Deduplicate references
    const uniqueRefs = new Map<string, ReferenceResolveRequest>();
    for (const ref of references) {
      const key = getReferenceKey(ref);
      if (!uniqueRefs.has(key)) {
        uniqueRefs.set(key, {
          type: ref.type,
          qualifier: ref.qualifier,
          id: ref.id,
        });
      }
    }

    // Skip if all refs are already resolved
    const unresolvedRefs = [...uniqueRefs.values()].filter(
      (ref) => !resolvedRefs.has(getReferenceKey(ref))
    );

    if (unresolvedRefs.length === 0) {
      return;
    }

    // Batch resolve
    resolveRefs({ references: unresolvedRefs })
      .unwrap()
      .then((response) => {
        setResolvedRefs((prev) => {
          const next = new Map(prev);
          for (const resolved of response.resolved) {
            // Cast API response to ResolvedReference (type field is validated)
            const typedResolved = resolved as ResolvedReference;
            const key = getReferenceKey(typedResolved);
            next.set(key, typedResolved);
          }
          return next;
        });
      })
      .catch((err) => {
        console.error('Failed to resolve references:', err);
      });
  }, [messageId, references, resolveRefs, resolvedRefs]);

  // Memoize context value
  const contextValue = useMemo<ReferenceResolverContextValue>(
    () => ({
      resolvedRefs,
      isLoading,
      error: error ? String(error) : undefined,
      resolve: async (refs) => {
        const request = refs.map((r) => ({
          type: r.type,
          qualifier: r.qualifier,
          id: r.id,
        }));
        try {
          const response = await resolveRefs({ references: request }).unwrap();
          setResolvedRefs((prev) => {
            const next = new Map(prev);
            for (const resolved of response.resolved) {
              // Cast API response to ResolvedReference (type field is validated)
              const typedResolved = resolved as ResolvedReference;
              const key = getReferenceKey(typedResolved);
              next.set(key, typedResolved);
            }
            return next;
          });
        } catch (err) {
          console.error('Failed to resolve references:', err);
        }
      },
    }),
    [resolvedRefs, isLoading, error, resolveRefs]
  );

  return (
    <ReferenceResolverContext.Provider value={contextValue}>
      {children}
    </ReferenceResolverContext.Provider>
  );
}
