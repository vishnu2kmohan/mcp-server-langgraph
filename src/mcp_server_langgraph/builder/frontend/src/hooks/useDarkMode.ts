/**
 * Dark Mode Hook
 *
 * Re-exports from shared frontend library with backward-compatible API.
 * See: src/mcp_server_langgraph/shared/frontend/src/hooks/useDarkMode.ts
 *
 * @deprecated Import from '@mcp-server-langgraph/shared-frontend' instead
 */

// Re-export from shared library
import { useDarkMode as useDarkModeShared } from '../../../../shared/frontend/src/hooks/useDarkMode';

export {
  useDarkMode,
  type UseDarkModeOptions,
  type UseDarkModeResult,
} from '../../../../shared/frontend/src/hooks/useDarkMode';

// Backward-compatible type alias for Builder
export type DarkModeResult = {
  isDarkMode: boolean;
  toggle: () => void;
  setDarkMode: (value: boolean) => void;
};

export default useDarkModeShared;
