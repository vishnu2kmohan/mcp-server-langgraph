/**
 * AIQualityMetricsCard Component Stories
 *
 * Storybook stories for the AI quality metrics dashboard card.
 * Uses a presenter pattern to avoid Vitest mock dependencies.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Flag,
  TrendingUp,
  Grid3X3,
  PieChart as PieChartIcon,
} from "lucide-react";
import { PieChart, Pie, Cell, Legend, ResponsiveContainer } from "recharts";
import { Skeleton } from "../UI/Skeleton";
import { Button } from "../UI/Button";

// =============================================================================
// Presenter Component (for Storybook - no API dependencies)
// =============================================================================

interface AIQualityMetricsCardPresenterProps {
  timeframe?: string;
  compact?: boolean;
  visualization?: "grid" | "pie";
  showToggle?: boolean;
  // Data props (instead of hook)
  isLoading?: boolean;
  isError?: boolean;
  hallucinationReports?: number;
  positiveRate?: number;
  categories?: {
    factualError: number;
    outdatedInfo: number;
    madeUpSource: number;
    other: number;
  };
}

const CATEGORY_CONFIG = {
  factualError: {
    label: "Factual Error",
    color: "text-error-600 dark:text-error-400",
    bgColor: "bg-error-100 dark:bg-error-900",
    pieColor: "#dc2626",
  },
  outdatedInfo: {
    label: "Outdated Info",
    color: "text-warning-600 dark:text-warning-400",
    bgColor: "bg-warning-100 dark:bg-warning-900",
    pieColor: "#d97706",
  },
  madeUpSource: {
    label: "Made Up Source",
    color: "text-error-600 dark:text-error-400",
    bgColor: "bg-error-100 dark:bg-error-900",
    pieColor: "#be123c",
  },
  other: {
    label: "Other",
    color: "text-neutral-600 dark:text-neutral-400",
    bgColor: "bg-neutral-100 dark:bg-neutral-700",
    pieColor: "#737373",
  },
} as const;

function LoadingSkeleton() {
  return (
    <div data-testid="ai-quality-loading" className="space-y-4">
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-10 w-24" />
      <div className="grid grid-cols-2 gap-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}

/**
 * Presenter component for Storybook - accepts data as props instead of using hooks.
 */
