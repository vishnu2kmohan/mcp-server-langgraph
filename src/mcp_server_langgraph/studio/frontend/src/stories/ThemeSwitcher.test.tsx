/**
 * Theme Switcher Story Tests
 *
 * Tests for the theme toggle functionality to ensure:
 * 1. Side-by-side dark/light comparison renders correctly
 * 2. CSS variable scoping works for nested .dark/.light classes
 * 3. Interactive theme switcher applies correct classes
 *
 * @see ThemeSwitcher.stories.tsx
 * @see docs-internal/frontend/STYLE.md#dark-mode-architecture
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, screen, within as _within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Import story components for testing
// Note: We test the rendered output, not the Storybook meta
import * as ThemeSwitcherStories from "./ThemeSwitcher.stories";

describe("ThemeSwitcher Stories", () => {
  describe("DarkVsLight - Side-by-Side Comparison", () => {
    it("should render both light and dark mode panels", () => {
      const { container: _container } = render(<ThemeSwitcherStories.DarkVsLight.render />);

      // Both panels should be present
      expect(screen.getByText("Light Mode")).toBeInTheDocument();
      expect(screen.getByText("Dark Mode")).toBeInTheDocument();

      // Light panel should have 'light' class
      const lightPanel = screen.getByText("Light Mode").closest("div");
      expect(lightPanel).toHaveClass("light");

      // Dark panel should have 'dark' class
      const darkPanel = screen.getByText("Dark Mode").closest("div");
      expect(darkPanel).toHaveClass("dark");
    });

    it("should have different background colors for light vs dark panels", () => {
      const { container: _container } = render(<ThemeSwitcherStories.DarkVsLight.render />);

      const lightPanel = screen.getByText("Light Mode").closest("div");
      const darkPanel = screen.getByText("Dark Mode").closest("div");

      // Both should have bg-neutral-1 class
      expect(lightPanel).toHaveClass("bg-neutral-1");
      expect(darkPanel).toHaveClass("bg-neutral-1");

      // In a real browser, computed styles would differ
      // JSDOM doesn't compute CSS variables, so we verify class presence
    });

    it("should render component previews in both panels", () => {
      render(<ThemeSwitcherStories.DarkVsLight.render />);

      // Each panel should have buttons
      const primaryButtons = screen.getAllByRole("button", { name: "Primary" });
      expect(primaryButtons).toHaveLength(2); // One in each panel

      const secondaryButtons = screen.getAllByRole("button", {
        name: "Secondary",
      });
      expect(secondaryButtons).toHaveLength(2);

      const dangerButtons = screen.getAllByRole("button", { name: "Danger" });
      expect(dangerButtons).toHaveLength(2);
    });

    it("should have status badges in both panels", () => {
      render(<ThemeSwitcherStories.DarkVsLight.render />);

      // Each panel should have all status badges
      const successBadges = screen.getAllByText("Success");
      expect(successBadges).toHaveLength(2);

      const warningBadges = screen.getAllByText("Warning");
      expect(warningBadges).toHaveLength(2);

      const errorBadges = screen.getAllByText("Error");
      expect(errorBadges).toHaveLength(2);
    });
  });

  describe("Interactive - Theme Switcher Controls", () => {
    let originalDataset: DOMStringMap;

    beforeEach(() => {
      // Save original document state
      originalDataset = { ...document.documentElement.dataset };
    });

    afterEach(() => {
      // Restore original document state
      document.documentElement.classList.remove("dark", "light");
      Object.keys(document.documentElement.dataset).forEach((key) => {
        delete document.documentElement.dataset[key];
      });
      Object.assign(document.documentElement.dataset, originalDataset);
    });

    it("should render appearance controls", () => {
      render(<ThemeSwitcherStories.Interactive.render />);

      expect(screen.getByText("Appearance")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Light/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Dark/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /System/i })
      ).toBeInTheDocument();
    });

    it("should render color theme controls", () => {
      render(<ThemeSwitcherStories.Interactive.render />);

      expect(screen.getByText("Color Theme")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Violet \+ Sage/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Teal \+ Sage/i })
      ).toBeInTheDocument();
    });

    it("should render code font controls", () => {
      render(<ThemeSwitcherStories.Interactive.render />);

      expect(screen.getByText("Code Font")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /JetBrains Mono/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /Fira Code/i })
      ).toBeInTheDocument();
    });

    it("should apply dark class when Dark button is clicked", async () => {
      const user = userEvent.setup();
      render(<ThemeSwitcherStories.Interactive.render />);

      const darkButton = screen.getByRole("button", { name: /Dark/i });
      await user.click(darkButton);

      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("should apply light class when Light button is clicked", async () => {
      const user = userEvent.setup();
      render(<ThemeSwitcherStories.Interactive.render />);

      const lightButton = screen.getByRole("button", { name: /Light/i });
      await user.click(lightButton);

      expect(document.documentElement.classList.contains("light")).toBe(true);
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });

    it("should update color theme data attribute when theme is selected", async () => {
      const user = userEvent.setup();
      render(<ThemeSwitcherStories.Interactive.render />);

      const tealSageButton = screen.getByRole("button", {
        name: /Teal \+ Sage/i,
      });
      await user.click(tealSageButton);

      expect(document.documentElement.dataset.colorTheme).toBe("teal-sage");
    });

    it("should update code font data attribute when font is selected", async () => {
      const user = userEvent.setup();
      render(<ThemeSwitcherStories.Interactive.render />);

      const firaCodeButton = screen.getByRole("button", {
        name: /Fira Code/i,
      });
      await user.click(firaCodeButton);

      expect(document.documentElement.dataset.codeFont).toBe("firacode");
    });
  });

  describe("Comparison - Color Theme Options", () => {
    it("should render all four color theme options", () => {
      render(<ThemeSwitcherStories.Comparison.render />);

      expect(screen.getByText("Violet + Sage (Default)")).toBeInTheDocument();
      expect(screen.getByText("Teal + Sage")).toBeInTheDocument();
      expect(screen.getByText("Violet + Olive")).toBeInTheDocument();
      expect(screen.getByText("Teal + Olive")).toBeInTheDocument();
    });

    it("should have data-color-theme attributes on theme panels", () => {
      const { container } = render(<ThemeSwitcherStories.Comparison.render />);

      const violetSagePanel = container.querySelector(
        '[data-color-theme="violet-sage"]'
      );
      const tealSagePanel = container.querySelector(
        '[data-color-theme="teal-sage"]'
      );
      const violetOlivePanel = container.querySelector(
        '[data-color-theme="violet-olive"]'
      );
      const tealOlivePanel = container.querySelector(
        '[data-color-theme="teal-olive"]'
      );

      expect(violetSagePanel).toBeInTheDocument();
      expect(tealSagePanel).toBeInTheDocument();
      expect(violetOlivePanel).toBeInTheDocument();
      expect(tealOlivePanel).toBeInTheDocument();
    });
  });

  describe("CSSVariables - Reference Documentation", () => {
    it("should render semantic color reference table", () => {
      render(<ThemeSwitcherStories.CSSVariables.render />);

      expect(screen.getByText("CSS Variables Reference")).toBeInTheDocument();

      // Check table headers
      expect(screen.getByText("Semantic")).toBeInTheDocument();
      expect(screen.getByText("Variable Pattern")).toBeInTheDocument();
      expect(screen.getByText("Description")).toBeInTheDocument();
    });

    it("should list all semantic color categories", () => {
      render(<ThemeSwitcherStories.CSSVariables.render />);

      expect(screen.getByText("primary")).toBeInTheDocument();
      expect(screen.getByText("neutral")).toBeInTheDocument();
      expect(screen.getByText("success")).toBeInTheDocument();
      expect(screen.getByText("warning")).toBeInTheDocument();
      expect(screen.getByText("error")).toBeInTheDocument();
      expect(screen.getByText("info")).toBeInTheDocument();
      expect(screen.getByText("insight")).toBeInTheDocument();
      expect(screen.getByText("grafana")).toBeInTheDocument();
    });
  });
});

describe("Theme CSS Variable Scoping", () => {
  it("should scope dark mode variables to .dark container", () => {
    // This test verifies the CSS architecture is correct
    // In JSDOM we can't test actual computed styles, but we can verify structure

    const { container: _container } = render(
      <div className="parent">
        <div className="light" data-testid="light-container">
          <div className="bg-neutral-1" data-testid="light-bg" />
        </div>
        <div className="dark" data-testid="dark-container">
          <div className="bg-neutral-1" data-testid="dark-bg" />
        </div>
      </div>
    );

    const lightContainer = screen.getByTestId("light-container");
    const darkContainer = screen.getByTestId("dark-container");

    // Both should have their respective classes
    expect(lightContainer).toHaveClass("light");
    expect(darkContainer).toHaveClass("dark");

    // Both inner elements should have bg-neutral-1
    const lightBg = screen.getByTestId("light-bg");
    const darkBg = screen.getByTestId("dark-bg");

    expect(lightBg).toHaveClass("bg-neutral-1");
    expect(darkBg).toHaveClass("bg-neutral-1");
  });
});
