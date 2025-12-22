/**
 * useWorkflowAPI - Thin Wrapper for Workflow RTK Query Hooks
 *
 * This wrapper module provides workflow-related API hooks while allowing
 * test files to mock this small module instead of the entire RTK Query API.
 *
 * This solves OOM issues in tests by preventing the full api/index.ts
 * from being evaluated during test module loading.
 *
 * Usage in components:
 * ```typescript
 * // Instead of: import { useGetWorkflowSuggestionsMutation } from "../api";
 * import { useGetWorkflowSuggestionsMutation } from "../hooks/useWorkflowAPI";
 * ```
 *
 * Usage in tests:
 * ```typescript
 * vi.mock("../hooks/useWorkflowAPI", () => ({
 *   useGetWorkflowSuggestionsMutation: () => [vi.fn(), { isLoading: false }],
 *   useListWorkflowExecutionsQuery: () => ({ data: [], isLoading: false }),
 * }));
 * ```
 */

export {
  useGetWorkflowSuggestionsMutation,
  useListWorkflowExecutionsQuery,
} from "../api";
