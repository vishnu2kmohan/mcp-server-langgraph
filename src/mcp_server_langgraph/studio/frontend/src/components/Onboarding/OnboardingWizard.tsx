/**
 * OnboardingWizard Component
 *
 * Multi-step onboarding wizard for new users.
 * Step 1: Welcome + value proposition
 * Step 2: Persona selection (admin/developer/user)
 * Step 3: Template selection
 * Step 4: Quick tour of interface
 *
 * Phase 6.5: AI-Powered Onboarding Personalization
 * - Uses useAIOnboarding to detect user intent
 * - Pre-selects persona based on AI prediction
 * - Highlights recommended templates
 * - Offers skip suggestions for advanced users
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  X,
  Shield,
  Code,
  User,
  FileCode,
  Bot,
  Server,
  Users,
  Command,
  MessageSquare,
  GitBranch,
  Zap,
} from "lucide-react";
import { useAIOnboarding } from "../../hooks/useAIOnboarding";

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
}

export type Persona = "admin" | "developer" | "user";

export interface OnboardingResult {
  persona: Persona;
  template: WorkflowTemplate | null;
  tourCompleted: boolean;
}

export interface OnboardingWizardProps {
  isOpen: boolean;
  onComplete: (result: OnboardingResult) => void;
  onSkip: () => void;
  templates: WorkflowTemplate[];
}

interface PersonaOption {
  id: Persona;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const personaOptions: PersonaOption[] = [
  {
    id: "admin",
    title: "Administrator",
    description: "Manage users, monitor system health, configure settings",
    icon: <Shield className="w-6 h-6" />,
  },
  {
    id: "developer",
    title: "Developer",
    description: "Build workflows, debug traces, optimize costs",
    icon: <Code className="w-6 h-6" />,
  },
  {
    id: "user",
    title: "Standard User",
    description: "Chat with AI agents, view shared workflows",
    icon: <User className="w-6 h-6" />,
  },
];

interface TourFeature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

const tourFeatures: TourFeature[] = [
  {
    icon: <Command className="w-5 h-5" />,
    title: "Command Palette",
    description: "Press Cmd+K to quickly search and navigate anywhere",
  },
  {
    icon: <MessageSquare className="w-5 h-5" />,
    title: "Chat Sessions",
    description: "Start conversations with AI agents and track history",
  },
  {
    icon: <GitBranch className="w-5 h-5" />,
    title: "Workflows",
    description: "Build and deploy custom AI agent workflows",
  },
];

const categoryIcons: Record<string, React.ReactNode> = {
  conversational: <Bot className="w-5 h-5" />,
  agent: <Server className="w-5 h-5" />,
  pipeline: <FileCode className="w-5 h-5" />,
  collaboration: <Users className="w-5 h-5" />,
  default: <Sparkles className="w-5 h-5" />,
};

const getCategoryIcon = (category: string) => {
  return categoryIcons[category] || categoryIcons.default;
};

export function OnboardingWizard({
  isOpen,
  onComplete,
  onSkip,
  templates,
}: OnboardingWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedPersona, setSelectedPersona] = useState<Persona | null>(null);
  const [selectedTemplate, setSelectedTemplate] =
    useState<WorkflowTemplate | null>(null);
  const [scratchSelected, setScratchSelected] = useState(false);

  // Focus trap for WCAG 2.1 AA compliance (Sprint 5.2)
  const dialogRef = useRef<HTMLDivElement>(null);
  useFocusTrap(dialogRef, isOpen);
  const [hasAppliedAISuggestions, setHasAppliedAISuggestions] = useState(false);

  const totalSteps = 4;

  // Phase 6.5: AI-Powered Onboarding Personalization
  const {
    detectedIntent,
    confidence,
    recommendedPath,
    skipSteps,
    personaPrediction,
    isLoading: aiLoading,
  } = useAIOnboarding({ enabled: isOpen });

  // Map AI persona predictions to our Persona type
  const mapPersonaPrediction = useCallback(
    (prediction: string | null): Persona | null => {
      if (!prediction) return null;
      if (prediction.includes("admin") || prediction === "security-admin")
        return "admin";
      if (
        prediction.includes("alice") ||
        prediction.includes("developer") ||
        prediction.includes("builder") ||
        prediction.includes("analyst") ||
        prediction.includes("devops")
      )
        return "developer";
      if (prediction === "bob" || prediction.includes("user")) return "user";
      return null;
    },
    [],
  );

  // Get recommended template from AI path
  const aiRecommendedTemplateId = useMemo(() => {
    const templateStep = recommendedPath.find(
      (step) => step.step === "template_selection" && step.template,
    );
    return templateStep?.template || null;
  }, [recommendedPath]);

  // Apply AI suggestions on first load (only once)
  useEffect(() => {
    if (!hasAppliedAISuggestions && !aiLoading && confidence >= 0.7) {
      const mappedPersona = mapPersonaPrediction(personaPrediction);
      if (mappedPersona && !selectedPersona) {
        setSelectedPersona(mappedPersona);
      }
      setHasAppliedAISuggestions(true);
    }
  }, [
    hasAppliedAISuggestions,
    aiLoading,
    confidence,
    personaPrediction,
    mapPersonaPrediction,
    selectedPersona,
  ]);

  // Check if current step should be skipped
  const shouldSkipCurrentStep = useMemo(() => {
    if (skipSteps.length === 0 || confidence < 0.8) return false;
    const stepNames = [
      "welcome",
      "persona_selection",
      "template_selection",
      "tour",
    ];
    return skipSteps.includes(stepNames[currentStep - 1] || "");
  }, [skipSteps, currentStep, confidence]);

  const handleNext = useCallback(() => {
    if (currentStep < totalSteps) {
      setCurrentStep((s) => s + 1);
    }
  }, [currentStep]);

  const handleBack = useCallback(() => {
    if (currentStep > 1) {
      setCurrentStep((s) => s - 1);
    }
  }, [currentStep]);

  const handlePersonaSelect = useCallback((persona: Persona) => {
    setSelectedPersona(persona);
  }, []);

  const handleTemplateSelect = useCallback((template: WorkflowTemplate) => {
    setSelectedTemplate(template);
    setScratchSelected(false);
  }, []);

  const handleScratchSelect = useCallback(() => {
    setSelectedTemplate(null);
    setScratchSelected(true);
  }, []);

  const handleComplete = useCallback(() => {
    if (selectedPersona) {
      onComplete({
        persona: selectedPersona,
        template: selectedTemplate,
        tourCompleted: true,
      });
    }
  }, [selectedPersona, selectedTemplate, onComplete]);

  const canProceedStep2 = selectedPersona !== null;
  const canProceedStep3 = selectedTemplate !== null || scratchSelected;

  if (!isOpen) {
    return null;
  }

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="wizard-title"
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50"
    >
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Step {currentStep} of {totalSteps}
              </div>
              <div
                role="progressbar"
                aria-valuenow={currentStep}
                aria-valuemin={1}
                aria-valuemax={totalSteps}
                className="w-32 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
              >
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${(currentStep / totalSteps) * 100}%` }}
                />
              </div>
            </div>
            <button
              onClick={onSkip}
              aria-label="Skip"
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Step 1: Welcome */}
          {currentStep === 1 && (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-100 dark:bg-blue-900/30 mb-6">
                <Sparkles className="w-8 h-8 text-blue-500" />
              </div>
              <h2
                id="wizard-title"
                className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3"
              >
                Welcome to Agent Studio
              </h2>
              <p className="text-gray-600 dark:text-gray-400 max-w-md mx-auto mb-8">
                Build AI agents that work for you. Create powerful workflows,
                connect to external services, and deploy intelligent assistants.
              </p>
              <div className="grid grid-cols-3 gap-4 max-w-md mx-auto text-center">
                <div className="p-4">
                  <Bot className="w-8 h-8 mx-auto text-blue-500 mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    AI Agents
                  </p>
                </div>
                <div className="p-4">
                  <GitBranch className="w-8 h-8 mx-auto text-green-500 mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Workflows
                  </p>
                </div>
                <div className="p-4">
                  <Server className="w-8 h-8 mx-auto text-purple-500 mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Integrations
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Persona Selection */}
          {currentStep === 2 && (
            <div>
              <h2
                id="wizard-title"
                className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2 text-center"
              >
                How will you use Agent Studio?
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
                We&apos;ll customize your experience based on your role
              </p>

              {/* AI Suggestion Banner (Phase 6.5) */}
              {detectedIntent && confidence >= 0.7 && (
                <div className="mb-4 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                  <div className="flex items-center gap-2 text-purple-700 dark:text-purple-300">
                    <Zap className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      AI detected: {detectedIntent.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-purple-500 dark:text-purple-400">
                      ({Math.round(confidence * 100)}% confidence)
                    </span>
                  </div>
                </div>
              )}

              <div className="space-y-3">
                {personaOptions.map((option) => {
                  const isAIRecommended =
                    mapPersonaPrediction(personaPrediction) === option.id &&
                    confidence >= 0.7;

                  return (
                    <button
                      key={option.id}
                      onClick={() => handlePersonaSelect(option.id)}
                      aria-pressed={selectedPersona === option.id}
                      className={`w-full flex items-center gap-4 p-4 rounded-lg border-2 transition-all ${
                        selectedPersona === option.id
                          ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                          : isAIRecommended
                            ? "border-purple-300 dark:border-purple-700 bg-purple-50/50 dark:bg-purple-900/10"
                            : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                      }`}
                    >
                      <div
                        className={`p-3 rounded-lg ${
                          selectedPersona === option.id
                            ? "bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400"
                            : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                        }`}
                      >
                        {option.icon}
                      </div>
                      <div className="text-left flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                            {option.title}
                          </h3>
                          {isAIRecommended && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/40 rounded-full">
                              <Zap className="w-3 h-3" />
                              Recommended
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {option.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Skip Step Suggestion (Phase 6.5) */}
              {shouldSkipCurrentStep && (
                <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
                      <Zap className="w-4 h-4" />
                      <span className="text-sm">
                        AI suggests skipping this step based on your experience
                      </span>
                    </div>
                    <button
                      onClick={handleNext}
                      className="text-sm font-medium text-green-600 dark:text-green-400 hover:underline"
                    >
                      Skip →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Template Selection */}
          {currentStep === 3 && (
            <div>
              <h2
                id="wizard-title"
                className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2 text-center"
              >
                Choose a template to get started
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
                Or start from scratch with a blank workflow
              </p>

              {/* AI Template Recommendation (Phase 6.5) */}
              {aiRecommendedTemplateId && confidence >= 0.7 && (
                <div className="mb-4 p-3 bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                  <div className="flex items-center gap-2 text-purple-700 dark:text-purple-300">
                    <Zap className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      AI recommends:{" "}
                      {aiRecommendedTemplateId.replace(/-/g, " ")}
                    </span>
                  </div>
                </div>
              )}

              {templates.length === 0 ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <FileCode className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No templates available</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-3 mb-4">
                  {templates.map((template) => {
                    const isAIRecommended =
                      aiRecommendedTemplateId === template.id &&
                      confidence >= 0.7;

                    return (
                      <button
                        key={template.id}
                        onClick={() => handleTemplateSelect(template)}
                        aria-pressed={selectedTemplate?.id === template.id}
                        className={`flex items-start gap-4 p-4 text-left rounded-lg border-2 transition-all ${
                          selectedTemplate?.id === template.id
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                            : isAIRecommended
                              ? "border-purple-300 dark:border-purple-700 bg-purple-50/50 dark:bg-purple-900/10"
                              : "border-gray-200 dark:border-gray-700 hover:border-gray-300"
                        }`}
                      >
                        <div
                          className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
                            selectedTemplate?.id === template.id
                              ? "bg-blue-100 text-blue-600 dark:bg-blue-900/40"
                              : "bg-gray-100 text-gray-600 dark:bg-gray-700"
                          }`}
                        >
                          {getCategoryIcon(template.category)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                              {template.name}
                            </h3>
                            {isAIRecommended && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/40 rounded-full">
                                <Zap className="w-3 h-3" />
                                AI Pick
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {template.description}
                          </p>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              <button
                onClick={handleScratchSelect}
                aria-label="Start from scratch"
                aria-pressed={scratchSelected}
                className={`w-full flex items-center justify-center gap-2 p-3 rounded-lg border-2 transition-all ${
                  scratchSelected
                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                    : "border-dashed border-gray-300 dark:border-gray-600 hover:border-gray-400"
                }`}
              >
                <FileCode className="w-5 h-5 text-gray-500" />
                <span className="text-gray-700 dark:text-gray-300">
                  Start from scratch
                </span>
              </button>
            </div>
          )}

          {/* Step 4: Quick Tour */}
          {currentStep === 4 && (
            <div>
              <h2
                id="wizard-title"
                className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2 text-center"
              >
                Quick Tour
              </h2>
              <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
                Here are some key features to help you get started
              </p>
              <div className="space-y-4">
                {tourFeatures.map((feature, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-4 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                  >
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                        {feature.title}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {feature.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div>
            {currentStep > 1 && (
              <button
                onClick={handleBack}
                aria-label="Back"
                className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            {currentStep < totalSteps ? (
              <>
                {currentStep === 1 && (
                  <button
                    onClick={handleNext}
                    aria-label="Get Started"
                    className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                  >
                    Get Started
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
                {currentStep === 2 && (
                  <button
                    onClick={handleNext}
                    disabled={!canProceedStep2}
                    aria-label="Next"
                    className={`flex items-center gap-2 px-6 py-2 rounded-lg ${
                      canProceedStep2
                        ? "bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-200 text-gray-400 cursor-not-allowed"
                    }`}
                  >
                    Next
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
                {currentStep === 3 && (
                  <button
                    onClick={handleNext}
                    disabled={!canProceedStep3}
                    aria-label="Next"
                    className={`flex items-center gap-2 px-6 py-2 rounded-lg ${
                      canProceedStep3
                        ? "bg-blue-600 text-white hover:bg-blue-700"
                        : "bg-gray-200 text-gray-400 cursor-not-allowed"
                    }`}
                  >
                    Next
                    <ArrowRight className="w-4 h-4" />
                  </button>
                )}
              </>
            ) : (
              <button
                onClick={handleComplete}
                aria-label="Complete"
                className="flex items-center gap-2 px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Complete
                <Sparkles className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default OnboardingWizard;
