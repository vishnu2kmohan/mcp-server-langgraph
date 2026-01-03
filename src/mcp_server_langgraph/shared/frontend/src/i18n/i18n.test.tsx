/**
 * i18n Infrastructure Tests
 *
 * TDD tests for internationalization configuration and hooks.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { Suspense, type ReactNode } from "react";
import { I18nextProvider } from "react-i18next";

import {
  initI18n,
  useAppTranslation,
  useCurrentLanguage,
  useChangeLanguage,
  defaultTranslations,
  SUPPORTED_LANGUAGES,
  TRANSLATION_NAMESPACES,
  i18n,
} from "./index";

// Reset i18n between tests
beforeEach(async () => {
  // Reset i18n instance
  if (i18n.isInitialized) {
    await i18n.changeLanguage("en");
  }
});

describe("i18n Configuration", () => {
  describe("Constants", () => {
    it("should have English as supported language", () => {
      expect(SUPPORTED_LANGUAGES).toContain("en");
    });

    it("should have common as translation namespace", () => {
      expect(TRANSLATION_NAMESPACES).toContain("common");
    });

    it("should have default translations for English", () => {
      expect(defaultTranslations.en).toBeDefined();
      expect(defaultTranslations.en.common).toBeDefined();
    });
  });

  describe("Default Translations Structure", () => {
    it("should have navigation translations", () => {
      const nav = defaultTranslations.en.common as Record<string, unknown>;
      expect(nav.nav).toBeDefined();

      const navItems = nav.nav as Record<string, string>;
      expect(navItems.projects).toBe("Projects");
      expect(navItems.chat).toBe("Chat");
      expect(navItems.workflows).toBe("Workflows");
    });

    it("should have action translations", () => {
      const common = defaultTranslations.en.common as Record<string, unknown>;
      expect(common.actions).toBeDefined();

      const actions = common.actions as Record<string, string>;
      expect(actions.save).toBe("Save");
      expect(actions.cancel).toBe("Cancel");
      expect(actions.delete).toBe("Delete");
    });

    it("should have status translations", () => {
      const common = defaultTranslations.en.common as Record<string, unknown>;
      expect(common.status).toBeDefined();

      const status = common.status as Record<string, string>;
      expect(status.loading).toBe("Loading...");
      expect(status.success).toBe("Success");
      expect(status.error).toBe("Error");
    });

    it("should have persona translations", () => {
      const common = defaultTranslations.en.common as Record<string, unknown>;
      expect(common.persona).toBeDefined();

      const persona = common.persona as Record<string, string>;
      expect(persona.admin).toBe("Administrator");
      expect(persona["alice-builder"]).toBe("Builder");
      expect(persona.bob).toBe("User");
    });

    it("should have error translations", () => {
      const common = defaultTranslations.en.common as Record<string, unknown>;
      expect(common.errors).toBeDefined();

      const errors = common.errors as Record<string, string>;
      expect(errors.generic).toContain("went wrong");
      expect(errors.network).toContain("Network");
    });

    it("should have accessibility translations", () => {
      const common = defaultTranslations.en.common as Record<string, unknown>;
      expect(common.a11y).toBeDefined();

      const a11y = common.a11y as Record<string, string>;
      expect(a11y.skipToContent).toBe("Skip to main content");
      expect(a11y.loading).toContain("Loading");
    });
  });
});

describe("initI18n", () => {
  it("should initialize i18n with default settings", async () => {
    const instance = await initI18n({ disableDetection: true });

    expect(instance.isInitialized).toBe(true);
    expect(instance.language).toBe("en");
  });

  it("should support custom default language", async () => {
    const instance = await initI18n({
      defaultLanguage: "en",
      disableDetection: true,
    });

    expect(instance.language).toBe("en");
  });

  it("should support additional translations parameter", async () => {
    // Note: Once initialized, i18n caches and won't reinitialize
    // This test verifies the parameter is accepted without error
    const additionalTranslations = {
      en: {
        common: {
          custom: {
            greeting: "Hello, World!",
          },
        },
      },
    };

    // Should not throw when passed additional translations
    const instance = await initI18n({
      additionalTranslations,
      disableDetection: true,
    });

    expect(instance.isInitialized).toBe(true);
    // Default translations should still work
    expect(i18n.t("nav.projects")).toBe("Projects");
  });

  it("should return same instance on multiple calls", async () => {
    const instance1 = await initI18n({ disableDetection: true });
    const instance2 = await initI18n({ disableDetection: true });

    expect(instance1).toBe(instance2);
  });
});

describe("useAppTranslation", () => {
  // Create wrapper with initialized i18n
  function createWrapper() {
    return function Wrapper({ children }: { children: ReactNode }) {
      return (
        <Suspense fallback="Loading...">
          <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
        </Suspense>
      );
    };
  }

  beforeEach(async () => {
    await initI18n({ disableDetection: true });
  });

  it("should return translation function", async () => {
    const wrapper = createWrapper();

    const { result } = renderHook(() => useAppTranslation(), { wrapper });

    await waitFor(() => {
      expect(result.current.t).toBeDefined();
    });
  });

  it("should translate navigation keys", async () => {
    const wrapper = createWrapper();

    const { result } = renderHook(() => useAppTranslation(), { wrapper });

    await waitFor(() => {
      expect(result.current.t("nav.projects")).toBe("Projects");
      expect(result.current.t("nav.chat")).toBe("Chat");
    });
  });

  it("should translate action keys", async () => {
    const wrapper = createWrapper();

    const { result } = renderHook(() => useAppTranslation(), { wrapper });

    await waitFor(() => {
      expect(result.current.t("actions.save")).toBe("Save");
      expect(result.current.t("actions.cancel")).toBe("Cancel");
    });
  });

  it("should return key for missing translations", async () => {
    const wrapper = createWrapper();

    const { result } = renderHook(() => useAppTranslation(), { wrapper });

    await waitFor(() => {
      // Missing keys return the key itself
      expect(result.current.t("nonexistent.key")).toBe("nonexistent.key");
    });
  });
});

describe("useCurrentLanguage", () => {
  function createWrapper() {
    return function Wrapper({ children }: { children: ReactNode }) {
      return (
        <Suspense fallback="Loading...">
          <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
        </Suspense>
      );
    };
  }

  beforeEach(async () => {
    await initI18n({ disableDetection: true });
  });

  it("should return current language", async () => {
    const wrapper = createWrapper();

    const { result } = renderHook(() => useCurrentLanguage(), { wrapper });

    await waitFor(() => {
      expect(result.current).toBe("en");
    });
  });
});

describe("useChangeLanguage", () => {
  function createWrapper() {
    return function Wrapper({ children }: { children: ReactNode }) {
      return (
        <Suspense fallback="Loading...">
          <I18nextProvider i18n={i18n}>{children}</I18nextProvider>
        </Suspense>
      );
    };
  }

  beforeEach(async () => {
    await initI18n({ disableDetection: true });
  });

  it("should return change language function", async () => {
    const wrapper = createWrapper();

    const { result } = renderHook(() => useChangeLanguage(), { wrapper });

    await waitFor(() => {
      expect(typeof result.current).toBe("function");
    });
  });
});
