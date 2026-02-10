import { vi } from "vitest";
import type { ChatInputProps } from "../ChatInput";

export const createMockProps = (
  overrides: Partial<ChatInputProps> = {},
): ChatInputProps => ({
  value: "",
  onChange: vi.fn(),
  onSubmit: vi.fn(),
  disabled: false,
  ...overrides,
});
