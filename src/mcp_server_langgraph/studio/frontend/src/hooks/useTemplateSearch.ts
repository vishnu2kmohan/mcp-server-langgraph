/**
 * useTemplateSearch Hook
 *
 * React hook for searching plan templates with pagination and sorting.
 * Wraps the RTK Query useSearchTemplatesQuery hook with convenient unwrapping.
 */

import { useMemo } from "react";
import { useSearchTemplatesQuery } from "../api";

export interface TemplateSearchParams {
  query?: string;
  orchestrator?: string;
  tags?: string;
  sortBy?: "popularity" | "success_rate" | "recent";
  sortOrder?: "asc" | "desc";
  limit?: number;
  offset?: number;
}

export interface PlanTemplateResult {
  templateId: string;
  name: string;
  description: string;
  orchestrator: string;
  thinkingBudget: string;
  critiqueRounds: number;
  autoApprove: boolean;
  createdBy: string;
  createdAt: string;
  useCount: number;
  successRate: number;
  tags: string[];
}

export interface UseTemplateSearchResult {
  /** List of matching templates */
  templates: PlanTemplateResult[];
  /** Total count of matching templates (for pagination) */
  total: number;
  /** Current page limit */
  limit: number;
  /** Current offset */
  offset: number;
  /** Whether data is loading */
  isLoading: boolean;
  /** Whether initial fetch is loading */
  isFetching: boolean;
  /** Error if any */
  error: unknown;
  /** Refetch function */
  refetch: () => void;
}

/**
 * Search plan templates with pagination and sorting.
 *
 * @example
 * ```tsx
 * const { templates, total, isLoading } = useTemplateSearch({
 *   query: "code review",
 *   sortBy: "popularity",
 *   limit: 10,
 * });
 * ```
 */
export function useTemplateSearch(
  params: TemplateSearchParams = {},
): UseTemplateSearchResult {
  const { data, isLoading, isFetching, error, refetch } =
    useSearchTemplatesQuery(params);

  const result = useMemo(
    () => ({
      templates: data?.templates ?? [],
      total: data?.total ?? 0,
      limit: data?.limit ?? params.limit ?? 20,
      offset: data?.offset ?? params.offset ?? 0,
      isLoading,
      isFetching,
      error,
      refetch,
    }),
    [data, isLoading, isFetching, error, refetch, params.limit, params.offset],
  );

  return result;
}

export default useTemplateSearch;
