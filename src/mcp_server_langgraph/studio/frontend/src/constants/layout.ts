/**
 * Shell-aware page layout classes.
 *
 * Pages inside StudioShellLayout use `page-shell` (flex-1, min-h-0).
 * Standalone pages (login, callbacks) use `page-legacy` (min-h-screen).
 *
 * IMPORTANT: Do NOT add overflow-y-auto - shell owns scrolling via route-outlet.
 *
 * @see src/index.css for CSS definitions
 * @see src/layout/StudioShellLayout.tsx for shell implementation
 */
export const PAGE_CLASSES = {
  /**
   * For pages inside StudioShellLayout.
   * Uses flex-1 and min-h-0 to fill available space without overflow.
   */
  shell: 'page-shell bg-neutral-1',

  /**
   * Loading state for shell pages.
   * Centers loading indicator within available space.
   */
  shellLoading: 'page-shell flex items-center justify-center',

  /**
   * Error state for shell pages.
   * Centers error message within available space.
   */
  shellError: 'page-shell flex items-center justify-center',

  /**
   * For standalone pages (login, callbacks) or legacy mode.
   * Uses min-h-screen for full viewport height.
   */
  standalone: 'page-legacy bg-neutral-1',

  /**
   * Loading state for standalone pages.
   */
  standaloneLoading: 'page-legacy flex items-center justify-center',
} as const;

/**
 * Type for PAGE_CLASSES keys
 */
export type PageClassKey = keyof typeof PAGE_CLASSES;
