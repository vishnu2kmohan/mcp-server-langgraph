/**
 * useConfirmation Hook
 *
 * Hook for managing confirmation dialog state.
 * Provides a clean API for showing confirmation dialogs
 * and handling user responses.
 */

import { useState, useCallback } from "react";
import type { DialogSeverity } from "../components/Common/ConfirmationDialog";

// ==============================================================================
// Types
// ==============================================================================

export interface ConfirmationConfig {
  /** Dialog title */
  title: string;
  /** Dialog message */
  message: string;
  /** Severity level */
  severity?: DialogSeverity;
  /** Text user must type to confirm (for dangerous actions) */
  confirmText?: string;
  /** Confirm button label */
  confirmLabel?: string;
  /** Cancel button label */
  cancelLabel?: string;
}

export interface ConfirmationState extends ConfirmationConfig {
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Whether an action is in progress */
  isLoading: boolean;
}

export interface UseConfirmationReturn {
  /** Current confirmation state */
  state: ConfirmationState;
  /** Show a confirmation dialog */
  confirm: (config: ConfirmationConfig) => Promise<boolean>;
  /** Close the dialog */
  close: () => void;
  /** Set loading state */
  setLoading: (loading: boolean) => void;
}

// ==============================================================================
// Default State
// ==============================================================================

const DEFAULT_STATE: ConfirmationState = {
  isOpen: false,
  isLoading: false,
  title: "",
  message: "",
  severity: "info",
};

// ==============================================================================
// Hook
// ==============================================================================

export function useConfirmation(): UseConfirmationReturn {
  const [state, setState] = useState<ConfirmationState>(DEFAULT_STATE);
  const [resolveRef, setResolveRef] = useState<{
    resolve: (value: boolean) => void;
  } | null>(null);

  const confirm = useCallback(
    (config: ConfirmationConfig): Promise<boolean> => {
      return new Promise((resolve) => {
        setState({
          ...DEFAULT_STATE,
          ...config,
          isOpen: true,
        });
        setResolveRef({ resolve });
      });
    },
    [],
  );

  const close = useCallback(() => {
    if (resolveRef) {
      resolveRef.resolve(false);
      setResolveRef(null);
    }
    setState(DEFAULT_STATE);
  }, [resolveRef]);

  const setLoading = useCallback((loading: boolean) => {
    setState((prev) => ({ ...prev, isLoading: loading }));
  }, []);

  // Create handlers for the dialog
  const handleConfirm = useCallback(() => {
    if (resolveRef) {
      resolveRef.resolve(true);
      setResolveRef(null);
    }
    setState(DEFAULT_STATE);
  }, [resolveRef]);

  const handleCancel = useCallback(() => {
    close();
  }, [close]);

  return {
    state: {
      ...state,
      // Attach handlers to state for easy prop spreading
      onConfirm: handleConfirm,
      onCancel: handleCancel,
    } as ConfirmationState & { onConfirm: () => void; onCancel: () => void },
    confirm,
    close,
    setLoading,
  };
}

export default useConfirmation;
