/**
 * ConnectedChatInputForm Test Fixtures
 *
 * Shared mock state objects and reset logic for ConnectedChatInputForm shards.
 */
import { vi } from "vitest";

// =============================================================================
// Mock Feature Flag
// =============================================================================
export const mockIsEnabled = vi.fn();

// =============================================================================
// Mock Redux Store (for submitOnEnter selector)
// =============================================================================
export const mockSubmitOnEnter = { current: true };
export const mockDispatch = vi.fn();

// =============================================================================
// Mock useFileUpload hook
// =============================================================================
export const mockSelectFiles = vi.fn();
export const mockRemoveFile = vi.fn();

// UploadedFile structure that ChatInputForm expects
interface MockUploadedFile {
  id: string;
  file: { name: string; size: number; type: string };
  status: "pending" | "uploading" | "complete" | "error";
  progress: number;
  error?: string;
}

export const mockFileUploadReturn = {
  files: [] as MockUploadedFile[],
  isUploading: false,
  isDragging: false,
  error: null as string | null,
  selectFiles: mockSelectFiles,
  removeFile: mockRemoveFile,
  dragHandlers: {
    onDragEnter: vi.fn(),
    onDragLeave: vi.fn(),
    onDragOver: vi.fn(),
    onDrop: vi.fn(),
  },
};

// =============================================================================
// Mock useVoiceInput hook
// =============================================================================
export const mockStartListening = vi.fn();
export const mockStopListening = vi.fn();
export const mockVoiceInputReturn = {
  isListening: false,
  isSupported: true,
  error: null as string | null,
  transcript: "",
  startListening: mockStartListening,
  stopListening: mockStopListening,
};

// =============================================================================
// Mock useKBStatus hook
// =============================================================================
export const mockKBStatusReturn = {
  data: undefined as
    | {
        status: string;
        qdrantConnected: boolean;
        collectionName?: string;
        vectorsCount?: number;
      }
    | undefined,
  isLoading: false,
  isError: false,
  isReady: false,
  kbStatusForUI: undefined as
    | "ready"
    | "misconfigured"
    | "unavailable"
    | undefined,
  refetch: vi.fn(),
};

// =============================================================================
// Mock useUrlContentFetch hook (Sprint 1 - Chat Input Gap Fix)
// =============================================================================
export const mockDetectUrls = vi.fn();
export const mockClearUrl = vi.fn();
export const mockUrlContentFetchReturn = {
  detectedUrls: [] as Array<{ raw: string; url: string }>,
  detectUrls: mockDetectUrls,
  fetchUrl: vi.fn(),
  fetchedContent: [] as Array<{
    url: string;
    title?: string;
    content?: string;
    error?: string;
  }>,
  isLoading: false,
  loadingUrls: [] as string[],
  clearContent: vi.fn(),
  clearUrl: mockClearUrl,
  getContextString: vi.fn().mockReturnValue(""),
};

// =============================================================================
// Mock useInlineSuggestions hook
// =============================================================================
export const mockUseInlineSuggestionsReturn = {
  suggestion: "",
  isLoading: false,
  updateInput: vi.fn(),
  acceptSuggestion: vi.fn(),
  dismissSuggestion: vi.fn(),
};

// =============================================================================
// Mock useAISuggestionsWebSocket hook
// =============================================================================
export const mockUseAISuggestionsWebSocketReturn = {
  status: "disconnected" as const,
  currentSuggestion: null,
  isPending: false,
  requestSuggestion: vi.fn(),
  acceptSuggestion: vi.fn(),
  rejectSuggestion: vi.fn(),
  updateContext: vi.fn(),
  clearSuggestion: vi.fn(),
};

// =============================================================================
// Mock useConnectorSuggestions hook (Phase 5 - Proactive Suggestions)
// =============================================================================
export const mockConnectorSuggestionsReturn = {
  suggestions: [],
  isLoading: false,
  isVisible: false,
  updateInput: vi.fn(),
  dismiss: vi.fn(),
  reset: vi.fn(),
};

// =============================================================================
// Default Props
// =============================================================================
export const defaultProps = {
  value: "",
  onChange: vi.fn(),
  onSubmit: vi.fn(),
};

// =============================================================================
// Reset All Mock States
// =============================================================================
export function resetAllMockStates(): void {
  vi.clearAllMocks();
  // Reset mock states
  mockFileUploadReturn.files = [];
  mockFileUploadReturn.isUploading = false;
  mockFileUploadReturn.isDragging = false;
  mockFileUploadReturn.error = null;
  mockVoiceInputReturn.isListening = false;
  mockVoiceInputReturn.isSupported = true;
  mockVoiceInputReturn.error = null;
  // Reset KB status mock
  mockKBStatusReturn.data = undefined;
  mockKBStatusReturn.isLoading = false;
  mockKBStatusReturn.isError = false;
  mockKBStatusReturn.isReady = false;
  mockKBStatusReturn.kbStatusForUI = undefined;
  // Reset URL content fetch mock (Sprint 1)
  mockUrlContentFetchReturn.detectedUrls = [];
  mockUrlContentFetchReturn.fetchedContent = [];
  mockUrlContentFetchReturn.isLoading = false;
  mockUrlContentFetchReturn.loadingUrls = [];
}
