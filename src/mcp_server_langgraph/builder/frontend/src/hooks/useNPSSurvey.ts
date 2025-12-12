/**
 * useNPSSurvey Hook
 *
 * Manages NPS survey display triggers:
 * - After first code export
 * - After 5th workflow save
 * - Monthly for returning users (if 30+ days since last NPS)
 */

import { useState, useCallback, useMemo } from 'react';

// ==============================================================================
// Types
// ==============================================================================

export interface UseNPSSurveyResult {
  shouldShowNPS: boolean;
  recordCodeExport: () => void;
  recordWorkflowSave: () => void;
  dismissNPS: () => void;
  submitNPS: (score: number) => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const STORAGE_KEYS = {
  CODE_EXPORT_SHOWN: 'nps_code_export_shown',
  WORKFLOW_SAVE_COUNT: 'nps_workflow_save_count',
  WORKFLOW_SAVE_NPS_SHOWN: 'nps_workflow_save_shown',
  LAST_SUBMITTED: 'nps_last_submitted',
} as const;

const WORKFLOW_SAVE_THRESHOLD = 5;
const COOLDOWN_DAYS = 30;

// ==============================================================================
// Helpers
// ==============================================================================

function isWithinCooldown(): boolean {
  const lastSubmitted = localStorage.getItem(STORAGE_KEYS.LAST_SUBMITTED);
  if (!lastSubmitted) return false;

  const lastDate = new Date(lastSubmitted).getTime();
  const now = Date.now();
  const daysSince = (now - lastDate) / (1000 * 60 * 60 * 24);

  return daysSince < COOLDOWN_DAYS;
}

// ==============================================================================
// Hook
// ==============================================================================

export function useNPSSurvey(): UseNPSSurveyResult {
  const [showNPS, setShowNPS] = useState(false);

  const recordCodeExport = useCallback(() => {
    // Check cooldown
    if (isWithinCooldown()) return;

    // Check if already shown for code export
    const alreadyShown = localStorage.getItem(STORAGE_KEYS.CODE_EXPORT_SHOWN);
    if (alreadyShown) return;

    // Trigger NPS
    localStorage.setItem(STORAGE_KEYS.CODE_EXPORT_SHOWN, 'true');
    setShowNPS(true);
  }, []);

  const recordWorkflowSave = useCallback(() => {
    // Check cooldown
    if (isWithinCooldown()) return;

    // Check if already shown for workflow saves
    const alreadyShown = localStorage.getItem(STORAGE_KEYS.WORKFLOW_SAVE_NPS_SHOWN);
    if (alreadyShown) return;

    // Increment save count
    const currentCount = parseInt(
      localStorage.getItem(STORAGE_KEYS.WORKFLOW_SAVE_COUNT) || '0',
      10
    );
    const newCount = currentCount + 1;
    localStorage.setItem(STORAGE_KEYS.WORKFLOW_SAVE_COUNT, String(newCount));

    // Check if threshold reached
    if (newCount >= WORKFLOW_SAVE_THRESHOLD) {
      localStorage.setItem(STORAGE_KEYS.WORKFLOW_SAVE_NPS_SHOWN, 'true');
      setShowNPS(true);
    }
  }, []);

  const dismissNPS = useCallback(() => {
    setShowNPS(false);
  }, []);

  const submitNPS = useCallback((score: number) => {
    setShowNPS(false);
    localStorage.setItem(STORAGE_KEYS.LAST_SUBMITTED, new Date().toISOString());
    // Score is passed to callback but can also be sent to analytics
    console.log('NPS Score submitted:', score);
  }, []);

  return useMemo(
    () => ({
      shouldShowNPS: showNPS,
      recordCodeExport,
      recordWorkflowSave,
      dismissNPS,
      submitNPS,
    }),
    [showNPS, recordCodeExport, recordWorkflowSave, dismissNPS, submitNPS]
  );
}

export default useNPSSurvey;
