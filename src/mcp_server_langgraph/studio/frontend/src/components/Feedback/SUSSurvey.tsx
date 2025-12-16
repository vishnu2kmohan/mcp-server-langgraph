/**
 * SUSSurvey Component
 *
 * System Usability Scale (SUS) survey component.
 * Standard 10-question survey for measuring perceived usability.
 * Score range: 0-100, with 68 being average.
 */

import { useState, useMemo } from "react";

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
    if (i % 2 === 0) {
      // Odd questions (0-indexed: 0, 2, 4...) - positive
      total += responses[i] - 1;
    } else {
      // Even questions (0-indexed: 1, 3, 5...) - negative
      total += 5 - responses[i];
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
    <div className="max-w-2xl mx-auto p-6 bg-white dark:bg-gray-800 rounded-lg shadow-lg max-h-[90vh] flex flex-col">
      {/* Header */}
      <div className="text-center mb-4 flex-shrink-0">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          System Usability Survey
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Help us improve by answering these 10 quick questions
        </p>
      </div>

      {/* Progress */}
      <div className="mb-4 flex-shrink-0">
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-300 mb-1">
          <span>{answeredCount} of 10 questions answered</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all"
            style={{ width: `${(answeredCount / 10) * 100}%` }}
          />
        </div>
      </div>

      {/* Scale Labels */}
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-2 px-8 flex-shrink-0">
        <span>Strongly Disagree</span>
        <span>Strongly Agree</span>
      </div>

      {/* Questions - scrollable area */}
      <div className="space-y-4 overflow-y-auto flex-1 min-h-0 pr-2">
        {SUS_QUESTIONS.map((question, index) => (
          <div
            key={index}
            className="border-b border-gray-100 dark:border-gray-700 pb-4"
          >
            <p
              id={`question-${index}`}
              className="text-sm text-gray-700 dark:text-gray-200 mb-3"
            >
              {index + 1}. {question}
            </p>
            <div
              role="radiogroup"
              aria-labelledby={`question-${index}`}
              className="flex justify-center gap-4"
            >
              {[1, 2, 3, 4, 5].map((rating) => (
                <label
                  key={rating}
                  className="flex flex-col items-center cursor-pointer"
                >
                  <input
                    type="radio"
                    name={`question-${index}`}
                    value={rating}
                    checked={responses[index] === rating}
                    onChange={() => handleRatingChange(index, rating)}
                    className="w-5 h-5 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {rating}
                  </span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex justify-between mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
        <button
          onClick={onDismiss}
          className="px-4 py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-800 dark:hover:text-gray-100"
        >
          Maybe Later
        </button>
        <button
          onClick={handleSubmit}
          disabled={!allAnswered}
          className={`px-6 py-2 text-sm rounded-md transition-colors ${
            allAnswered
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-200 text-gray-400 cursor-not-allowed"
          }`}
        >
          Submit
        </button>
      </div>
    </div>
  );
}

export default SUSSurvey;
