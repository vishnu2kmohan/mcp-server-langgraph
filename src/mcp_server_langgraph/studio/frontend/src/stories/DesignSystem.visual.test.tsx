/**
 * Design System Visual Regression Tests
 *
 * TDD tests for visual consistency of design system components.
 * Uses Vitest snapshot testing to catch unintended visual changes.
 *
 * These tests ensure:
 * - Color palette renders correctly across themes
 * - Typography scale is consistent
 * - Animation tokens work as expected
 * - Spacing follows the 4px grid
 * - Design token validation stories render without errors
 *
 * @see docs-internal/frontend/DESIGN_SYSTEM_CHANGELOG.md
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { composeStories } from "@storybook/react";

// Import stories from design system
import * as ColorPaletteStories from "./ColorPalette.stories";
import * as TypographyStories from "./Typography.stories";
import * as SpacingStories from "./Spacing.stories";
import * as AnimationsStories from "./Animations.stories";
import * as DesignTokenValidationStories from "./DesignTokenValidation.stories";

import { TestProvider } from "@/test-utils";

// Compose stories for testing
const ColorPalette = composeStories(ColorPaletteStories);
const Typography = composeStories(TypographyStories);
const Spacing = composeStories(SpacingStories);
const Animations = composeStories(AnimationsStories);
const DesignTokenValidation = composeStories(DesignTokenValidationStories);

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
  // Mock requestAnimationFrame for animation tests
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    cb(0);
    return 0;
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

// =============================================================================
// Color Palette Visual Tests
// =============================================================================

describe("ColorPalette Stories", () => {
  it("should render Palette story without errors", () => {
    const { container } = render(
      <TestProvider>
        <ColorPalette.Palette />
      </TestProvider>,
    );
    // Check for semantic color names in content
    const content = container.textContent || "";
    expect(content).toMatch(/primary/i);
    expect(content).toMatch(/success/i);
    expect(content).toMatch(/error/i);
    expect(content).toMatch(/warning/i);
  });

  it("should render Usage story without errors", () => {
    render(
      <TestProvider>
        <ColorPalette.Usage />
      </TestProvider>,
    );
    // Usage story shows how to use colors
    expect(document.body.textContent).toBeTruthy();
  });

  it("should render Accessibility story without errors", () => {
    render(
      <TestProvider>
        <ColorPalette.Accessibility />
      </TestProvider>,
    );
    expect(document.body.textContent).toBeTruthy();
  });

  it("should match Palette snapshot", () => {
    const { container } = render(
      <TestProvider>
        <ColorPalette.Palette />
      </TestProvider>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("should render color shades for each semantic color", () => {
    const { container } = render(
      <TestProvider>
        <ColorPalette.Palette />
      </TestProvider>,
    );
    // Each semantic color palette should have multiple shade swatches
    const colorSwatches = container.querySelectorAll('[class*="bg-"]');
    expect(colorSwatches.length).toBeGreaterThan(20);
  });

  it("should use semantic color names, not raw Tailwind", () => {
    const { container } = render(
      <TestProvider>
        <ColorPalette.Palette />
      </TestProvider>,
    );
    // Should NOT contain raw Tailwind color classes
    expect(container.innerHTML).not.toMatch(/\btext-blue-\d{3}\b/);
    expect(container.innerHTML).not.toMatch(/\bbg-red-\d{3}\b/);
  });
});

// =============================================================================
// Typography Visual Tests
// =============================================================================

describe("Typography Stories", () => {
  it("should render Scale story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Scale />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/typography scale/i);
  });

  it("should render Fonts story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Fonts />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/inter/i);
    expect(content).toMatch(/jetbrains mono/i);
  });

  it("should render Weights story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Weights />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/normal/i);
    expect(content).toMatch(/medium/i);
    expect(content).toMatch(/bold/i);
  });

  it("should render Headings story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Headings />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/heading hierarchy/i);
  });

  it("should render Accessibility story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Accessibility />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/typography accessibility/i);
  });

  it("should match Scale snapshot", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Scale />
      </TestProvider>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("should display all text size classes from xs to 4xl", () => {
    render(
      <TestProvider>
        <Typography.Scale />
      </TestProvider>,
    );
    const sizes = [
      "text-xs",
      "text-sm",
      "text-base",
      "text-lg",
      "text-xl",
      "text-2xl",
      "text-3xl",
      "text-4xl",
    ];
    sizes.forEach((size) => {
      expect(screen.getByText(size)).toBeInTheDocument();
    });
  });
});

// =============================================================================
// Spacing Visual Tests
// =============================================================================

describe("Spacing Stories", () => {
  it("should render Scale story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Spacing.Scale />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/spacing scale/i);
  });

  it("should render Rules story without errors", () => {
    render(
      <TestProvider>
        <Spacing.Rules />
      </TestProvider>,
    );
    expect(document.body.textContent).toBeTruthy();
  });

  it("should render Components story without errors", () => {
    render(
      <TestProvider>
        <Spacing.Components />
      </TestProvider>,
    );
    expect(document.body.textContent).toBeTruthy();
  });

  it("should match Scale snapshot", () => {
    const { container } = render(
      <TestProvider>
        <Spacing.Scale />
      </TestProvider>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("should display spacing tokens with pixel values", () => {
    const { container } = render(
      <TestProvider>
        <Spacing.Scale />
      </TestProvider>,
    );
    const content = container.textContent || "";
    // Check for pixel values in the scale
    expect(content).toMatch(/4px/);
    expect(content).toMatch(/8px/);
    expect(content).toMatch(/16px/);
  });

  it("should mention 4px grid in documentation", () => {
    const { container } = render(
      <TestProvider>
        <Spacing.Scale />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/4px/i);
  });
});

// =============================================================================
// Animation Visual Tests
// =============================================================================

describe("Animations Stories", () => {
  it("should render Durations story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Animations.Durations />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/duration/i);
  });

  it("should render Easings story without errors", () => {
    const { container } = render(
      <TestProvider>
        <Animations.Easings />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/easing/i);
  });

  it("should render Presets story without errors", () => {
    render(
      <TestProvider>
        <Animations.Presets />
      </TestProvider>,
    );
    expect(document.body.textContent).toBeTruthy();
  });

  it("should match Durations snapshot", () => {
    const { container } = render(
      <TestProvider>
        <Animations.Durations />
      </TestProvider>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("should display standard duration values", () => {
    const { container } = render(
      <TestProvider>
        <Animations.Durations />
      </TestProvider>,
    );
    // Duration values should be present in the content
    const content = container.textContent || "";
    expect(content).toMatch(/75|100|150|200|300/);
  });

  it("should render Accessibility story for reduced motion", () => {
    const { container } = render(
      <TestProvider>
        <Animations.Accessibility />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/reduced motion/i);
  });
});

// =============================================================================
// Design Token Validation Visual Tests
// =============================================================================

describe("DesignTokenValidation Stories", () => {
  it("should render Dashboard story without errors", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.Dashboard />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/design.*token/i);
  });

  it("should render ZIndex story without errors", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.ZIndex />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/z-index/i);
  });

  it("should render Animation story without errors", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.Animation />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/animation/i);
  });

  it("should render Sizing story without errors", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.Sizing />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/sizing/i);
  });

  it("should render AuditCommands story without errors", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.AuditCommands />
      </TestProvider>,
    );
    const content = container.textContent || "";
    expect(content).toMatch(/audit/i);
  });

  it("should match Dashboard snapshot", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.Dashboard />
      </TestProvider>,
    );
    expect(container.firstChild).toMatchSnapshot();
  });

  it("should display z-index token examples", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.ZIndex />
      </TestProvider>,
    );
    const content = container.textContent || "";
    // Should mention token values
    expect(content).toMatch(/z-(0|10|50|55|60|65|70|75)/);
  });

  it("should show audit command examples", () => {
    const { container } = render(
      <TestProvider>
        <DesignTokenValidation.AuditCommands />
      </TestProvider>,
    );
    // Should show npm run command(s)
    const content = container.textContent || "";
    expect(content).toMatch(/npm run/);
  });
});

// =============================================================================
// Cross-Story Consistency Tests
// =============================================================================

describe("Design System Consistency", () => {
  it("should use consistent color naming across stories", () => {
    // Verify semantic color names are used consistently
    const { container: colorContainer } = render(
      <TestProvider>
        <ColorPalette.Palette />
      </TestProvider>,
    );
    cleanup();

    const { container: typographyContainer } = render(
      <TestProvider>
        <Typography.Accessibility />
      </TestProvider>,
    );

    // Both should NOT contain raw Tailwind colors
    expect(colorContainer.innerHTML).not.toMatch(/\btext-blue-\d{3}\b/);
    expect(typographyContainer.innerHTML).not.toMatch(/\btext-blue-\d{3}\b/);
  });

  it("should use semantic neutral colors (neutral-X)", () => {
    const { container } = render(
      <TestProvider>
        <ColorPalette.Palette />
      </TestProvider>,
    );

    // Should use semantic neutral classes
    expect(container.innerHTML).toMatch(/neutral-\d{1,2}/);
  });

  it("should not use legacy Tailwind neutral scale in UI text", () => {
    const { container } = render(
      <TestProvider>
        <Typography.Scale />
      </TestProvider>,
    );

    // Should NOT use raw Tailwind gray shades for text
    expect(container.innerHTML).not.toMatch(/\btext-gray-\d{3}\b/);
  });
});
