/**
 * Tests for SkillVersionWarning component
 *
 * TDD: Tests written first per project guidelines.
 * WCAG 2.2 AA accessibility verified.
 *
 * Shows warnings when a skill reference uses a version that
 * differs from the currently installed version.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { SkillVersionWarning } from "./SkillVersionWarning";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SkillVersionWarning", () => {
  describe("rendering", () => {
    it("should render nothing when versions match", () => {
      const { container } = render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.2.0"
            installedVersion="1.2.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("should render nothing when no versions provided", () => {
      const { container } = render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion={undefined}
            installedVersion={undefined}
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("should render warning when versions differ", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should show referenced version in warning", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/1\.0\.0/)).toBeInTheDocument();
    });

    it("should show installed version in warning", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/2\.0\.0/)).toBeInTheDocument();
    });

    it("should show skill name in warning", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/code-review/)).toBeInTheDocument();
    });
  });

  describe("severity levels", () => {
    it("should show major version warning for major version mismatch", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/Major version/i)).toBeInTheDocument();
    });

    it("should show minor version warning for minor version mismatch", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="1.1.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/Minor version/i)).toBeInTheDocument();
    });

    it("should show patch version warning for patch version mismatch", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="1.0.1"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/Patch version/i)).toBeInTheDocument();
    });

    it("should use error styling for major version mismatch", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="3.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("bg-danger-2");
    });

    it("should use warning styling for minor version mismatch", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="1.2.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("bg-warning-2");
    });

    it("should use info styling for patch version mismatch", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="1.0.5"
            skillName="code-review"
          />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveClass("bg-info-2");
    });
  });

  describe("upgrade/downgrade indication", () => {
    it("should indicate upgrade when installed is newer", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/newer version installed/i)).toBeInTheDocument();
    });

    it("should indicate downgrade warning when installed is older", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="2.0.0"
            installedVersion="1.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/older version installed/i)).toBeInTheDocument();
    });
  });

  describe("recommendations", () => {
    it("should suggest updating reference for major upgrade", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(
        screen.getByText(/Consider updating the reference/i),
      ).toBeInTheDocument();
    });

    it("should show breaking changes warning for major version difference", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="3.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/breaking changes/i)).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("should render compact version when compact prop is true", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
            compact
          />
        </TestProvider>,
      );

      // Compact shows just icon and brief text
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(screen.queryByText(/Consider updating/i)).not.toBeInTheDocument();
    });

    it("should still show version numbers in compact mode", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
            compact
          />
        </TestProvider>,
      );

      expect(screen.getByText(/1\.0\.0/)).toBeInTheDocument();
      expect(screen.getByText(/2\.0\.0/)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have alert role", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should have warning icon with aria-hidden", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      const svg = alert.querySelector("svg");
      expect(svg).toHaveAttribute("aria-hidden", "true");
    });

    it("should have descriptive text for screen readers", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="2.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("code-review");
      expect(alert.textContent).toContain("1.0.0");
      expect(alert.textContent).toContain("2.0.0");
    });
  });

  describe("edge cases", () => {
    it("should handle prerelease versions", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0-alpha"
            installedVersion="1.0.0"
            skillName="code-review"
          />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should handle build metadata in versions", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0+build.123"
            installedVersion="1.0.0+build.456"
            skillName="code-review"
          />
        </TestProvider>,
      );

      // Build metadata should be ignored, versions are equal
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    it("should handle latest as installed version", () => {
      render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion="latest"
            skillName="code-review"
          />
        </TestProvider>,
      );

      // Cannot compare, show info message
      expect(
        screen.getByText(/Version comparison unavailable/i),
      ).toBeInTheDocument();
    });

    it("should handle missing installed version gracefully", () => {
      const { container } = render(
        <TestProvider>
          <SkillVersionWarning
            referencedVersion="1.0.0"
            installedVersion={undefined}
            skillName="code-review"
          />
        </TestProvider>,
      );

      // Should not crash, render nothing
      expect(container.firstChild).toBeNull();
    });
  });
});
