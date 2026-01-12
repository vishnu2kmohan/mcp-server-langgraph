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

import { Button } from "@/components/UI";

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
      <div className="bg-white dark:bg-neutral-800 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-sm text-neutral-500 dark:text-neutral-400">
                Step {currentStep} of {totalSteps}
              </div>
              <div
                role="progressbar"
                aria-valuenow={currentStep}
                aria-valuemin={1}
                aria-valuemax={totalSteps}
                className="w-32 h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden"
              >
                <div
                  className="h-full bg-primary-500 transition-all duration-300"
                  style={{ width: `${(currentStep / totalSteps) * 100}%` }}
                />
              </div>
            </div>
            <Button
              variant="secondary"
              className="p-2 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300 rounded-lg hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700"
              onClick={onSkip}
              aria-label="Skip"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {/* Step 1: Welcome */}
          {currentStep === 1 && (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30 mb-6">
                <Sparkles className="w-8 h-8 text-primary-500" />
              </div>
              <h2
                id="wizard-title"
                className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-3"
              >
                Welcome to Agent Studio
              </h2>
              <p className="text-neutral-600 dark:text-neutral-400 max-w-md mx-auto mb-8">
                Build AI agents that work for you. Create powerful workflows,
                connect to external services, and deploy intelligent assistants.
              </p>
              <div className="grid grid-cols-3 gap-4 max-w-md mx-auto text-center">
                <div className="p-4">
                  <Bot className="w-8 h-8 mx-auto text-primary-500 mb-2" />
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    AI Agents
                  </p>
                </div>
                <div className="p-4">
                  <GitBranch className="w-8 h-8 mx-auto text-success-500 mb-2" />
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    Workflows
                  </p>
                </div>
                <div className="p-4">
                  <Server className="w-8 h-8 mx-auto text-insight-500 mb-2" />
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
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
                className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2 text-center"
              >
                How will you use Agent Studio?
              </h2>
              <p className="text-neutral-600 dark:text-neutral-400 text-center mb-6">
                We&apos;ll customize your experience based on your role
              </p>

              {/* AI Suggestion Banner (Phase 6.5) */}
              {detectedIntent && confidence >= 0.7 && (
                <div className="mb-4 p-3 bg-insight-50 dark:bg-insight-900/20 border border-insight-200 dark:border-insight-800 rounded-lg">
                  <div className="flex items-center gap-2 text-insight-700 dark:text-insight-300">
                    <Zap className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      AI detected: {detectedIntent.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-insight-500 dark:text-insight-400">
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
                    <Button
                      className="w-full flex p-4 rounded-lg border-2"
                      key={option.id}
                      onClick={() => handlePersonaSelect(option.id)}
                      aria-pressed={selectedPersona === option.id}
                    >
                      <div
                        className={`p-3 rounded-lg ${
                          selectedPersona === option.id
                            ? "bg-primary-100 text-primary-600 dark:bg-primary-900/40 dark:text-primary-400"
                            : "bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
                        }`}
                      >
                        {option.icon}
                      </div>
                      <div className="text-left flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
                            {option.title}
                          </h3>
                          {isAIRecommended && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-insight-700 dark:text-insight-300 bg-insight-100 dark:bg-insight-900/40 rounded-full">
                              <Zap className="w-3 h-3" />
                              Recommended
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-neutral-600 dark:text-neutral-400">
                          {option.description}
                        </p>
                      </div>
                    </Button>
                  );
                })}
              </div>

              {/* Skip Step Suggestion (Phase 6.5) */}
              {shouldSkipCurrentStep && (
                <div className="mt-4 p-3 bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-success-700 dark:text-success-300">
                      <Zap className="w-4 h-4" />
                      <span className="text-sm">
                        AI suggests skipping this step based on your experience
                      </span>
                    </div>
                    <Button
                      className="text-sm text-success-600 dark:text-success-400 hover:underline"
                      onClick={handleNext}
                    >
                      Skip →
                    </Button>
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
                className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2 text-center"
              >
                Choose a template to get started
              </h2>
              <p className="text-neutral-600 dark:text-neutral-400 text-center mb-6">
                Or start from scratch with a blank workflow
              </p>

              {/* AI Template Recommendation (Phase 6.5) */}
              {aiRecommendedTemplateId && confidence >= 0.7 && (
                <div className="mb-4 p-3 bg-insight-50 dark:bg-insight-900/20 border border-insight-200 dark:border-insight-800 rounded-lg">
                  <div className="flex items-center gap-2 text-insight-700 dark:text-insight-300">
                    <Zap className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      AI recommends:{" "}
                      {aiRecommendedTemplateId.replace(/-/g, " ")}
                    </span>
                  </div>
                </div>
              )}

              {templates.length === 0 ? (
                <div className="text-center py-8 text-neutral-500 dark:text-neutral-400">
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
                      <Button
                        className="flex items-start p-4 text-left rounded-lg border-2"
                        key={template.id}
                        onClick={() => handleTemplateSelect(template)}
                        aria-pressed={selectedTemplate?.id === template.id}
                      >
                        <div
                          className={`flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center ${
                            selectedTemplate?.id === template.id
                              ? "bg-primary-100 text-primary-600 dark:bg-primary-900/40"
                              : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 dark:bg-neutral-700"
                          }`}
                        >
                          {getCategoryIcon(template.category)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
                              {template.name}
                            </h3>
                            {isAIRecommended && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-insight-700 dark:text-insight-300 bg-insight-100 dark:bg-insight-900/40 rounded-full">
                                <Zap className="w-3 h-3" />
                                AI Pick
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
                            {template.description}
                          </p>
                        </div>
                      </Button>
                    );
                  })}
                </div>
              )}

              <Button
                className="w-full flex p-3 rounded-lg border-2"
                onClick={handleScratchSelect}
                aria-label="Start from scratch"
                aria-pressed={scratchSelected}
              >
                <FileCode className="w-5 h-5 text-neutral-500 dark:text-neutral-400" />
                <span className="text-neutral-700 dark:text-neutral-300">
                  Start from scratch
                </span>
              </Button>
            </div>
          )}

          {/* Step 4: Quick Tour */}
          {currentStep === 4 && (
            <div>
              <h2
                id="wizard-title"
                className="text-xl font-bold text-neutral-900 dark:text-neutral-100 mb-2 text-center"
              >
                Quick Tour
              </h2>
              <p className="text-neutral-600 dark:text-neutral-400 text-center mb-6">
                Here are some key features to help you get started
              </p>
              <div className="space-y-4">
                {tourFeatures.map((feature, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-4 p-4 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg"
                  >
                    <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg text-primary-600 dark:text-primary-400">
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-neutral-900 dark:text-neutral-100">
                        {feature.title}
                      </h3>
                      <p className="text-sm text-neutral-600 dark:text-neutral-400">
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
        <div className="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
          <div>
            {currentStep > 1 && (
              <Button
                className="flex px-4 py-2 text-neutral-600 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200"
                onClick={handleBack}
                aria-label="Back"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </Button>
            )}
          </div>
          <div className="flex items-center gap-3">
            {currentStep < totalSteps ? (
              <>
                {currentStep === 1 && (
                  <Button
                    variant="primary"
                    size="lg"
                    className="flex px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    onClick={handleNext}
                    aria-label="Get Started"
                  >
                    Get Started
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                )}
                {currentStep === 2 && (
                  <Button
                    size="lg"
                    className="flex px-6 py-2 rounded-lg"
                    onClick={handleNext}
                    disabled={!canProceedStep2}
                    aria-label="Next"
                  >
                    Next
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                )}
                {currentStep === 3 && (
                  <Button
                    size="lg"
                    className="flex px-6 py-2 rounded-lg"
                    onClick={handleNext}
                    disabled={!canProceedStep3}
                    aria-label="Next"
                  >
                    Next
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                )}
              </>
            ) : (
              <Button
                variant="success"
                size="lg"
                className="flex px-6 py-2 bg-success-600 text-white rounded-lg hover:bg-success-700"
                onClick={handleComplete}
                aria-label="Complete"
              >
                Complete
                <Sparkles className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default OnboardingWizard;
