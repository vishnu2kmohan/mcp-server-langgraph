/**
 * A11yDevTools - Runtime Accessibility Checker
 *
 * Development-only component that runs axe-core accessibility checks
 * and logs violations to the console. Only active in development mode.
 *
 * @module @mcp-server-langgraph/shared-frontend/components
 *
 * @example
 * ```tsx
 * // Add to your app root in development
 * function App() {
 *   return (
 *     <>
 *       <A11yDevTools />
 *       <YourApp />
 *     </>
 *   );
 * }
 * ```
 */

import { useEffect, useRef } from 'react';

/**
 * Configuration options for A11yDevTools
 */
export interface A11yDevToolsProps {
  /**
   * Debounce delay in ms before running checks after DOM changes
   * @default 1000
   */
  debounceMs?: number;

  /**
   * WCAG tags to check against
   * @default ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
   */
  tags?: string[];

  /**
   * Whether to run checks automatically on mount
   * @default true
   */
  autoRun?: boolean;

  /**
   * Custom context element to check (defaults to document)
   */
  context?: Element | null;
}

/**
 * A11yDevTools Component
 *
 * Runs axe-core accessibility checks in development mode and logs
 * violations to the browser console with helpful formatting.
 *
 * Features:
 * - Only runs in development (NODE_ENV !== 'production')
 * - Debounced to avoid excessive checks during rapid DOM updates
 * - Configurable WCAG levels (defaults to WCAG 2.2 AA)
 * - Color-coded console output for easy identification
 *
 * @example
 * ```tsx
 * // Basic usage - add to app root
 * <A11yDevTools />
 *
 * // With custom configuration
 * <A11yDevTools
 *   debounceMs={500}
 *   tags={['wcag2aa', 'wcag22aa']}
 * />
 * ```
 */
export function A11yDevTools({
  debounceMs = 1000,
  tags = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'],
  autoRun = true,
  context,
}: A11yDevToolsProps = {}) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isInitializedRef = useRef(false);

  useEffect(() => {
    // Only run in development
    if (process.env.NODE_ENV === 'production') {
      return;
    }

    // Prevent duplicate initialization in React StrictMode
    if (isInitializedRef.current) {
      return;
    }
    isInitializedRef.current = true;

    const runAxeCheck = async () => {
      try {
        // Dynamic import to avoid bundling in production
        const axeCore = await import('axe-core');
        const axe = axeCore.default;

        const results = await axe.run(context || document, {
          runOnly: {
            type: 'tag',
            values: tags,
          },
        });

        if (results.violations.length > 0) {
          console.group(
            '%c♿ Accessibility Issues Found',
            'color: #ff6b6b; font-weight: bold; font-size: 14px;'
          );

          results.violations.forEach((violation) => {
            console.groupCollapsed(
              `%c${violation.impact?.toUpperCase()}: ${violation.help}`,
              `color: ${getImpactColor(violation.impact)}; font-weight: bold;`
            );

            console.log('%cDescription:', 'font-weight: bold;', violation.description);
            console.log('%cWCAG:', 'font-weight: bold;', violation.tags.join(', '));
            console.log('%cHelp URL:', 'font-weight: bold;', violation.helpUrl);

            violation.nodes.forEach((node, index) => {
              console.groupCollapsed(`Element ${index + 1}`);
              console.log('%cHTML:', 'font-weight: bold;', node.html);
              console.log('%cSelector:', 'font-weight: bold;', node.target.join(' > '));
              console.log('%cFix:', 'font-weight: bold;', node.failureSummary);
              console.groupEnd();
            });

            console.groupEnd();
          });

          console.log(
            `%cTotal: ${results.violations.length} violation(s) affecting ${
              results.violations.reduce((acc, v) => acc + v.nodes.length, 0)
            } element(s)`,
            'color: #ff6b6b;'
          );

          console.groupEnd();
        } else {
          console.log(
            '%c♿ No accessibility violations found!',
            'color: #51cf66; font-weight: bold;'
          );
        }
      } catch (error) {
        // axe-core not available - silently skip
        if (error instanceof Error && !error.message.includes('axe-core')) {
          console.warn('[A11yDevTools] Error running accessibility check:', error);
        }
      }
    };

    const debouncedCheck = () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
      debounceRef.current = setTimeout(runAxeCheck, debounceMs);
    };

    // Run initial check
    if (autoRun) {
      // Small delay to ensure DOM is ready
      setTimeout(runAxeCheck, 500);
    }

    // Set up MutationObserver to catch dynamic changes
    const observer = new MutationObserver(debouncedCheck);

    observer.observe(context || document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['aria-label', 'aria-hidden', 'role', 'alt', 'title'],
    });

    return () => {
      observer.disconnect();
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [debounceMs, tags, autoRun, context]);

  // This component renders nothing
  return null;
}

/**
 * Get console color based on violation impact
 */
function getImpactColor(impact: string | null | undefined): string {
  switch (impact) {
    case 'critical':
      return '#ff0000';
    case 'serious':
      return '#ff6b6b';
    case 'moderate':
      return '#ffa94d';
    case 'minor':
      return '#ffd43b';
    default:
      return '#868e96';
  }
}

export default A11yDevTools;