function AIQualityMetricsCardPresenter({
  timeframe = "7d",
  compact = false,
  visualization = "grid",
  showToggle = false,
  isLoading = false,
  isError = false,
  hallucinationReports = 0,
  positiveRate = 0,
  categories,
}: AIQualityMetricsCardPresenterProps) {
  const [currentVisualization, setCurrentVisualization] = useState<
    "grid" | "pie"
  >(visualization);
  const paddingClass = compact ? "p-3" : "p-6";
  const hasNoReports = hallucinationReports === 0;

  const handleToggleVisualization = () => {
    setCurrentVisualization((prev) => (prev === "grid" ? "pie" : "grid"));
  };

  if (isLoading) {
    return (
      <section
        data-testid="ai-quality-card"
        className={`bg-white dark:bg-neutral-800 rounded-lg shadow ${paddingClass}`}
        role="region"
        aria-label="AI quality metrics"
      >
        <LoadingSkeleton />
      </section>
    );
  }

  if (isError) {
    return (
      <section
        data-testid="ai-quality-card"
        className={`bg-white dark:bg-neutral-800 rounded-lg shadow ${paddingClass}`}
        role="region"
        aria-label="AI quality metrics"
      >
        <div className="flex items-center gap-2 text-error-600 dark:text-error-400">
          <AlertTriangle className="w-5 h-5" />
          <span>Failed to load AI quality metrics</span>
        </div>
      </section>
    );
  }

  return (
    <section
      data-testid="ai-quality-card"
      className={`bg-white dark:bg-neutral-800 rounded-lg shadow ${paddingClass}`}
      role="region"
      aria-label="AI quality metrics"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-neutral-900 dark:text-white flex items-center gap-2">
          <Flag className="w-5 h-5 text-primary-500" aria-hidden="true" />
          AI Quality
        </h2>
        <div className="flex items-center gap-2">
          {showToggle && !compact && !hasNoReports && categories && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleToggleVisualization}
              className="p-1.5 text-neutral-500 dark:text-neutral-400"
              aria-label={
                currentVisualization === "grid"
                  ? "Switch to pie chart view"
                  : "Switch to grid view"
              }
            >
              {currentVisualization === "grid" ? (
                <PieChartIcon className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Grid3X3 className="w-4 h-4" aria-hidden="true" />
              )}
            </Button>
          )}
          <span className="text-sm text-neutral-500 dark:text-neutral-400">
            {timeframe}
          </span>
        </div>
      </div>

      {/* Main metrics row */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-3">
          <div className="text-sm text-neutral-600 dark:text-neutral-300 mb-1">
            Hallucination Reports
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-neutral-900 dark:text-white">
              {hallucinationReports}
            </span>
            {hasNoReports && (
              <CheckCircle
                className="w-5 h-5 text-success-500"
                aria-hidden="true"
              />
            )}
          </div>
          {hasNoReports && (
            <div className="text-xs text-success-600 dark:text-success-400 mt-1">
              No reports in this period
            </div>
          )}
        </div>

        <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-3">
          <div className="text-sm text-neutral-600 dark:text-neutral-300 mb-1">
            Response Approval Rate
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold ${
                positiveRate >= 0.8
                  ? "text-success-600"
                  : positiveRate >= 0.6
                    ? "text-warning-600"
                    : "text-error-600"
              }`}
            >
              {Math.round(positiveRate * 100)}%
            </span>
            {positiveRate >= 0.8 && (
              <TrendingUp
                className="w-4 h-4 text-success-500"
                aria-hidden="true"
              />
            )}
          </div>
        </div>
      </div>

      {/* Category breakdown */}
      {!compact && categories && !hasNoReports && (
        <div className="border-t border-neutral-200 dark:border-neutral-600 pt-4">
          <h3 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
            Reports by Category
          </h3>

          {currentVisualization === "pie" && (
            <div
              data-testid="ai-quality-pie-chart"
              aria-label="Hallucination reports category breakdown"
              className="h-48"
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={Object.entries(CATEGORY_CONFIG).map(
                      ([key, config]) => ({
                        name: config.label,
                        value: categories[key as keyof typeof categories] ?? 0,
                        color: config.pieColor,
                      }),
                    )}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                  >
                    {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                      <Cell key={key} fill={config.pieColor} />
                    ))}
                  </Pie>
                  <Legend
                    layout="vertical"
                    align="right"
                    verticalAlign="middle"
                    formatter={(value: string) => (
                      <span className="text-sm text-neutral-700 dark:text-neutral-300">
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          {currentVisualization === "grid" && (
            <div className="grid grid-cols-2 gap-2">
              {(
                Object.entries(CATEGORY_CONFIG) as [
                  keyof typeof CATEGORY_CONFIG,
                  (typeof CATEGORY_CONFIG)[keyof typeof CATEGORY_CONFIG],
                ][]
              ).map(([key, config]) => {
                const count = categories[key as keyof typeof categories] ?? 0;
                return (
                  <div
                    key={key}
                    className={`flex items-center justify-between rounded-md px-3 py-2 ${config.bgColor}`}
                  >
                    <span className={`text-sm ${config.color}`}>
                      {config.label}
                    </span>
                    <span className={`text-sm font-semibold ${config.color}`}>
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// =============================================================================
// Storybook Meta & Stories
// =============================================================================

const meta: Meta<typeof AIQualityMetricsCardPresenter> = {
  title: "Admin/AIQualityMetricsCard",
  component: AIQualityMetricsCardPresenter,
  tags: ["autodocs"],
  parameters: {
    layout: "padded",
    docs: {
      description: {
        component:
          "Displays AI quality metrics including hallucination reports and category breakdowns for the admin dashboard.",
      },
    },
  },
  argTypes: {
    timeframe: {
      control: "select",
      options: ["7d", "14d", "30d", "90d"],
      description: "Time period for metrics",
    },
    compact: {
      control: "boolean",
      description: "Compact display mode (hides category breakdown)",
    },
    visualization: {
      control: "select",
      options: ["grid", "pie"],
      description: "Category breakdown visualization mode",
    },
    showToggle: {
      control: "boolean",
      description: "Show toggle button to switch between grid and pie views",
    },
    isLoading: {
      control: "boolean",
      description: "Show loading state",
    },
    isError: {
      control: "boolean",
      description: "Show error state",
    },
    hallucinationReports: {
      control: "number",
      description: "Number of hallucination reports",
    },
    positiveRate: {
      control: { type: "range", min: 0, max: 1, step: 0.05 },
      description: "Positive rate (0-1)",
    },
  },
};

export default meta;
type Story = StoryObj<typeof AIQualityMetricsCardPresenter>;

// Default mock data
const defaultCategories = {
  factualError: 5,
  outdatedInfo: 3,
  madeUpSource: 2,
  other: 2,
};

export const Default: Story = {
  args: {
    timeframe: "7d",
    hallucinationReports: 12,
    positiveRate: 0.8,
    categories: defaultCategories,
  },
};

export const WithPieChart: Story = {
  args: {
    timeframe: "7d",
    visualization: "pie",
    hallucinationReports: 12,
    positiveRate: 0.8,
    categories: defaultCategories,
  },
};

export const WithToggle: Story = {
  args: {
    timeframe: "7d",
    showToggle: true,
    hallucinationReports: 12,
    positiveRate: 0.8,
    categories: defaultCategories,
  },
};

export const Compact: Story = {
  args: {
    timeframe: "7d",
    compact: true,
    hallucinationReports: 12,
    positiveRate: 0.8,
    categories: defaultCategories,
  },
};

export const Loading: Story = {
  args: {
    isLoading: true,
  },
};

export const Error: Story = {
  args: {
    isError: true,
  },
};

export const NoReports: Story = {
  args: {
    timeframe: "7d",
    hallucinationReports: 0,
    positiveRate: 0.95,
  },
};

export const LowApprovalRate: Story = {
  args: {
    timeframe: "7d",
    hallucinationReports: 25,
    positiveRate: 0.45,
    categories: {
      factualError: 12,
      outdatedInfo: 5,
      madeUpSource: 5,
      other: 3,
    },
  },
};

export const HighVolume: Story = {
  args: {
    timeframe: "30d",
    hallucinationReports: 89,
    positiveRate: 0.8,
    categories: {
      factualError: 35,
      outdatedInfo: 22,
      madeUpSource: 18,
      other: 14,
    },
  },
};

export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="text-lg font-medium mb-2">Grid View (Default)</h3>
        <AIQualityMetricsCardPresenter
          visualization="grid"
          hallucinationReports={12}
          positiveRate={0.8}
          categories={defaultCategories}
        />
      </div>
      <div>
        <h3 className="text-lg font-medium mb-2">Pie Chart View</h3>
        <AIQualityMetricsCardPresenter
          visualization="pie"
          hallucinationReports={12}
          positiveRate={0.8}
          categories={defaultCategories}
        />
      </div>
      <div>
        <h3 className="text-lg font-medium mb-2">With Toggle</h3>
        <AIQualityMetricsCardPresenter
          showToggle
          hallucinationReports={12}
          positiveRate={0.8}
          categories={defaultCategories}
        />
      </div>
      <div>
        <h3 className="text-lg font-medium mb-2">Compact Mode</h3>
        <AIQualityMetricsCardPresenter
          compact
          hallucinationReports={12}
          positiveRate={0.8}
          categories={defaultCategories}
        />
      </div>
    </div>
  ),
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-900 p-6 rounded-lg">
      <div className="flex flex-col gap-4">
        <AIQualityMetricsCardPresenter
          visualization="grid"
          hallucinationReports={12}
          positiveRate={0.8}
          categories={defaultCategories}
        />
        <AIQualityMetricsCardPresenter
          visualization="pie"
          hallucinationReports={12}
          positiveRate={0.8}
          categories={defaultCategories}
        />
      </div>
    </div>
  ),
};
