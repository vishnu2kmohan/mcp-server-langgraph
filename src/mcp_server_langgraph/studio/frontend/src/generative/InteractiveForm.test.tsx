/**
 * InteractiveForm Tests - Phase 2
 *
 * Tests for AI-generated interactive forms.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { InteractiveForm, type FormConfig } from "./InteractiveForm";

import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const mockFormConfig: FormConfig = {
  id: "form-1",
  title: "User Registration",
  fields: [
    {
      id: "name",
      type: "text",
      label: "Full Name",
      placeholder: "Enter your name",
      required: true,
    },
    {
      id: "email",
      type: "email",
      label: "Email Address",
      placeholder: "you@example.com",
      required: true,
    },
    {
      id: "role",
      type: "select",
      label: "Role",
      options: ["Developer", "Designer", "Manager"],
      required: false,
    },
    {
      id: "subscribe",
      type: "checkbox",
      label: "Subscribe to newsletter",
      required: false,
    },
  ],
  submitLabel: "Register",
};

// =============================================================================
// Tests
// =============================================================================

describe("InteractiveForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render form container", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByTestId("interactive-form")).toBeInTheDocument();
    });

    it("should display form title", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByText("User Registration")).toBeInTheDocument();
    });

    it("should render all form fields", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/Full Name/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Email Address/)).toBeInTheDocument();
      expect(screen.getByLabelText(/Role/)).toBeInTheDocument();
      expect(
        screen.getByLabelText(/Subscribe to newsletter/),
      ).toBeInTheDocument();
    });

    it("should show submit button with custom label", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: "Register" }),
      ).toBeInTheDocument();
    });
  });

  describe("Field Types", () => {
    it("should render text input field", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const nameInput = screen.getByPlaceholderText("Enter your name");
      expect(nameInput).toHaveAttribute("type", "text");
    });

    it("should render email input field", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const emailInput = screen.getByPlaceholderText("you@example.com");
      expect(emailInput).toHaveAttribute("type", "email");
    });

    it("should render select field with options", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const select = screen.getByLabelText(/Role/);
      expect(select.tagName).toBe("SELECT");
      expect(screen.getByText("Developer")).toBeInTheDocument();
      expect(screen.getByText("Designer")).toBeInTheDocument();
      expect(screen.getByText("Manager")).toBeInTheDocument();
    });

    it("should render checkbox field", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const checkbox = screen.getByLabelText(/Subscribe to newsletter/);
      expect(checkbox).toHaveAttribute("type", "checkbox");
    });
  });

  describe("Validation", () => {
    it("should mark required fields", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const nameInput = screen.getByLabelText(/Full Name/);
      expect(nameInput).toHaveAttribute("aria-required", "true");
    });

    it("should show validation error for empty required field on submit", async () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: "Register" }));
      await waitFor(() => {
        expect(screen.getByTestId("error-name")).toBeInTheDocument();
      });
    });
  });

  describe("Submission", () => {
    it("should call onSubmit with form data", async () => {
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={onSubmit} />
        </TestProvider>,
      );

      await userEvent.type(
        screen.getByPlaceholderText("Enter your name"),
        "Alice",
      );
      await userEvent.type(
        screen.getByPlaceholderText("you@example.com"),
        "alice@example.com",
      );
      fireEvent.click(screen.getByRole("button", { name: "Register" }));

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith({
          name: "Alice",
          email: "alice@example.com",
          role: "",
          subscribe: false,
        });
      });
    });

    it("should disable submit button when isSubmitting", () => {
      render(
        <TestProvider>
          <InteractiveForm
            config={mockFormConfig}
            onSubmit={() => {}}
            isSubmitting
          />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: "Register" })).toBeDisabled();
    });

    it("should show loading spinner when isSubmitting", () => {
      render(
        <TestProvider>
          <InteractiveForm
            config={mockFormConfig}
            onSubmit={() => {}}
            isSubmitting
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("submit-spinner")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when submitting", async () => {
      const { container } = render(
        <TestProvider>
          <InteractiveForm
            config={mockFormConfig}
            onSubmit={() => {}}
            isSubmitting
          />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have form role", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("form")).toBeInTheDocument();
    });

    it("should associate labels with inputs", () => {
      render(
        <TestProvider>
          <InteractiveForm config={mockFormConfig} onSubmit={() => {}} />
        </TestProvider>,
      );
      const nameInput = screen.getByLabelText(/Full Name/);
      expect(nameInput).toHaveAttribute("id");
    });
  });
});
