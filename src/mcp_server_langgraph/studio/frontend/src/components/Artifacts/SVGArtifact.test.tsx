/**
 * SVGArtifact Tests
 *
 * TDD tests for SVG artifact rendering component.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SVGArtifact } from "./SVGArtifact";

describe("SVGArtifact", () => {
  const simpleSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <circle cx="50" cy="50" r="40" fill="red" />
  </svg>`;

  describe("rendering", () => {
    it("should render SVG content inline", () => {
      render(<SVGArtifact data={simpleSvg} />);
      // SVG should be rendered
      const svg = document.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("should render circle element from SVG", () => {
      render(<SVGArtifact data={simpleSvg} />);
      const circle = document.querySelector("circle");
      expect(circle).toBeInTheDocument();
      expect(circle).toHaveAttribute("fill", "red");
    });

    it("should apply custom width from config", () => {
      render(<SVGArtifact data={simpleSvg} config={{ width: 200 }} />);
      const container = screen.getByTestId("svg-container");
      expect(container).toHaveStyle({ width: "200px" });
    });

    it("should apply custom height from config", () => {
      render(<SVGArtifact data={simpleSvg} config={{ height: 150 }} />);
      const container = screen.getByTestId("svg-container");
      expect(container).toHaveStyle({ height: "150px" });
    });

    it("should render title if provided", () => {
      render(<SVGArtifact data={simpleSvg} title="My SVG Diagram" />);
      expect(screen.getByText("My SVG Diagram")).toBeInTheDocument();
    });
  });

  describe("data URL handling", () => {
    it("should handle base64 SVG data URL", () => {
      const base64Svg = `data:image/svg+xml;base64,${btoa(simpleSvg)}`;
      render(<SVGArtifact data={base64Svg} />);
      const svg = document.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });

    it("should handle URL-encoded SVG data URL", () => {
      const encodedSvg = `data:image/svg+xml,${encodeURIComponent(simpleSvg)}`;
      render(<SVGArtifact data={encodedSvg} />);
      const svg = document.querySelector("svg");
      expect(svg).toBeInTheDocument();
    });
  });

  describe("error handling", () => {
    it("should show error for invalid SVG", () => {
      render(<SVGArtifact data="not valid svg" />);
      expect(screen.getByText(/invalid svg/i)).toBeInTheDocument();
    });

    it("should show error for empty data", () => {
      render(<SVGArtifact data="" />);
      expect(screen.getByText(/no svg data/i)).toBeInTheDocument();
    });
  });

  describe("security", () => {
    it("should sanitize script tags from SVG", () => {
      const maliciousSvg = `<svg xmlns="http://www.w3.org/2000/svg">
        <script>alert('xss')</script>
        <circle cx="50" cy="50" r="40" fill="blue" />
      </svg>`;
      render(<SVGArtifact data={maliciousSvg} />);
      // Script should be removed
      const script = document.querySelector("script");
      expect(script).not.toBeInTheDocument();
      // Circle should still render
      const circle = document.querySelector("circle");
      expect(circle).toBeInTheDocument();
    });

    it("should remove event handlers from SVG elements", () => {
      const svgWithHandlers = `<svg xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="40" onclick="alert('clicked')" fill="green" />
      </svg>`;
      render(<SVGArtifact data={svgWithHandlers} />);
      const circle = document.querySelector("circle");
      expect(circle).not.toHaveAttribute("onclick");
    });
  });
});
