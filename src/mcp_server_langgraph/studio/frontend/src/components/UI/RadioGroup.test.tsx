/**
 * RadioGroup Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RadioGroup, Radio } from "./RadioGroup";

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
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          {options.map((opt) => (
            <Radio key={opt.value} value={opt.value} label={opt.label} />
          ))}
        </RadioGroup>,
      );
      expect(screen.getByText("Option 1")).toBeInTheDocument();
      expect(screen.getByText("Option 2")).toBeInTheDocument();
      expect(screen.getByText("Option 3")).toBeInTheDocument();
    });

    it("renders radio inputs with correct name attribute", () => {
      render(
        <RadioGroup name="test-group" value="option1" onChange={() => {}}>
          {options.map((opt) => (
            <Radio key={opt.value} value={opt.value} label={opt.label} />
          ))}
        </RadioGroup>,
      );
      const radios = screen.getAllByRole("radio");
      expect(radios).toHaveLength(3);
      radios.forEach((radio) => {
        expect(radio).toHaveAttribute("name", "test-group");
      });
    });

    it("renders with legend when provided", () => {
      render(
        <RadioGroup
          name="test"
          value="option1"
          onChange={() => {}}
          legend="Select an option"
        >
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      expect(screen.getByText("Select an option")).toBeInTheDocument();
    });

    it("applies custom className", () => {
      render(
        <RadioGroup
          name="test"
          value="option1"
          onChange={() => {}}
          className="custom-class"
        >
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      expect(screen.getByRole("radiogroup")).toHaveClass("custom-class");
    });
  });

  describe("selection", () => {
    it("marks the correct option as checked", () => {
      render(
        <RadioGroup name="test" value="option2" onChange={() => {}}>
          {options.map((opt) => (
            <Radio key={opt.value} value={opt.value} label={opt.label} />
          ))}
        </RadioGroup>,
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
        <RadioGroup name="test" value="option1" onChange={onChange}>
          {options.map((opt) => (
            <Radio key={opt.value} value={opt.value} label={opt.label} />
          ))}
        </RadioGroup>,
      );

      await user.click(screen.getByText("Option 2"));
      expect(onChange).toHaveBeenCalledWith("option2");
    });

    it("can be toggled by clicking the label", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <RadioGroup name="test" value="option1" onChange={onChange}>
          <Radio value="option1" label="Click me" />
          <Radio value="option2" label="Or me" />
        </RadioGroup>,
      );

      await user.click(screen.getByText("Or me"));
      expect(onChange).toHaveBeenCalledWith("option2");
    });
  });

  describe("disabled state", () => {
    it("disables all options when group is disabled", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}} disabled>
          {options.map((opt) => (
            <Radio key={opt.value} value={opt.value} label={opt.label} />
          ))}
        </RadioGroup>,
      );
      const radios = screen.getAllByRole("radio");
      radios.forEach((radio) => {
        expect(radio).toBeDisabled();
      });
    });

    it("disables individual options", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio value="option1" label="Option 1" />
          <Radio value="option2" label="Option 2" disabled />
          <Radio value="option3" label="Option 3" />
        </RadioGroup>,
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
        <RadioGroup name="test" value="option1" onChange={onChange}>
          <Radio value="option1" label="Option 1" />
          <Radio value="option2" label="Option 2" disabled />
        </RadioGroup>,
      );

      await user.click(screen.getByText("Option 2"));
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}} size="sm">
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      const radio = screen.getByRole("radio");
      expect(radio).toHaveClass("h-4");
      expect(radio).toHaveClass("w-4");
    });

    it("renders medium size (default)", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      const radio = screen.getByRole("radio");
      expect(radio).toHaveClass("h-5");
      expect(radio).toHaveClass("w-5");
    });

    it("renders large size", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}} size="lg">
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      const radio = screen.getByRole("radio");
      expect(radio).toHaveClass("h-6");
      expect(radio).toHaveClass("w-6");
    });
  });

  describe("orientation", () => {
    it("renders vertical by default", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio value="option1" label="Option 1" />
          <Radio value="option2" label="Option 2" />
        </RadioGroup>,
      );
      const group = screen.getByRole("radiogroup");
      expect(group).toHaveClass("flex-col");
    });

    it("renders horizontal when specified", () => {
      render(
        <RadioGroup
          name="test"
          value="option1"
          onChange={() => {}}
          orientation="horizontal"
        >
          <Radio value="option1" label="Option 1" />
          <Radio value="option2" label="Option 2" />
        </RadioGroup>,
      );
      const group = screen.getByRole("radiogroup");
      expect(group).toHaveClass("flex-row");
    });
  });

  describe("accessibility", () => {
    it("has role radiogroup", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("is focusable via keyboard", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );
      const radio = screen.getByRole("radio");
      radio.focus();
      expect(radio).toHaveFocus();
    });

    it("supports aria-label on group", () => {
      render(
        <RadioGroup
          name="test"
          value="option1"
          onChange={() => {}}
          aria-label="Choose option"
        >
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
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
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio
            value="option1"
            label="Option 1"
            description="This is the first option"
          />
        </RadioGroup>,
      );
      expect(screen.getByText("This is the first option")).toBeInTheDocument();
    });
  });
});

describe("Radio (standalone)", () => {
  it("renders as a radio input", () => {
    render(
      <RadioGroup name="test" value="" onChange={() => {}}>
        <Radio value="test" label="Test" />
      </RadioGroup>,
    );
    expect(screen.getByRole("radio")).toBeInTheDocument();
  });

  it("renders label", () => {
    render(
      <RadioGroup name="test" value="" onChange={() => {}}>
        <Radio value="test" label="Test Label" />
      </RadioGroup>,
    );
    expect(screen.getByText("Test Label")).toBeInTheDocument();
  });
});

describe("RadioGroup variants", () => {
  describe("card variant", () => {
    it("renders card-style radio options with borders", () => {
      render(
        <RadioGroup
          name="test"
          value="option1"
          onChange={() => {}}
          variant="card"
        >
          <Radio value="option1" label="Option 1" description="First option" />
          <Radio value="option2" label="Option 2" description="Second option" />
        </RadioGroup>,
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
        <RadioGroup
          name="test"
          value="option1"
          onChange={() => {}}
          variant="card"
        >
          <Radio value="option1" label="Option 1" data-testid="radio-1" />
          <Radio value="option2" label="Option 2" data-testid="radio-2" />
        </RadioGroup>,
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
        <RadioGroup
          name="test"
          value="option1"
          onChange={onChange}
          variant="card"
        >
          <Radio value="option1" label="Option 1" />
          <Radio value="option2" label="Option 2" />
        </RadioGroup>,
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
        <RadioGroup
          name="rating"
          value="3"
          onChange={() => {}}
          variant="rating"
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <Radio key={n} value={String(n)} label={String(n)} />
          ))}
        </RadioGroup>,
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
        <RadioGroup
          name="rating"
          value="3"
          onChange={() => {}}
          variant="rating"
        >
          <Radio value="1" label="1" />
        </RadioGroup>,
      );

      // Label should be in flex-col layout below the radio
      const label = screen.getByText("1").closest("label");
      expect(label).toHaveClass("flex-col");
    });

    it("centers items in rating variant", () => {
      render(
        <RadioGroup
          name="rating"
          value="3"
          onChange={() => {}}
          variant="rating"
        >
          <Radio value="1" label="1" />
        </RadioGroup>,
      );

      const label = screen.getByText("1").closest("label");
      expect(label).toHaveClass("items-center");
    });
  });

  describe("default variant", () => {
    it("renders standard layout without variant prop", () => {
      render(
        <RadioGroup name="test" value="option1" onChange={() => {}}>
          <Radio value="option1" label="Option 1" />
        </RadioGroup>,
      );

      // Default should not have card-style borders on label
      const label = screen.getByText("Option 1").closest("label");
      expect(label).not.toHaveClass("border");
    });
  });
});
