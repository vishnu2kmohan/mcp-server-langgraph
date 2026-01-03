/**
 * Internationalization (i18n) Configuration
 *
 * Provides i18n infrastructure using react-i18next.
 *
 * Stage 1 (Current):
 * - Single namespace: 'common'
 * - English only
 * - Browser language detection
 *
 * Stage 2 (Future):
 * - Additional namespaces: 'studio', 'errors'
 * - Additional languages as content owners are identified
 *
 * @example
 * ```tsx
 * // In app entry point
 * import { initI18n } from '@mcp-server-langgraph/shared-frontend/i18n';
 *
 * await initI18n();
 *
 * // In components
 * import { useAppTranslation } from '@mcp-server-langgraph/shared-frontend/i18n';
 *
 * function MyComponent() {
 *   const { t } = useAppTranslation();
 *   return <h1>{t('nav.projects')}</h1>;
 * }
 * ```
 */

import i18n, { type Resource } from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// =============================================================================
// Configuration
// =============================================================================

/**
 * Supported languages (Stage 1: English only)
 */
export const SUPPORTED_LANGUAGES = ["en"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

/**
 * Translation namespaces (Stage 1: common only)
 */
export const TRANSLATION_NAMESPACES = ["common"] as const;
export type TranslationNamespace = (typeof TRANSLATION_NAMESPACES)[number];

/**
 * Default translations (English - common namespace)
 * These are bundled with the package for fast initial load.
 */
export const defaultTranslations: Record<string, Record<string, unknown>> = {
  en: {
    common: {
      // Navigation
      nav: {
        projects: "Projects",
        chat: "Chat",
        workflows: "Workflows",
        agents: "Agents",
        mcp: "MCP Servers",
        vectors: "Vectors",
        connections: "Connections",
        files: "Files",
        traces: "Traces",
        observability: "Observability",
        cost: "Cost",
        admin: "Admin",
        audit: "Audit",
        compliance: "Compliance",
        help: "Help",
        settings: "Settings",
      },
      // Common actions
      actions: {
        save: "Save",
        cancel: "Cancel",
        delete: "Delete",
        confirm: "Confirm",
        create: "Create",
        edit: "Edit",
        view: "View",
        close: "Close",
        submit: "Submit",
        search: "Search",
        filter: "Filter",
        refresh: "Refresh",
        export: "Export",
        import: "Import",
        copy: "Copy",
        paste: "Paste",
        undo: "Undo",
        redo: "Redo",
      },
      // Common status
      status: {
        loading: "Loading...",
        saving: "Saving...",
        success: "Success",
        error: "Error",
        pending: "Pending",
        active: "Active",
        inactive: "Inactive",
        draft: "Draft",
        published: "Published",
        archived: "Archived",
      },
      // Persona names
      persona: {
        admin: "Administrator",
        "security-admin": "Security Admin",
        auditor: "Auditor",
        "alice-builder": "Builder",
        "alice-analyst": "Analyst",
        "alice-devops": "DevOps",
        "compliance-officer": "Compliance Officer",
        bob: "User",
      },
      // Error messages
      errors: {
        generic: "Something went wrong. Please try again.",
        network: "Network error. Please check your connection.",
        unauthorized: "You are not authorized to perform this action.",
        notFound: "The requested resource was not found.",
        validation: "Please check your input and try again.",
        timeout: "The request timed out. Please try again.",
      },
      // Confirmation messages
      confirm: {
        delete: "Are you sure you want to delete this item?",
        unsavedChanges:
          "You have unsaved changes. Are you sure you want to leave?",
        logout: "Are you sure you want to log out?",
      },
      // Accessibility
      a11y: {
        skipToContent: "Skip to main content",
        openMenu: "Open menu",
        closeMenu: "Close menu",
        expandSection: "Expand section",
        collapseSection: "Collapse section",
        loading: "Loading, please wait",
      },
    },
  },
};

// =============================================================================
// Initialization
// =============================================================================

let initialized = false;

/**
 * Initialize i18n with react-i18next.
 *
 * Call this once at app startup before rendering.
 *
 * @param options - Optional configuration overrides
 */
export async function initI18n(options?: {
  /** Override default language */
  defaultLanguage?: SupportedLanguage;
  /** Additional translations to merge */
  additionalTranslations?: Record<string, Record<string, unknown>>;
  /** Disable language detection */
  disableDetection?: boolean;
}): Promise<typeof i18n> {
  if (initialized) {
    return i18n;
  }

  const resources: Resource = {
    ...defaultTranslations,
    ...options?.additionalTranslations,
  } as Resource;

  await i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources,
      fallbackLng: options?.defaultLanguage ?? "en",
      supportedLngs: [...SUPPORTED_LANGUAGES],
      ns: [...TRANSLATION_NAMESPACES],
      defaultNS: "common",
      interpolation: {
        escapeValue: false, // React already escapes
      },
      detection: options?.disableDetection
        ? undefined
        : {
            order: ["localStorage", "navigator", "htmlTag"],
            caches: ["localStorage"],
            lookupLocalStorage: "i18nextLng",
          },
      react: {
        useSuspense: true,
      },
    });

  initialized = true;
  return i18n;
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Translation hook with proper typing for our namespaces.
 *
 * @param ns - Namespace(s) to use (default: 'common')
 * @returns Translation function and i18n instance
 *
 * @example
 * ```tsx
 * const { t } = useAppTranslation();
 * return <button>{t('actions.save')}</button>;
 * ```
 */
export function useAppTranslation(
  ns: TranslationNamespace | TranslationNamespace[] = "common"
) {
  return useTranslation(ns);
}

/**
 * Get current language.
 */
export function useCurrentLanguage(): SupportedLanguage {
  const { i18n: i18nInstance } = useTranslation();
  return (i18nInstance.language as SupportedLanguage) || "en";
}

/**
 * Change the current language.
 */
export function useChangeLanguage() {
  const { i18n: i18nInstance } = useTranslation();

  return async (language: SupportedLanguage) => {
    await i18nInstance.changeLanguage(language);
  };
}

// =============================================================================
// Exports
// =============================================================================

export { i18n };
export default i18n;
