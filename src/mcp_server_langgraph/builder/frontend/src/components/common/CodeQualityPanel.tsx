/**
 * CodeQualityPanel Component
 *
 * Displays code quality metrics for generated workflow code.
 * Implements UX Honeycomb "Credible" and "Useful" facets.
 */

import React from 'react';

// ==============================================================================
// Types
// ==============================================================================

export type ComplexityLevel = 'low' | 'medium' | 'high';

export interface CodeQualityPanelProps {
  linesOfCode: number;
  nodeCount: number;
  edgeCount: number;
  complexity: ComplexityLevel;
  lintWarnings?: number;
}

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Subcomponents
// ==============================================================================

function MetricCard({
  value,
  label,
  icon,
}: {
  value: number;
  label: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2">
      <div className="text-gray-400 dark:text-gray-500">{icon}</div>
      <div>
        <div className="text-lg font-semibold text-gray-900 dark:text-white">{value}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
      </div>
    </div>
  );
}

// ==============================================================================
// Icons
// ==============================================================================

function CodeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" width="20" height="20">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
    </svg>
  );
}

function NodeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" width="20" height="20">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
    </svg>
  );
}

function EdgeIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" width="20" height="20">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" width="20" height="20">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  );
}

// ==============================================================================
// Component
// ==============================================================================

export function CodeQualityPanel({
  linesOfCode,
  nodeCount,
  edgeCount,
  complexity,
  lintWarnings = 0,
}: CodeQualityPanelProps): React.ReactElement {
  const complexityConfig = {
    low: {
      bgClass: 'bg-green-100 dark:bg-green-900/30',
      textClass: 'text-green-700 dark:text-green-300',
      label: 'Low',
    },
    medium: {
      bgClass: 'bg-yellow-100 dark:bg-yellow-900/30',
      textClass: 'text-yellow-700 dark:text-yellow-300',
      label: 'Medium',
    },
    high: {
      bgClass: 'bg-red-100 dark:bg-red-900/30',
      textClass: 'text-red-700 dark:text-red-300',
      label: 'High',
    },
  };

  const config = complexityConfig[complexity];
  const hasCode = linesOfCode > 0 || nodeCount > 0;

  return (
    <div
      role="region"
      aria-label="Code Quality Metrics"
      className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4"
      data-testid="code-quality-panel"
    >
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">
        Code Quality
      </h3>

      {!hasCode ? (
        <div className="text-center py-4 text-gray-500 dark:text-gray-400 text-sm">
          No code generated yet
        </div>
      ) : (
        <>
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <MetricCard value={linesOfCode} label="Lines" icon={<CodeIcon />} />
            <MetricCard value={nodeCount} label="Nodes" icon={<NodeIcon />} />
            <MetricCard value={edgeCount} label="Edges" icon={<EdgeIcon />} />
            <MetricCard value={lintWarnings} label="Warnings" icon={<WarningIcon />} />
          </div>

          {/* Complexity Badge */}
          <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500 dark:text-gray-400">Complexity</span>
              <span
                data-testid="complexity-badge"
                className={clsx(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  config.bgClass,
                  config.textClass
                )}
              >
                {config.label}
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default CodeQualityPanel;
