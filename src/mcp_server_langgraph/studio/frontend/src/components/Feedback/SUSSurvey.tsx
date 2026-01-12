/**
 * SUSSurvey Component
 *
 * System Usability Scale (SUS) survey component.
 * Standard 10-question survey for measuring perceived usability.
 * Score range: 0-100, with 68 being average.
 */

import { useState, useMemo } from "react";

import { Button, RadioGroup, Radio } from "@/components/UI";

/**
 * Standard SUS questions
 * Odd-indexed questions (1,3,5,7,9) are positive statements
 * Even-indexed questions (2,4,6,8,10) are negative statements
 */
const SUS_QUESTIONS = [
  "I think that I would like to use this system frequently.",
  "I found the system unnecessarily complex.",
  "I thought the system was easy to use.",
  "I think that I would need support of a technical person to be able to use this system.",
  "I found the various functions in this system were well integrated.",
  "I thought there was too much inconsistency in this system.",
  "I would imagine that most people would learn to use this system very quickly.",
  "I found the system very cumbersome to use.",
  "I felt very confident using the system.",
  "I needed to learn a lot of things before I could get going with this system.",
];

export interface SUSSurveyResult {
  /** Calculated SUS score (0-100) */
  score: number;
  /** Individual question responses (1-5 for each) */
  responses: number[];
  /** Timestamp of submission */
  timestamp: number;
}

export interface SUSSurveyProps {
  /** Called when survey is submitted with calculated score */
  onSubmit: (result: SUSSurveyResult) => void;
  /** Called when user dismisses the survey */
  onDismiss: () => void;
}

/**
 * Calculate SUS score from responses
 * For odd items (positive): contribution = response - 1
 * For even items (negative): contribution = 5 - response
 * SUS Score = sum of contributions * 2.5
 */
function calculateSUSScore(responses: number[]): number {
  let total = 0;
  for (let i = 0; i < responses.length; i++) {
    const response = responses[i];
    if (response === undefined) continue;
    if (i % 2 === 0) {
      // Odd questions (0-indexed: 0, 2, 4...) - positive
      total += response - 1;
    } else {
      // Even questions (0-indexed: 1, 3, 5...) - negative
      total += 5 - response;
    }
  }
  return total * 2.5;
}

/**
 * SUSSurvey component for collecting System Usability Scale feedback.
 *
 * @example
 * ```tsx
 * <SUSSurvey
 *   onSubmit={(result) => console.log(`SUS Score: ${result.score}`)}
 *   onDismiss={() => setShowSurvey(false)}
 * />
 * ```
 */
export function SUSSurvey({ onSubmit, onDismiss }: SUSSurveyProps) {
  const [responses, setResponses] = useState<(number | null)[]>(
    new Array(10).fill(null),
  );

  const answeredCount = useMemo(
    () => responses.filter((r) => r !== null).length,
    [responses],
  );

  const allAnswered = answeredCount === 10;

  const handleRatingChange = (questionIndex: number, rating: number) => {
    setResponses((prev) => {
      const newResponses = [...prev];
      newResponses[questionIndex] = rating;
      return newResponses;
    });
  };

  const handleSubmit = () => {
    if (!allAnswered) return;

    const validResponses = responses as number[];
    const score = calculateSUSScore(validResponses);

    onSubmit({
      score,
      responses: validResponses,
      timestamp: Date.now(),
    });
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white dark:bg-neutral-800 rounded-lg shadow-lg max-h-[90vh] flex flex-col">
      {/* Header */}
      <div className="text-center mb-4 flex-shrink-0">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">
          System Usability Survey
        </h2>
        <p className="text-sm text-neutral-500 dark:text-neutral-400 mt-1">
          Help us improve by answering these 10 quick questions
        </p>
      </div>
      {/* Progress */}
      <div className="mb-4 flex-shrink-0">
        <div className="flex justify-between text-sm text-neutral-600 dark:text-neutral-300 mb-1">
          <span>{answeredCount} of 10 questions answered</span>
        </div>
        <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
          <div
            className="bg-primary-600 h-2 rounded-full transition-all"
            style={{ width: `${(answeredCount / 10) * 100}%` }}
          />
        </div>
      </div>
      {/* Scale Labels */}
      <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mb-2 px-8 flex-shrink-0">
        <span>Strongly Disagree</span>
        <span>Strongly Agree</span>
      </div>
      {/* Questions - scrollable area */}
      <div className="space-y-4 overflow-y-auto flex-1 min-h-0 pr-2">
        {SUS_QUESTIONS.map((question, index) => (
          <div
            key={index}
            className="border-b border-neutral-100 dark:border-neutral-700 pb-4"
          >
            <p
              id={`question-${index}`}
              className="text-sm text-neutral-700 dark:text-neutral-200 mb-3"
            >
              {index + 1}. {question}
            </p>
            <RadioGroup
              name={`question-${index}`}
              value={responses[index]?.toString() ?? ""}
              onChange={(val) => handleRatingChange(index, parseInt(val, 10))}
              variant="rating"
              aria-label={`Question ${index + 1}`}
            >
              {[1, 2, 3, 4, 5].map((rating) => (
                <Radio
                  key={rating}
                  value={rating.toString()}
                  label={rating.toString()}
                />
              ))}
            </RadioGroup>
          </div>
        ))}
      </div>
      {/* Actions */}
      <div className="flex justify-between mt-4 pt-4 border-t border-neutral-200 dark:border-neutral-700 flex-shrink-0">
        <Button
          className="px-4 py-2 text-sm text-neutral-600 dark:text-neutral-300 hover:text-neutral-800 dark:hover:text-neutral-100"
          onClick={onDismiss}
        >
          Maybe Later
        </Button>
        <Button
          size="lg"
          className="px-6 py-2 text-sm rounded-md"
          onClick={handleSubmit}
          disabled={!allAnswered}
        >
          Submit
        </Button>
      </div>
    </div>
  );
}

export default SUSSurvey;
