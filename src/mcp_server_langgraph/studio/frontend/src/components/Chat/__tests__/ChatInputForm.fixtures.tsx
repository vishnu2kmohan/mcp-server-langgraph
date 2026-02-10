import { vi } from "vitest";
import type { UploadFile } from "../ChatInputForm";

export const createDefaultProps = () => ({
  input: "",
  onInputChange: vi.fn(),
  onSubmit: vi.fn(),
  isProcessing: false,
  isListening: false,
  isVoiceSupported: true,
  voiceError: null as string | null,
  onStartListening: vi.fn(),
  onStopListening: vi.fn(),
  uploadFiles: [] as UploadFile[],
  isUploading: false,
  isDragging: false,
  fileError: null as string | null,
  onSelectFiles: vi.fn(),
  onRemoveFile: vi.fn(),
  dragHandlers: {},
});
