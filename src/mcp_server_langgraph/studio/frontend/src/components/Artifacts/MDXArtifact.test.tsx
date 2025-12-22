/**
 * MDXArtifact Tests
 *
 * Tests for MDX content rendering with interactive components.
 */

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  MDXArtifact,
  Accordion,
  AccordionGroup,
  Callout,
  Note,
  Warning,
  Tip,
  Card,
  CardGroup,
  Tabs,
  Tab,
  Steps,
  Step,
} from "./MDXArtifact";

describe("MDXArtifact", () => {
  describe("Main Component", () => {
    it("should render MDX content", () => {
      render(<MDXArtifact data="# Hello World" />);
      expect(screen.getByText("# Hello World")).toBeInTheDocument();
    });

    it("should render with title when provided", () => {
      render(<MDXArtifact data="content" title="Test Document" />);
      expect(screen.getByText("Test Document")).toBeInTheDocument();
    });

    it("should render without title when not provided", () => {
      render(<MDXArtifact data="content" />);
      expect(screen.queryByRole("heading")).not.toBeInTheDocument();
    });

    it("should show custom components count when provided", () => {
      const customComponents = {
        CustomButton: () => <button>Custom</button>,
        CustomAlert: () => <div>Alert</div>,
      };
      render(<MDXArtifact data="content" components={customComponents} />);
      expect(screen.getByText("2 custom components")).toBeInTheDocument();
    });

    it("should not show components badge when no custom components", () => {
      render(<MDXArtifact data="content" />);
      expect(screen.queryByText(/custom components/)).not.toBeInTheDocument();
    });
  });

  describe("Accordion Component", () => {
    it("should render collapsed by default", () => {
      render(
        <Accordion title="Click me">
          <p>Hidden content</p>
        </Accordion>,
      );
      expect(screen.getByText("Click me")).toBeInTheDocument();
      expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
    });

    it("should expand when clicked", () => {
      render(
        <Accordion title="Click me">
          <p>Hidden content</p>
        </Accordion>,
      );
      fireEvent.click(screen.getByRole("button"));
      expect(screen.getByText("Hidden content")).toBeInTheDocument();
    });

    it("should collapse when clicked again", () => {
      render(
        <Accordion title="Click me">
          <p>Hidden content</p>
        </Accordion>,
      );
      const button = screen.getByRole("button");
      fireEvent.click(button);
      expect(screen.getByText("Hidden content")).toBeInTheDocument();
      fireEvent.click(button);
      expect(screen.queryByText("Hidden content")).not.toBeInTheDocument();
    });

    it("should render open when defaultOpen is true", () => {
      render(
        <Accordion title="Click me" defaultOpen>
          <p>Visible content</p>
        </Accordion>,
      );
      expect(screen.getByText("Visible content")).toBeInTheDocument();
    });

    it("should render icon when provided", () => {
      render(
        <Accordion title="Click me" icon={<span data-testid="icon">🎉</span>}>
          <p>Content</p>
        </Accordion>,
      );
      expect(screen.getByTestId("icon")).toBeInTheDocument();
    });
  });

  describe("AccordionGroup Component", () => {
    it("should render children", () => {
      render(
        <AccordionGroup>
          <Accordion title="First">Content 1</Accordion>
          <Accordion title="Second">Content 2</Accordion>
        </AccordionGroup>,
      );
      expect(screen.getByText("First")).toBeInTheDocument();
      expect(screen.getByText("Second")).toBeInTheDocument();
    });
  });

  describe("Callout Component", () => {
    it("should render note type by default", () => {
      render(<Callout>This is a note</Callout>);
      expect(screen.getByText("This is a note")).toBeInTheDocument();
    });

    it("should render with title when provided", () => {
      render(<Callout title="Important">Content here</Callout>);
      expect(screen.getByText("Important")).toBeInTheDocument();
      expect(screen.getByText("Content here")).toBeInTheDocument();
    });

    it("should render with emoji when provided", () => {
      render(<Callout emoji="🚀">Rocket content</Callout>);
      expect(screen.getByText("🚀")).toBeInTheDocument();
    });

    it("should render warning type", () => {
      render(<Callout type="warning">Warning message</Callout>);
      expect(screen.getByText("Warning message")).toBeInTheDocument();
    });

    it("should render tip type", () => {
      render(<Callout type="tip">Helpful tip</Callout>);
      expect(screen.getByText("Helpful tip")).toBeInTheDocument();
    });

    it("should render info type", () => {
      render(<Callout type="info">Info message</Callout>);
      expect(screen.getByText("Info message")).toBeInTheDocument();
    });

    it("should render check type", () => {
      render(<Callout type="check">Success message</Callout>);
      expect(screen.getByText("Success message")).toBeInTheDocument();
    });
  });

  describe("Shorthand Callouts", () => {
    it("should render Note component", () => {
      render(<Note>Note content</Note>);
      expect(screen.getByText("Note content")).toBeInTheDocument();
    });

    it("should render Warning component", () => {
      render(<Warning>Warning content</Warning>);
      expect(screen.getByText("Warning content")).toBeInTheDocument();
    });

    it("should render Tip component", () => {
      render(<Tip>Tip content</Tip>);
      expect(screen.getByText("Tip content")).toBeInTheDocument();
    });
  });

  describe("Card Component", () => {
    it("should render card with title", () => {
      render(<Card title="Card Title">Card content</Card>);
      expect(screen.getByText("Card Title")).toBeInTheDocument();
      expect(screen.getByText("Card content")).toBeInTheDocument();
    });

    it("should render card without children", () => {
      render(<Card title="Title Only" />);
      expect(screen.getByText("Title Only")).toBeInTheDocument();
    });

    it("should render card with icon", () => {
      render(
        <Card title="Card" icon={<span data-testid="card-icon">📦</span>}>
          Content
        </Card>,
      );
      expect(screen.getByTestId("card-icon")).toBeInTheDocument();
    });

    it("should render as link when href provided", () => {
      render(
        <Card title="Link Card" href="/some-path">
          Clickable
        </Card>,
      );
      const link = screen.getByRole("link");
      expect(link).toHaveAttribute("href", "/some-path");
    });

    it("should not render as link when no href", () => {
      render(<Card title="No Link">Not clickable</Card>);
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
    });
  });

  describe("CardGroup Component", () => {
    it("should render cards in grid", () => {
      render(
        <CardGroup>
          <Card title="Card 1">Content 1</Card>
          <Card title="Card 2">Content 2</Card>
        </CardGroup>,
      );
      expect(screen.getByText("Card 1")).toBeInTheDocument();
      expect(screen.getByText("Card 2")).toBeInTheDocument();
    });

    it("should use custom column count", () => {
      const { container } = render(
        <CardGroup cols={3}>
          <Card title="Card 1">Content</Card>
        </CardGroup>,
      );
      const grid = container.querySelector('[style*="repeat(3"]');
      expect(grid).toBeInTheDocument();
    });
  });

  describe("Tabs Component", () => {
    it("should render first tab content by default", () => {
      render(
        <Tabs>
          <Tab title="First">First content</Tab>
          <Tab title="Second">Second content</Tab>
        </Tabs>,
      );
      expect(screen.getByText("First content")).toBeInTheDocument();
    });

    it("should switch tabs when clicked", () => {
      render(
        <Tabs>
          <Tab title="First">First content</Tab>
          <Tab title="Second">Second content</Tab>
        </Tabs>,
      );
      fireEvent.click(screen.getByText("Second"));
      expect(screen.getByText("Second content")).toBeInTheDocument();
    });

    it("should render tab buttons", () => {
      render(
        <Tabs>
          <Tab title="Tab A">Content A</Tab>
          <Tab title="Tab B">Content B</Tab>
        </Tabs>,
      );
      expect(screen.getByText("Tab A")).toBeInTheDocument();
      expect(screen.getByText("Tab B")).toBeInTheDocument();
    });

    it("should handle empty tabs gracefully", () => {
      render(<Tabs>{null}</Tabs>);
      // Should not crash
      expect(document.body).toBeInTheDocument();
    });
  });

  describe("Steps Component", () => {
    it("should render steps", () => {
      render(
        <Steps>
          <Step title="Step 1">First step content</Step>
          <Step title="Step 2">Second step content</Step>
        </Steps>,
      );
      expect(screen.getByText("Step 1")).toBeInTheDocument();
      expect(screen.getByText("First step content")).toBeInTheDocument();
      expect(screen.getByText("Step 2")).toBeInTheDocument();
    });
  });
});
