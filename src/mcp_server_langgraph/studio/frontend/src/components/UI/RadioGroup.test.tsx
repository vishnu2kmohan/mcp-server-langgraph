/**
 * RadioGroup Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RadioGroup, Radio } from "./RadioGroup";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("RadioGroup", () => {
  const options = [
    { value: "option1", label: "Option 1" },
    { value: "option2", label: "Option 2" },
    { value: "option3", label: "Option 3" },
  ];

  describe("rendering", () => {
    it("renders all options", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            {options.map((opt) => (
              <Radio key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </RadioGroup>
        </TestProvider>,
      );
      expect(screen.getByText("Option 1")).toBeInTheDocument();
      expect(screen.getByText("Option 2")).toBeInTheDocument();
      expect(screen.getByText("Option 3")).toBeInTheDocument();
    });

    it("renders radio inputs with correct name attribute", () => {
      render(
        <TestProvider>
          <RadioGroup name="test-group" value="option1" onChange={() => {}}>
            {options.map((opt) => (
              <Radio key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </RadioGroup>
        </TestProvider>,
      );
      const radios = screen.getAllByRole("radio");
      expect(radios).toHaveLength(3);
      radios.forEach((radio) => {
        expect(radio).toHaveAttribute("name", "test-group");
      });
    });

    it("renders with legend when provided", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={() => {}}
            legend="Select an option"
          >
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      expect(screen.getByText("Select an option")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={() => {}}
            className="custom-class"
          >
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      expect(screen.getByRole("radiogroup")).toHaveClass("custom-class");
    });
  });

  describe("selection", () => {
    it("marks the correct option as checked", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option2" onChange={() => {}}>
            {options.map((opt) => (
              <Radio key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </RadioGroup>
        </TestProvider>,
      );
      const radios = screen.getAllByRole("radio");
      expect(radios[0]).not.toBeChecked();
      expect(radios[1]).toBeChecked();
      expect(radios[2]).not.toBeChecked();
    });

    it("calls onChange when option is selected", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={onChange}>
            {options.map((opt) => (
              <Radio key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </RadioGroup>
        </TestProvider>,
      );

      await user.click(screen.getByText("Option 2"));
      expect(onChange).toHaveBeenCalledWith("option2");
    });

    it("can be toggled by clicking the label", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={onChange}>
            <Radio value="option1" label="Click me" />
            <Radio value="option2" label="Or me" />
          </RadioGroup>
        </TestProvider>,
      );

      await user.click(screen.getByText("Or me"));
      expect(onChange).toHaveBeenCalledWith("option2");
    });
  });

  describe("disabled state", () => {
    it("disables all options when group is disabled", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}} disabled>
            {options.map((opt) => (
              <Radio key={opt.value} value={opt.value} label={opt.label} />
            ))}
          </RadioGroup>
        </TestProvider>,
      );
      const radios = screen.getAllByRole("radio");
      radios.forEach((radio) => {
        expect(radio).toBeDisabled();
      });
    });

    it("disables individual options", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio value="option1" label="Option 1" />
            <Radio value="option2" label="Option 2" disabled />
            <Radio value="option3" label="Option 3" />
          </RadioGroup>
        </TestProvider>,
      );
      const radios = screen.getAllByRole("radio");
      expect(radios[0]).not.toBeDisabled();
      expect(radios[1]).toBeDisabled();
      expect(radios[2]).not.toBeDisabled();
    });

    it("does not call onChange when disabled option is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={onChange}>
            <Radio value="option1" label="Option 1" />
            <Radio value="option2" label="Option 2" disabled />
          </RadioGroup>
        </TestProvider>,
      );

      await user.click(screen.getByText("Option 2"));
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}} size="sm">
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      const radio = screen.getByRole("radio");
      expect(radio).toHaveClass("h-4");
      expect(radio).toHaveClass("w-4");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      const radio = screen.getByRole("radio");
      expect(radio).toHaveClass("h-5");
      expect(radio).toHaveClass("w-5");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}} size="lg">
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      const radio = screen.getByRole("radio");
      expect(radio).toHaveClass("h-6");
      expect(radio).toHaveClass("w-6");
    });
  });

  describe("orientation", () => {
    it("renders vertical by default", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio value="option1" label="Option 1" />
            <Radio value="option2" label="Option 2" />
          </RadioGroup>
        </TestProvider>,
      );
      const group = screen.getByRole("radiogroup");
      expect(group).toHaveClass("flex-col");
    });

    it("renders horizontal when specified", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={() => {}}
            orientation="horizontal"
          >
            <Radio value="option1" label="Option 1" />
            <Radio value="option2" label="Option 2" />
          </RadioGroup>
        </TestProvider>,
      );
      const group = screen.getByRole("radiogroup");
      expect(group).toHaveClass("flex-row");
    });
  });

  describe("accessibility", () => {
    it("has role radiogroup", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("is focusable via keyboard", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      const radio = screen.getByRole("radio");
      radio.focus();
      expect(radio).toHaveFocus();
    });

    it("supports aria-label on group", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={() => {}}
            aria-label="Choose option"
          >
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );
      expect(screen.getByRole("radiogroup")).toHaveAttribute(
        "aria-label",
        "Choose option",
      );
    });
  });

  describe("Radio with description", () => {
    it("renders description when provided", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio
              value="option1"
              label="Option 1"
              description="This is the first option"
            />
          </RadioGroup>
        </TestProvider>,
      );
      expect(screen.getByText("This is the first option")).toBeInTheDocument();
    });
  });
});

describe("Radio (standalone)", () => {
  it("renders as a radio input", () => {
    render(
      <TestProvider>
        <RadioGroup name="test" value="" onChange={() => {}}>
          <Radio value="test" label="Test" />
        </RadioGroup>
      </TestProvider>,
    );
    expect(screen.getByRole("radio")).toBeInTheDocument();
  });

  it("renders label", () => {
    render(
      <TestProvider>
        <RadioGroup name="test" value="" onChange={() => {}}>
          <Radio value="test" label="Test Label" />
        </RadioGroup>
      </TestProvider>,
    );
    expect(screen.getByText("Test Label")).toBeInTheDocument();
  });
});

describe("RadioGroup variants", () => {
  describe("card variant", () => {
    it("renders card-style radio options with borders", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={() => {}}
            variant="card"
          >
            <Radio
              value="option1"
              label="Option 1"
              description="First option"
            />
            <Radio
              value="option2"
              label="Option 2"
              description="Second option"
            />
          </RadioGroup>
        </TestProvider>,
      );

      // Check that card wrapper elements exist (labels should have border classes)
      const labels = screen
        .getAllByText(/Option/)
        .map((el) => el.closest("label"));
      expect(labels[0]).toHaveClass("border");
      expect(labels[0]).toHaveClass("rounded-lg");
    });

    it("highlights selected card with primary border", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={() => {}}
            variant="card"
          >
            <Radio value="option1" label="Option 1" data-testid="radio-1" />
            <Radio value="option2" label="Option 2" data-testid="radio-2" />
          </RadioGroup>
        </TestProvider>,
      );

      const selectedLabel = screen.getByText("Option 1").closest("label");
      const unselectedLabel = screen.getByText("Option 2").closest("label");

      expect(selectedLabel).toHaveClass("border-primary-9");
      expect(unselectedLabel).not.toHaveClass("border-primary-9");
    });

    it("updates highlighting when selection changes", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      const { rerender } = render(
        <TestProvider>
          <RadioGroup
            name="test"
            value="option1"
            onChange={onChange}
            variant="card"
          >
            <Radio value="option1" label="Option 1" />
            <Radio value="option2" label="Option 2" />
          </RadioGroup>
        </TestProvider>,
      );

      await user.click(screen.getByText("Option 2"));
      expect(onChange).toHaveBeenCalledWith("option2");

      // Simulate parent updating value after onChange
      rerender(
        <RadioGroup
          name="test"
          value="option2"
          onChange={onChange}
          variant="card"
        >
          <Radio value="option1" label="Option 1" />
          <Radio value="option2" label="Option 2" />
        </RadioGroup>,
      );

      const option2Label = screen.getByText("Option 2").closest("label");
      expect(option2Label).toHaveClass("border-primary-9");
    });
  });

  describe("rating variant", () => {
    it("renders compact horizontal rating scale", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="rating"
            value="3"
            onChange={() => {}}
            variant="rating"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <Radio key={n} value={String(n)} label={String(n)} />
            ))}
          </RadioGroup>
        </TestProvider>,
      );

      // Rating should be horizontal
      const group = screen.getByRole("radiogroup");
      expect(group).toHaveClass("flex-row");

      // All numbers should be visible
      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
    });

    it("shows label below radio in rating variant", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="rating"
            value="3"
            onChange={() => {}}
            variant="rating"
          >
            <Radio value="1" label="1" />
          </RadioGroup>
        </TestProvider>,
      );

      // Label should be in flex-col layout below the radio
      const label = screen.getByText("1").closest("label");
      expect(label).toHaveClass("flex-col");
    });

    it("centers items in rating variant", () => {
      render(
        <TestProvider>
          <RadioGroup
            name="rating"
            value="3"
            onChange={() => {}}
            variant="rating"
          >
            <Radio value="1" label="1" />
          </RadioGroup>
        </TestProvider>,
      );

      const label = screen.getByText("1").closest("label");
      expect(label).toHaveClass("items-center");
    });
  });

  describe("default variant", () => {
    it("renders standard layout without variant prop", () => {
      render(
        <TestProvider>
          <RadioGroup name="test" value="option1" onChange={() => {}}>
            <Radio value="option1" label="Option 1" />
          </RadioGroup>
        </TestProvider>,
      );

      // Default should not have card-style borders on label
      const label = screen.getByText("Option 1").closest("label");
      expect(label).not.toHaveClass("border");
    });
  });
});
