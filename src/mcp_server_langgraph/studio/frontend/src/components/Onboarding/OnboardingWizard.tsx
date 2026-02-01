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

import { Button, SelectionCard } from "@/components/UI";

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
      className="fixed inset-0 z-60 flex items-center justify-center bg-neutral-a7"
    >
      <div className="bg-neutral-2 border border-neutral-6 rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col backdrop-blur-sm">
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="text-sm text-neutral-10">
                Step {currentStep} of {totalSteps}
              </div>
              <div
                role="progressbar"
                aria-valuenow={currentStep}
                aria-valuemin={1}
                aria-valuemax={totalSteps}
                className="w-32 h-1.5 bg-neutral-4 rounded-full overflow-hidden"
              >
                <div
                  className="h-full bg-primary-9 transition-all duration-300"
                  style={
                    {
                      "--progress": `${(currentStep / totalSteps) * 100}%`,
                    } as React.CSSProperties
                  }
                />
              </div>
            </div>
            <Button
              size="icon"
              variant="secondary"
              className="p-2 text-neutral-9 hover:text-neutral-11 rounded-lg hover:bg-neutral-3"
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
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-3 mb-6">
                <Sparkles className="w-8 h-8 text-primary-9" />
              </div>
              <h2
                id="wizard-title"
                className="text-2xl font-bold text-neutral-12 mb-3"
              >
                Welcome to Agent Studio
              </h2>
              <p className="text-neutral-11 max-w-md mx-auto mb-8">
                Build AI agents that work for you. Create powerful workflows,
                connect to external services, and deploy intelligent assistants.
              </p>
              <div className="grid grid-cols-3 gap-4 max-w-md mx-auto text-center">
                <div className="p-4">
                  <Bot className="w-8 h-8 mx-auto text-primary-9 mb-2" />
                  <p className="text-sm text-neutral-11">AI Agents</p>
                </div>
                <div className="p-4">
                  <GitBranch className="w-8 h-8 mx-auto text-success-9 mb-2" />
                  <p className="text-sm text-neutral-11">Workflows</p>
                </div>
                <div className="p-4">
                  <Server className="w-8 h-8 mx-auto text-insight-9 mb-2" />
                  <p className="text-sm text-neutral-11">Integrations</p>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Persona Selection */}
          {currentStep === 2 && (
            <div>
              <h2
                id="wizard-title"
                className="text-xl font-bold text-neutral-12 mb-2 text-center"
              >
                How will you use Agent Studio?
              </h2>
              <p className="text-neutral-11 text-center mb-6">
                We&apos;ll customize your experience based on your role
              </p>

              {/* AI Suggestion Banner (Phase 6.5) */}
              {detectedIntent && confidence >= 0.7 && (
                <div className="mb-4 p-3 bg-insight-3 border border-insight-6 rounded-lg">
                  <div className="flex items-center gap-2 text-insight-11">
                    <Zap className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      AI detected: {detectedIntent.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs text-insight-9">
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
                    <SelectionCard
                      key={option.id}
                      title={option.title}
                      description={option.description}
                      icon={option.icon}
                      selected={selectedPersona === option.id}
                      onClick={() => handlePersonaSelect(option.id)}
                      badge={isAIRecommended ? "Recommended" : undefined}
                    />
                  );
                })}
              </div>

              {/* Skip Step Suggestion (Phase 6.5) */}
              {shouldSkipCurrentStep && (
                <div className="mt-4 p-3 bg-success-3 border border-success-6 rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-success-11">
                      <Zap className="w-4 h-4" />
                      <span className="text-sm">
                        AI suggests skipping this step based on your experience
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      className="text-sm text-success-11 hover:underline"
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
                className="text-xl font-bold text-neutral-12 mb-2 text-center"
              >
                Choose a template to get started
              </h2>
              <p className="text-neutral-11 text-center mb-6">
                Or start from scratch with a blank workflow
              </p>

              {/* AI Template Recommendation (Phase 6.5) */}
              {aiRecommendedTemplateId && confidence >= 0.7 && (
                <div className="mb-4 p-3 bg-insight-3 border border-insight-6 rounded-lg">
                  <div className="flex items-center gap-2 text-insight-11">
                    <Zap className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      AI recommends:{" "}
                      {aiRecommendedTemplateId.replace(/-/g, " ")}
                    </span>
                  </div>
                </div>
              )}

              {templates.length === 0 ? (
                <div className="text-center py-8 text-neutral-9">
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
                      <SelectionCard
                        key={template.id}
                        title={template.name}
                        description={template.description}
                        icon={getCategoryIcon(template.category)}
                        selected={selectedTemplate?.id === template.id}
                        onClick={() => handleTemplateSelect(template)}
                        badge={isAIRecommended ? "AI Pick" : undefined}
                      />
                    );
                  })}
                </div>
              )}

              <SelectionCard
                title="Start from scratch"
                description="Begin with a blank workflow"
                icon={<FileCode className="w-5 h-5" />}
                selected={scratchSelected}
                onClick={handleScratchSelect}
                ariaLabel="Start from scratch"
              />
            </div>
          )}

          {/* Step 4: Quick Tour */}
          {currentStep === 4 && (
            <div>
              <h2
                id="wizard-title"
                className="text-xl font-bold text-neutral-12 mb-2 text-center"
              >
                Quick Tour
              </h2>
              <p className="text-neutral-11 text-center mb-6">
                Here are some key features to help you get started
              </p>
              <div className="space-y-4">
                {tourFeatures.map((feature, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-4 p-4 bg-neutral-3 rounded-lg"
                  >
                    <div className="p-2 bg-primary-3 rounded-lg text-primary-11">
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="font-semibold text-neutral-12">
                        {feature.title}
                      </h3>
                      <p className="text-sm text-neutral-11">
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
        <div className="px-6 py-4 border-t border-neutral-6 flex items-center justify-between">
          <div>
            {currentStep > 1 && (
              <Button
                variant="secondary"
                className="flex gap-2 px-4 py-2 text-neutral-11 hover:text-neutral-12 hover:bg-neutral-3 rounded-lg"
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
                    className="flex gap-2 px-6 py-2 bg-primary-9 text-primary-contrast rounded-lg hover:bg-primary-10"
                    onClick={handleNext}
                    aria-label="Get Started"
                  >
                    Get Started
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                )}
                {currentStep === 2 && (
                  <Button
                    variant="primary"
                    size="lg"
                    className="flex gap-2 px-6 py-2 bg-primary-9 text-primary-contrast rounded-lg hover:bg-primary-10 disabled:opacity-50 disabled:cursor-not-allowed"
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
                    variant="primary"
                    size="lg"
                    className="flex gap-2 px-6 py-2 bg-primary-9 text-primary-contrast rounded-lg hover:bg-primary-10 disabled:opacity-50 disabled:cursor-not-allowed"
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
                className="flex gap-2 px-6 py-2 bg-success-9 text-success-contrast rounded-lg hover:bg-success-10"
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
