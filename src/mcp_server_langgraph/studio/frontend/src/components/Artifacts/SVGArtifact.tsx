/**
 * SVGArtifact Component
 *
 * Renders SVG content inline with sanitization for security.
 * Supports raw SVG markup, base64 data URLs, and URL-encoded data URLs.
 */

import { useMemo } from "react";
import type { SVGConfig } from "../../types/artifacts";

export interface SVGArtifactProps {
  data: string;
  title?: string;
  config?: SVGConfig;
}

/**
 * Sanitize SVG content to remove potentially dangerous elements and attributes
 */
function sanitizeSvg(svgContent: string): string {
  // Create a DOM parser to parse the SVG
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgContent, "image/svg+xml");

  // Check for parsing errors
  const parserError = doc.querySelector("parsererror");
  if (parserError) {
    throw new Error("Invalid SVG content");
  }

  const svg = doc.querySelector("svg");
  if (!svg) {
    throw new Error("No SVG element found");
  }

  // Remove dangerous elements
  const dangerousElements = [
    "script",
    "foreignObject",
    "iframe",
    "object",
    "embed",
  ];
  dangerousElements.forEach((tag) => {
    const elements = svg.querySelectorAll(tag);
    elements.forEach((el) => el.remove());
  });

  // Remove event handlers from all elements
  const allElements = svg.querySelectorAll("*");
  allElements.forEach((el) => {
    // Get all attributes
    const attrs = Array.from(el.attributes);
    attrs.forEach((attr) => {
      // Remove event handlers (on*)
      if (attr.name.toLowerCase().startsWith("on")) {
        el.removeAttribute(attr.name);
      }
      // Remove javascript: URLs
      if (attr.value.toLowerCase().includes("javascript:")) {
        el.removeAttribute(attr.name);
      }
    });
  });

  // Also sanitize the SVG element itself
  const svgAttrs = Array.from(svg.attributes);
  svgAttrs.forEach((attr) => {
    if (attr.name.toLowerCase().startsWith("on")) {
      svg.removeAttribute(attr.name);
    }
  });

  return svg.outerHTML;
}

/**
 * Extract SVG content from data URL or raw SVG
 */
function extractSvgContent(data: string): string {
  // Handle base64 data URL
  if (data.startsWith("data:image/svg+xml;base64,")) {
    const base64 = data.replace("data:image/svg+xml;base64,", "");
    return atob(base64);
  }

  // Handle URL-encoded data URL
  if (data.startsWith("data:image/svg+xml,")) {
    const encoded = data.replace("data:image/svg+xml,", "");
    return decodeURIComponent(encoded);
  }

  // Raw SVG content
  return data;
}

export function SVGArtifact({ data, title, config }: SVGArtifactProps) {
  const { sanitizedSvg, error } = useMemo(() => {
    if (!data || data.trim() === "") {
      return { sanitizedSvg: null, error: "No SVG data provided" };
    }

    try {
      const svgContent = extractSvgContent(data);
      const sanitized = sanitizeSvg(svgContent);
      return { sanitizedSvg: sanitized, error: null };
    } catch (err) {
      return {
        sanitizedSvg: null,
        error: err instanceof Error ? err.message : "Invalid SVG",
      };
    }
  }, [data]);

  const containerStyle: React.CSSProperties = {
    width: config?.width
      ? typeof config.width === "number"
        ? `${config.width}px`
        : config.width
      : undefined,
    height: config?.height
      ? typeof config.height === "number"
        ? `${config.height}px`
        : config.height
      : undefined,
  };

  if (error) {
    return (
      <div
        className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden">
      {title && (
        <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {title}
          </h4>
        </div>
      )}
      <div
        data-testid="svg-container"
        className="p-4 flex items-center justify-center"
        style={containerStyle}
        dangerouslySetInnerHTML={{ __html: sanitizedSvg || "" }}
      />
    </div>
  );
}
