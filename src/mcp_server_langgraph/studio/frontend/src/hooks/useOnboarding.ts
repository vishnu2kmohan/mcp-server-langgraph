/**
 * useOnboarding Hook
 *
 * Hook to manage onboarding flow for first-time users.
 * Features:
 * - First-time user detection
 * - Step-by-step navigation
 * - Skip functionality
 * - Completion tracking
 * - Persistence to localStorage
 */

import { useState, useCallback, useMemo } from "react";
import { storage, STORAGE_KEYS } from "../utils/storage";

// ==============================================================================
// Types
// ==============================================================================

export interface OnboardingStep {
  title: string;
  description: string;
  icon?: string;
}

export interface OnboardingState {
  isFirstTime: boolean;
  showOnboarding: boolean;
  currentStep: number;
  steps: OnboardingStep[];
  totalSteps: number;
  isLastStep: boolean;
  startOnboarding: () => void;
  closeOnboarding: () => void;
  nextStep: () => void;
  previousStep: () => void;
  goToStep: (step: number) => void;
  completeOnboarding: () => void;
  skipOnboarding: () => void;
  resetOnboarding: () => void;
}

// ==============================================================================
// Constants
// ==============================================================================

const STORAGE_KEY = STORAGE_KEYS.ONBOARDING;

const DEFAULT_STEPS: OnboardingStep[] = [
  {
    title: "Welcome to LangGraph Studio",
    description:
      "Build and visualize AI workflows with ease. Let us show you around!",
    icon: "rocket",
  },
  {
    title: "Create Chat Sessions",
    description:
      "Start conversations with AI agents. Your chats are automatically saved and organized.",
    icon: "chat",
  },
  {
    title: "Visualize Workflows",
    description:
      "See your agent workflows in real-time with our interactive graph view.",
    icon: "workflow",
  },
  {
    title: "Customize Your Experience",
    description:
      "Adjust settings, themes, and keyboard shortcuts to work your way.",
    icon: "settings",
  },
];

// ==============================================================================
// Helper Functions
// ==============================================================================

interface StoredState {
  completed: boolean;
}

function loadState(): StoredState | null {
  return storage.get<StoredState>(STORAGE_KEY, { expectObject: true }) ?? null;
}

function saveState(state: StoredState): void {
  storage.set(STORAGE_KEY, state);
}

function clearState(): void {
  storage.remove(STORAGE_KEY);
}

// ==============================================================================
// Hook
// ==============================================================================

export function useOnboarding(customSteps?: OnboardingStep[]): OnboardingState {
  const steps = customSteps || DEFAULT_STEPS;

  // Load initial state from localStorage
  const [isFirstTime, setIsFirstTime] = useState(() => {
    const stored = loadState();
    return !stored?.completed;
  });

  const [showOnboarding, setShowOnboarding] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  const totalSteps = steps.length;
  const isLastStep = currentStep === totalSteps - 1;

  const startOnboarding = useCallback(() => {
    setShowOnboarding(true);
    setCurrentStep(0);
  }, []);

  const closeOnboarding = useCallback(() => {
    setShowOnboarding(false);
  }, []);

  const nextStep = useCallback(() => {
    setCurrentStep((prev) => Math.min(prev + 1, totalSteps - 1));
  }, [totalSteps]);

  const previousStep = useCallback(() => {
    setCurrentStep((prev) => Math.max(prev - 1, 0));
  }, []);

  const goToStep = useCallback(
    (step: number) => {
      setCurrentStep(Math.max(0, Math.min(step, totalSteps - 1)));
    },
    [totalSteps],
  );

  const completeOnboarding = useCallback(() => {
    setShowOnboarding(false);
    setIsFirstTime(false);
    saveState({ completed: true });
  }, []);

  const skipOnboarding = useCallback(() => {
    setShowOnboarding(false);
    setIsFirstTime(false);
    saveState({ completed: true });
  }, []);

  const resetOnboarding = useCallback(() => {
    clearState();
    setIsFirstTime(true);
    setCurrentStep(0);
  }, []);

  return useMemo(
    () => ({
      isFirstTime,
      showOnboarding,
      currentStep,
      steps,
      totalSteps,
      isLastStep,
      startOnboarding,
      closeOnboarding,
      nextStep,
      previousStep,
      goToStep,
      completeOnboarding,
      skipOnboarding,
      resetOnboarding,
    }),
    [
      isFirstTime,
      showOnboarding,
      currentStep,
      steps,
      totalSteps,
      isLastStep,
      startOnboarding,
      closeOnboarding,
      nextStep,
      previousStep,
      goToStep,
      completeOnboarding,
      skipOnboarding,
      resetOnboarding,
    ],
  );
}

export default useOnboarding;
