/**
 * MDX Parser Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 *
 * The MDX parser extracts known components from MDX content
 * and renders them as React elements without full MDX compilation.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { parseMDXContent, extractMDXComponents } from "./mdxParser";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("MDX Parser", () => {
  describe("parseMDXContent", () => {
    it("should parse plain text content", () => {
      const content = "Hello, world!";
      const result = parseMDXContent(content);

      expect(result).toHaveLength(1);
      expect(result[0].type).toBe("text");
      expect(result[0].content).toBe("Hello, world!");
    });

    it("should parse markdown headings", () => {
      const content = "# Welcome\n\nThis is a paragraph.";
      const result = parseMDXContent(content);

      expect(result).toHaveLength(1);
      expect(result[0].type).toBe("text");
      expect(result[0].content).toContain("# Welcome");
    });

    it("should extract Callout component", () => {
      const content = `# Title

<Callout type="tip">
  This is a helpful tip!
</Callout>

More text here.`;

      const result = parseMDXContent(content);

      expect(result.length).toBeGreaterThanOrEqual(2);
      const calloutNode = result.find((n) => n.type === "component");
      expect(calloutNode).toBeDefined();
      expect(calloutNode?.component).toBe("Callout");
      expect(calloutNode?.props?.type).toBe("tip");
    });

    it("should extract Note component (shorthand Callout)", () => {
      const content = `<Note>
  Remember to save your work!
</Note>`;

      const result = parseMDXContent(content);

      const noteNode = result.find(
        (n) => n.type === "component" && n.component === "Note",
      );
      expect(noteNode).toBeDefined();
    });

    it("should extract Warning component", () => {
      const content = `<Warning>
  This action cannot be undone.
</Warning>`;

      const result = parseMDXContent(content);

      const warningNode = result.find(
        (n) => n.type === "component" && n.component === "Warning",
      );
      expect(warningNode).toBeDefined();
    });

    it("should extract Tip component", () => {
      const content = `<Tip>
  Pro tip: Use keyboard shortcuts!
</Tip>`;

      const result = parseMDXContent(content);

      const tipNode = result.find(
        (n) => n.type === "component" && n.component === "Tip",
      );
      expect(tipNode).toBeDefined();
    });

    it("should extract Accordion component", () => {
      const content = `<Accordion title="Click to expand">
  Hidden content here.
</Accordion>`;

      const result = parseMDXContent(content);

      const accordionNode = result.find(
        (n) => n.type === "component" && n.component === "Accordion",
      );
      expect(accordionNode).toBeDefined();
      expect(accordionNode?.props?.title).toBe("Click to expand");
    });

    it("should extract AccordionGroup component", () => {
      const content = `<AccordionGroup>
  <Accordion title="First">Content 1</Accordion>
  <Accordion title="Second">Content 2</Accordion>
</AccordionGroup>`;

      const result = parseMDXContent(content);

      const groupNode = result.find(
        (n) => n.type === "component" && n.component === "AccordionGroup",
      );
      expect(groupNode).toBeDefined();
    });

    it("should extract Card component", () => {
      const content = `<Card title="Feature" icon="star">
  Description of the feature.
</Card>`;

      const result = parseMDXContent(content);

      const cardNode = result.find(
        (n) => n.type === "component" && n.component === "Card",
      );
      expect(cardNode).toBeDefined();
      expect(cardNode?.props?.title).toBe("Feature");
    });

    it("should extract CardGroup component", () => {
      const content = `<CardGroup cols={2}>
  <Card title="Card 1">Content 1</Card>
  <Card title="Card 2">Content 2</Card>
</CardGroup>`;

      const result = parseMDXContent(content);

      const groupNode = result.find(
        (n) => n.type === "component" && n.component === "CardGroup",
      );
      expect(groupNode).toBeDefined();
      expect(groupNode?.props?.cols).toBe(2);
    });

    it("should extract Tabs and Tab components", () => {
      const content = `<Tabs>
  <Tab title="Tab 1">Content 1</Tab>
  <Tab title="Tab 2">Content 2</Tab>
</Tabs>`;

      const result = parseMDXContent(content);

      const tabsNode = result.find(
        (n) => n.type === "component" && n.component === "Tabs",
      );
      expect(tabsNode).toBeDefined();
    });

    it("should extract Steps and Step components", () => {
      const content = `<Steps>
  <Step title="Step 1">Do this first</Step>
  <Step title="Step 2">Then do this</Step>
</Steps>`;

      const result = parseMDXContent(content);

      const stepsNode = result.find(
        (n) => n.type === "component" && n.component === "Steps",
      );
      expect(stepsNode).toBeDefined();
    });

    it("should handle mixed content with text and components", () => {
      const content = `# Getting Started

Welcome to the guide.

<Callout type="info">
  Important information here.
</Callout>

## Next Steps

Continue reading below.

<Tip>
  This is a pro tip!
</Tip>`;

      const result = parseMDXContent(content);

      // Should have multiple nodes
      expect(result.length).toBeGreaterThanOrEqual(3);

      // Should have text nodes
      const textNodes = result.filter((n) => n.type === "text");
      expect(textNodes.length).toBeGreaterThanOrEqual(2);

      // Should have component nodes
      const componentNodes = result.filter((n) => n.type === "component");
      expect(componentNodes.length).toBe(2);
    });

    it("should preserve whitespace in component children", () => {
      const content = `<Callout>
  Line 1
  Line 2
</Callout>`;

      const result = parseMDXContent(content);

      const calloutNode = result.find((n) => n.component === "Callout");
      expect(calloutNode?.children).toContain("Line 1");
      expect(calloutNode?.children).toContain("Line 2");
    });

    it("should handle self-closing components", () => {
      const content = `<Card title="Empty Card" />`;

      const result = parseMDXContent(content);

      const cardNode = result.find((n) => n.component === "Card");
      expect(cardNode).toBeDefined();
      expect(cardNode?.props?.title).toBe("Empty Card");
    });

    it("should parse props with different value types", () => {
      const content = `<CardGroup cols={3}>
  <Card title="Card" href="/path" />
</CardGroup>`;

      const result = parseMDXContent(content);

      const groupNode = result.find((n) => n.component === "CardGroup");
      expect(groupNode?.props?.cols).toBe(3);
    });

    it("should handle boolean props", () => {
      const content = `<Accordion title="Expanded" defaultOpen>
  Content
</Accordion>`;

      const result = parseMDXContent(content);

      const accordionNode = result.find((n) => n.component === "Accordion");
      expect(accordionNode?.props?.defaultOpen).toBe(true);
    });

    it("should ignore unknown components", () => {
      const content = `<UnknownComponent>
  Some content
</UnknownComponent>`;

      const result = parseMDXContent(content);

      // Unknown components should be treated as text
      expect(result.every((n) => n.type === "text")).toBe(true);
    });
  });

  describe("extractMDXComponents", () => {
    it("should return list of known MDX components", () => {
      const components = extractMDXComponents();

      expect(components).toContain("Callout");
      expect(components).toContain("Note");
      expect(components).toContain("Warning");
      expect(components).toContain("Tip");
      expect(components).toContain("Accordion");
      expect(components).toContain("AccordionGroup");
      expect(components).toContain("Card");
      expect(components).toContain("CardGroup");
      expect(components).toContain("Tabs");
      expect(components).toContain("Tab");
      expect(components).toContain("Steps");
      expect(components).toContain("Step");
    });
  });
});

describe("MDX Parser Extended Components", () => {
  it("should extract CodeGroup component", () => {
    const content = `<CodeGroup>
\`\`\`python
print("hello")
\`\`\`

\`\`\`javascript
console.log("hello")
\`\`\`
</CodeGroup>`;

    const result = parseMDXContent(content);

    const codeGroupNode = result.find(
      (n) => n.type === "component" && n.component === "CodeGroup",
    );
    expect(codeGroupNode).toBeDefined();
    expect(codeGroupNode?.children).toContain("python");
  });

  it("should extract Frame component", () => {
    const content = `<Frame caption="My Image">
  <img src="image.png" alt="example" />
</Frame>`;

    const result = parseMDXContent(content);

    const frameNode = result.find(
      (n) => n.type === "component" && n.component === "Frame",
    );
    expect(frameNode).toBeDefined();
    expect(frameNode?.props?.caption).toBe("My Image");
  });

  it("should extract Expandable component", () => {
    const content = `<Expandable title="See more details">
  Hidden content that can be expanded.
</Expandable>`;

    const result = parseMDXContent(content);

    const expandableNode = result.find(
      (n) => n.type === "component" && n.component === "Expandable",
    );
    expect(expandableNode).toBeDefined();
    expect(expandableNode?.props?.title).toBe("See more details");
  });

  it("should extract Icon component (self-closing)", () => {
    const content = `Check out this icon: <Icon icon="check" size={24} />`;

    const result = parseMDXContent(content);

    const iconNode = result.find(
      (n) => n.type === "component" && n.component === "Icon",
    );
    expect(iconNode).toBeDefined();
    expect(iconNode?.props?.icon).toBe("check");
    expect(iconNode?.props?.size).toBe(24);
  });

  it("should extract Info callout variant", () => {
    const content = `<Info>
  Informational message
</Info>`;

    const result = parseMDXContent(content);

    const infoNode = result.find(
      (n) => n.type === "component" && n.component === "Info",
    );
    expect(infoNode).toBeDefined();
  });

  it("should extract Check component", () => {
    const content = `<Check>
  Task completed successfully!
</Check>`;

    const result = parseMDXContent(content);

    const checkNode = result.find(
      (n) => n.type === "component" && n.component === "Check",
    );
    expect(checkNode).toBeDefined();
  });

  it("should extract ResponseField component", () => {
    const content = `<ResponseField name="id" type="string" required>
  The unique identifier
</ResponseField>`;

    const result = parseMDXContent(content);

    const responseFieldNode = result.find(
      (n) => n.type === "component" && n.component === "ResponseField",
    );
    expect(responseFieldNode).toBeDefined();
    expect(responseFieldNode?.props?.name).toBe("id");
    expect(responseFieldNode?.props?.type).toBe("string");
    expect(responseFieldNode?.props?.required).toBe(true);
  });

  it("should extract ParamField component", () => {
    const content = `<ParamField path="user_id" type="string" required>
  The user ID to fetch
</ParamField>`;

    const result = parseMDXContent(content);

    const paramFieldNode = result.find(
      (n) => n.type === "component" && n.component === "ParamField",
    );
    expect(paramFieldNode).toBeDefined();
    expect(paramFieldNode?.props?.path).toBe("user_id");
  });
});

describe("MDX Parser Edge Cases", () => {
  it("should handle empty content", () => {
    const result = parseMDXContent("");
    expect(result).toHaveLength(0);
  });

  it("should handle whitespace-only content", () => {
    const result = parseMDXContent("   \n\n   ");
    expect(result).toHaveLength(0);
  });

  it("should handle nested components", () => {
    const content = `<AccordionGroup>
  <Accordion title="Section 1">
    <Callout type="info">
      Nested callout
    </Callout>
  </Accordion>
</AccordionGroup>`;

    const result = parseMDXContent(content);

    const groupNode = result.find((n) => n.component === "AccordionGroup");
    expect(groupNode).toBeDefined();
    // Children should contain the nested structure
    expect(groupNode?.children).toContain("Accordion");
  });

  it("should handle components with code blocks inside", () => {
    const content = `<Callout>
  Use the following code:
  \`\`\`python
  print("Hello")
  \`\`\`
</Callout>`;

    const result = parseMDXContent(content);

    const calloutNode = result.find((n) => n.component === "Callout");
    expect(calloutNode).toBeDefined();
    expect(calloutNode?.children).toContain("python");
  });

  it("should handle multiline prop values", () => {
    const content = `<Callout
  type="warning"
  title="Important">
  Content here
</Callout>`;

    const result = parseMDXContent(content);

    const calloutNode = result.find((n) => n.component === "Callout");
    expect(calloutNode?.props?.type).toBe("warning");
    expect(calloutNode?.props?.title).toBe("Important");
  });
});
