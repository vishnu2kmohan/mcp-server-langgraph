/**
 * MDXArtifact Tests
 *
 * Tests for MDX content rendering with interactive components.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
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
  mdxComponents,
} from "./MDXArtifact";

describe("MDXArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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

    it("should accept custom components prop", () => {
      const customComponents = {
        CustomButton: () => <button>Custom</button>,
        CustomAlert: () => <div>Alert</div>,
      };
      // Custom components are merged with built-in components for rendering
      // The component renders successfully when custom components are provided
      render(<MDXArtifact data="content" components={customComponents} />);
      expect(screen.getByTestId("mdx-artifact")).toBeInTheDocument();
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

  describe("Extended Components", () => {
    // Access extended components from mdxComponents registry
    const Info = mdxComponents.Info;
    const Check = mdxComponents.Check;
    const CodeGroup = mdxComponents.CodeGroup;
    const Frame = mdxComponents.Frame;
    const Expandable = mdxComponents.Expandable;
    const Icon = mdxComponents.Icon;
    const ResponseField = mdxComponents.ResponseField;
    const ParamField = mdxComponents.ParamField;

    describe("Info Component", () => {
      it("should render info callout", () => {
        render(<Info>Information message</Info>);
        expect(screen.getByText("Information message")).toBeInTheDocument();
      });

      it("should render with title", () => {
        render(<Info title="FYI">Details here</Info>);
        expect(screen.getByText("FYI")).toBeInTheDocument();
        expect(screen.getByText("Details here")).toBeInTheDocument();
      });
    });

    describe("Check Component", () => {
      it("should render check/success callout", () => {
        render(<Check>Task completed successfully!</Check>);
        expect(
          screen.getByText("Task completed successfully!"),
        ).toBeInTheDocument();
      });

      it("should render with title", () => {
        render(<Check title="Done">All tests passed</Check>);
        expect(screen.getByText("Done")).toBeInTheDocument();
        expect(screen.getByText("All tests passed")).toBeInTheDocument();
      });
    });

    describe("CodeGroup Component", () => {
      it("should render code group container", () => {
        render(
          <CodeGroup>
            <pre>python code</pre>
            <pre>javascript code</pre>
          </CodeGroup>,
        );
        expect(screen.getByText("Code Examples")).toBeInTheDocument();
        expect(screen.getByText("python code")).toBeInTheDocument();
        expect(screen.getByText("javascript code")).toBeInTheDocument();
      });
    });

    describe("Frame Component", () => {
      it("should render frame without caption", () => {
        render(
          <Frame>
            <img src="test.png" alt="Test" />
          </Frame>,
        );
        expect(screen.getByRole("img")).toBeInTheDocument();
      });

      it("should render frame with caption", () => {
        render(
          <Frame caption="Example image">
            <img src="test.png" alt="Test" />
          </Frame>,
        );
        expect(screen.getByText("Example image")).toBeInTheDocument();
      });
    });

    describe("Expandable Component", () => {
      it("should render collapsed by default", () => {
        render(
          <Expandable title="Show more">
            <p>Hidden details</p>
          </Expandable>,
        );
        expect(screen.getByText("Show more")).toBeInTheDocument();
        expect(screen.queryByText("Hidden details")).not.toBeInTheDocument();
      });

      it("should expand when clicked", () => {
        render(
          <Expandable title="Show more">
            <p>Hidden details</p>
          </Expandable>,
        );
        fireEvent.click(screen.getByRole("button"));
        expect(screen.getByText("Hidden details")).toBeInTheDocument();
      });

      it("should collapse when clicked again", () => {
        render(
          <Expandable title="Show more">
            <p>Hidden details</p>
          </Expandable>,
        );
        const button = screen.getByRole("button");
        fireEvent.click(button);
        expect(screen.getByText("Hidden details")).toBeInTheDocument();
        fireEvent.click(button);
        expect(screen.queryByText("Hidden details")).not.toBeInTheDocument();
      });
    });

    describe("Icon Component", () => {
      it("should render check icon", () => {
        render(<Icon icon="check" />);
        // Icon should be rendered with aria-label
        expect(screen.getByLabelText("check")).toBeInTheDocument();
      });

      it("should render info icon", () => {
        render(<Icon icon="info" />);
        expect(screen.getByLabelText("info")).toBeInTheDocument();
      });

      it("should render warning icon", () => {
        render(<Icon icon="warning" />);
        expect(screen.getByLabelText("warning")).toBeInTheDocument();
      });

      it("should render lightbulb icon", () => {
        render(<Icon icon="lightbulb" />);
        expect(screen.getByLabelText("lightbulb")).toBeInTheDocument();
      });

      it("should render fallback for unknown icons", () => {
        render(<Icon icon="unknown" />);
        expect(screen.getByLabelText("unknown")).toBeInTheDocument();
      });

      it("should accept size prop", () => {
        render(<Icon icon="check" size={24} />);
        const iconElement = screen.getByLabelText("check");
        expect(iconElement).toHaveStyle({ width: "24px", height: "24px" });
      });
    });

    describe("ResponseField Component", () => {
      it("should render response field with name", () => {
        render(<ResponseField name="id">The unique identifier</ResponseField>);
        expect(screen.getByText("id")).toBeInTheDocument();
        expect(screen.getByText("The unique identifier")).toBeInTheDocument();
      });

      it("should render with type", () => {
        render(
          <ResponseField name="count" type="number">
            The count value
          </ResponseField>,
        );
        expect(screen.getByText("count")).toBeInTheDocument();
        expect(screen.getByText("number")).toBeInTheDocument();
      });

      it("should show required badge when required", () => {
        render(
          <ResponseField name="email" required>
            User email address
          </ResponseField>,
        );
        expect(screen.getByText("required")).toBeInTheDocument();
      });

      it("should render without children", () => {
        render(<ResponseField name="data" type="object" />);
        expect(screen.getByText("data")).toBeInTheDocument();
        expect(screen.getByText("object")).toBeInTheDocument();
      });
    });

    describe("ParamField Component", () => {
      it("should render param field with path parameter", () => {
        render(<ParamField path="user_id">The user ID to fetch</ParamField>);
        expect(screen.getByText("user_id")).toBeInTheDocument();
        expect(screen.getByText("path")).toBeInTheDocument();
        expect(screen.getByText("The user ID to fetch")).toBeInTheDocument();
      });

      it("should render query parameter", () => {
        render(
          <ParamField query="limit" type="integer">
            Maximum results to return
          </ParamField>,
        );
        expect(screen.getByText("limit")).toBeInTheDocument();
        expect(screen.getByText("query")).toBeInTheDocument();
        expect(screen.getByText("integer")).toBeInTheDocument();
      });

      it("should render body parameter", () => {
        render(
          <ParamField body="payload" type="object">
            Request body data
          </ParamField>,
        );
        expect(screen.getByText("payload")).toBeInTheDocument();
        expect(screen.getByText("body")).toBeInTheDocument();
      });

      it("should show required badge when required", () => {
        render(
          <ParamField path="id" required>
            Required parameter
          </ParamField>,
        );
        expect(screen.getByText("required")).toBeInTheDocument();
      });

      it("should render without children", () => {
        render(<ParamField query="page" type="integer" />);
        expect(screen.getByText("page")).toBeInTheDocument();
        expect(screen.getByText("query")).toBeInTheDocument();
      });
    });
  });

  describe("Component Registry", () => {
    it("should export all core components", () => {
      expect(mdxComponents.Accordion).toBeDefined();
      expect(mdxComponents.AccordionGroup).toBeDefined();
      expect(mdxComponents.Callout).toBeDefined();
      expect(mdxComponents.Note).toBeDefined();
      expect(mdxComponents.Warning).toBeDefined();
      expect(mdxComponents.Tip).toBeDefined();
      expect(mdxComponents.Card).toBeDefined();
      expect(mdxComponents.CardGroup).toBeDefined();
      expect(mdxComponents.Tabs).toBeDefined();
      expect(mdxComponents.Tab).toBeDefined();
      expect(mdxComponents.Steps).toBeDefined();
      expect(mdxComponents.Step).toBeDefined();
    });

    it("should export all extended components", () => {
      expect(mdxComponents.Info).toBeDefined();
      expect(mdxComponents.Check).toBeDefined();
      expect(mdxComponents.CodeGroup).toBeDefined();
      expect(mdxComponents.Frame).toBeDefined();
      expect(mdxComponents.Expandable).toBeDefined();
      expect(mdxComponents.Icon).toBeDefined();
      expect(mdxComponents.ResponseField).toBeDefined();
      expect(mdxComponents.ParamField).toBeDefined();
    });

    it("should have 20 total components in registry", () => {
      // Core: Accordion, AccordionGroup, Callout, Note, Warning, Tip, Info, Check, Card, CardGroup, Tabs, Tab, Steps, Step (14)
      // Extended: CodeGroup, Frame, Expandable, Icon, ResponseField, ParamField (6)
      expect(Object.keys(mdxComponents)).toHaveLength(20);
    });
  });
});
