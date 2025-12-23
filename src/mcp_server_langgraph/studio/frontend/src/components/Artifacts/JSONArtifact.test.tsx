/**
 * JSONArtifact Tests
 *
 * Tests for JSON tree view component with collapsible nodes.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { JSONArtifact } from "./JSONArtifact";
import type { JSONArtifact as JSONArtifactType } from "../../types/artifacts";

describe("JSONArtifact", () => {
  const mockSimpleArtifact: JSONArtifactType = {
    id: "json-1",
    type: "json",
    data: {
      name: "John Doe",
      age: 30,
      email: "john@example.com",
    },
  };

  const mockNestedArtifact: JSONArtifactType = {
    id: "json-2",
    type: "json",
    data: {
      user: {
        profile: {
          name: "Jane Smith",
          age: 25,
        },
        preferences: {
          theme: "dark",
          notifications: true,
        },
      },
      metadata: {
        created: "2024-01-01",
        updated: "2024-01-15",
      },
    },
  };

  const mockArrayArtifact: JSONArtifactType = {
    id: "json-3",
    type: "json",
    data: [
      { id: 1, name: "Item 1" },
      { id: 2, name: "Item 2" },
      { id: 3, name: "Item 3" },
    ],
  };

  beforeEach(() => {
    // Mock clipboard API
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn(() => Promise.resolve()),
      },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render simple JSON object", () => {
      render(<JSONArtifact artifact={mockSimpleArtifact} />);
      expect(screen.getByText(/name/i)).toBeInTheDocument();
      expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
    });

    it("should render with custom title", () => {
      const artifactWithTitle: JSONArtifactType = {
        ...mockSimpleArtifact,
        title: "User Data",
      };
      render(<JSONArtifact artifact={artifactWithTitle} />);
      expect(screen.getByText("User Data")).toBeInTheDocument();
    });

    it("should render nested objects", () => {
      render(<JSONArtifact artifact={mockNestedArtifact} />);
      expect(screen.getByText(/user/i)).toBeInTheDocument();
      expect(screen.getByText(/profile/i)).toBeInTheDocument();
    });

    it("should render arrays", () => {
      render(<JSONArtifact artifact={mockArrayArtifact} />);
      // Arrays should be rendered
      const container = screen.getByRole("region", { name: /json/i });
      expect(container).toBeInTheDocument();
    });
  });

  describe("Collapsing", () => {
    it("should collapse nested objects", async () => {
      const user = userEvent.setup();
      render(<JSONArtifact artifact={mockNestedArtifact} />);

      // Find collapse button for user object
      const collapseButtons = screen.getAllByRole("button", {
        name: /toggle/i,
      });
      expect(collapseButtons.length).toBeGreaterThan(0);

      // Click to collapse
      await user.click(collapseButtons[0]);

      // Content should still be present (as this is just a collapse, not remove)
      expect(screen.getByRole("region", { name: /json/i })).toBeInTheDocument();
    });

    it("should respect initial collapsed state", () => {
      const collapsedArtifact: JSONArtifactType = {
        ...mockNestedArtifact,
        config: {
          collapsed: true,
        },
      };
      render(<JSONArtifact artifact={collapsedArtifact} />);
      expect(screen.getByRole("region", { name: /json/i })).toBeInTheDocument();
    });

    it("should respect collapse depth", () => {
      const depthCollapsedArtifact: JSONArtifactType = {
        ...mockNestedArtifact,
        config: {
          collapsed: 2, // Collapse at depth 2
        },
      };
      render(<JSONArtifact artifact={depthCollapsedArtifact} />);
      expect(screen.getByRole("region", { name: /json/i })).toBeInTheDocument();
    });
  });

  describe("Copy Functionality", () => {
    it("should have copy button", () => {
      render(<JSONArtifact artifact={mockSimpleArtifact} />);
      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should show feedback after copying", async () => {
      const user = userEvent.setup();
      render(<JSONArtifact artifact={mockSimpleArtifact} />);

      const copyButton = screen.getByRole("button", { name: /copy/i });
      await user.click(copyButton);

      // Should show "Copied!" feedback
      expect(await screen.findByText(/copied/i)).toBeInTheDocument();
    });
  });

  describe("Primitive Types", () => {
    it("should render string values", () => {
      render(<JSONArtifact artifact={mockSimpleArtifact} />);
      expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
    });

    it("should render number values", () => {
      render(<JSONArtifact artifact={mockSimpleArtifact} />);
      expect(screen.getByText("30")).toBeInTheDocument();
    });

    it("should render boolean values", () => {
      const boolArtifact: JSONArtifactType = {
        id: "json-bool",
        type: "json",
        data: { active: true, disabled: false },
      };
      render(<JSONArtifact artifact={boolArtifact} />);
      expect(screen.getByText("true")).toBeInTheDocument();
      expect(screen.getByText("false")).toBeInTheDocument();
    });

    it("should render null values", () => {
      const nullArtifact: JSONArtifactType = {
        id: "json-null",
        type: "json",
        data: { value: null },
      };
      render(<JSONArtifact artifact={nullArtifact} />);
      expect(screen.getByText("null")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty object", () => {
      const emptyArtifact: JSONArtifactType = {
        id: "json-empty",
        type: "json",
        data: {},
      };
      render(<JSONArtifact artifact={emptyArtifact} />);
      expect(screen.getByRole("region", { name: /json/i })).toBeInTheDocument();
    });

    it("should handle empty array", () => {
      const emptyArrayArtifact: JSONArtifactType = {
        id: "json-empty-array",
        type: "json",
        data: [],
      };
      render(<JSONArtifact artifact={emptyArrayArtifact} />);
      expect(screen.getByRole("region", { name: /json/i })).toBeInTheDocument();
    });

    it("should handle deeply nested objects", () => {
      const deepArtifact: JSONArtifactType = {
        id: "json-deep",
        type: "json",
        data: {
          level1: {
            level2: {
              level3: {
                level4: {
                  value: "deep value",
                },
              },
            },
          },
        },
      };
      render(<JSONArtifact artifact={deepArtifact} />);
      expect(screen.getByRole("region", { name: /json/i })).toBeInTheDocument();
    });
  });

  describe("Theme Support", () => {
    it("should apply light theme", () => {
      const lightArtifact: JSONArtifactType = {
        ...mockSimpleArtifact,
        config: {
          theme: "light",
        },
      };
      const { container } = render(<JSONArtifact artifact={lightArtifact} />);
      const jsonContainer = container.querySelector('[data-theme="light"]');
      expect(jsonContainer).toBeInTheDocument();
    });

    it("should apply dark theme", () => {
      const darkArtifact: JSONArtifactType = {
        ...mockSimpleArtifact,
        config: {
          theme: "dark",
        },
      };
      const { container } = render(<JSONArtifact artifact={darkArtifact} />);
      const jsonContainer = container.querySelector('[data-theme="dark"]');
      expect(jsonContainer).toBeInTheDocument();
    });
  });

  describe("Download Functionality", () => {
    it("should have download button", () => {
      render(<JSONArtifact artifact={mockSimpleArtifact} />);
      expect(
        screen.getByRole("button", { name: /download/i }),
      ).toBeInTheDocument();
    });

    it("should trigger download when button clicked", async () => {
      const user = userEvent.setup();

      // Mock URL methods
      const createObjectURLMock = vi.fn(() => "blob:test-url");
      const revokeObjectURLMock = vi.fn();
      URL.createObjectURL = createObjectURLMock;
      URL.revokeObjectURL = revokeObjectURLMock;

      render(<JSONArtifact artifact={mockSimpleArtifact} />);
      const downloadButton = screen.getByRole("button", { name: /download/i });
      await user.click(downloadButton);

      // Verify blob URL was created and cleaned up
      expect(createObjectURLMock).toHaveBeenCalled();
      expect(revokeObjectURLMock).toHaveBeenCalled();
    });
  });
});
