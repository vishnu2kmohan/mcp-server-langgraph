import { vi } from "vitest";

export const mockOnSubmit = vi.fn();
export const mockOnChange = vi.fn();

export const createMocks = () => ({
  onSubmit: vi.fn(),
  onChange: vi.fn(),
});
