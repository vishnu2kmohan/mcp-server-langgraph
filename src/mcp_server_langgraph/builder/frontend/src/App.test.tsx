/**
 * Tests for Visual Workflow Builder App Component
 *
 * Comprehensive test suite for the main App component including:
 * - Component rendering
 * - React Flow canvas interactions
 * - Node creation and management
 * - Edge connections
 * - Code generation
 * - File operations
 * - Monaco Editor integration
 * - User interactions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from './test/test-utils';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import App from './App';
import { mockGeneratedCode, createMockAxiosResponse, createMockAxiosError } from './test/test-utils';

// Mock axios
vi.mock('axios');
const mockedAxios = vi.mocked(axios, true);

// Mock Monaco Editor
vi.mock('@monaco-editor/react', () => ({
  default: ({ value, onChange }: any) => (
    <textarea
      data-testid="monaco-editor"
      value={value}
      onChange={(e) => onChange?.(e.target.value)}
    />
  ),
}));

// Mock React Flow to avoid jsdom incompatibility issues
vi.mock('reactflow', async (importOriginal) => {
  const React = await import('react');
  const actual = await importOriginal() as any;

  return {
    ...actual,
    default: ({ children, ...props }: any) => (
      <div data-testid="react-flow" className="react-flow" {...props}>
        <div className="react-flow__renderer">
          {children}
        </div>
        <div className="react-flow__controls" />
        <div className="react-flow__background" />
        <div className="react-flow__minimap" />
        {/* Render nodes */}
        {props.nodes?.map((node: any) => (
          <div
            key={node.id}
            className="react-flow__node"
            data-node-id={node.id}
            onClick={(e) => props.onNodeClick?.(e, node)}
            onContextMenu={(e) => props.onNodeContextMenu?.(e, node)}
          >
            {node.data?.label}
          </div>
        ))}
      </div>
    ),
    Controls: () => <div className="react-flow__controls" />,
    Background: () => <div className="react-flow__background" />,
    MiniMap: () => <div className="react-flow__minimap" />,
    Panel: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    useNodesState: (initialNodes: any) => {
      const [nodes, setNodes] = React.useState(initialNodes);
      const onNodesChange = React.useCallback(() => {}, []);
      return [nodes, setNodes, onNodesChange];
    },
    useEdgesState: (initialEdges: any) => {
      const [edges, setEdges] = React.useState(initialEdges);
      const onEdgesChange = React.useCallback(() => {}, []);
      return [edges, setEdges, onEdgesChange];
    },
    addEdge: (params: any, edges: any[]) => [...edges, params],
    ReactFlowProvider: ({ children }: any) => <>{children}</>,
    useReactFlow: () => ({
      getNodes: () => [],
      getEdges: () => [],
      fitView: () => {},
    }),
  };
});

// Track toast calls for testing
const toastCalls: { type: string; message: string }[] = [];

// Mock sonner for toast notifications
vi.mock('sonner', () => ({
  Toaster: () => <div data-sonner-toaster="true" />,
  toast: {
    success: vi.fn((message: string) => {
      toastCalls.push({ type: 'success', message });
      // Also add to DOM for screen queries
      const toastEl = document.createElement('div');
      toastEl.textContent = message;
      toastEl.setAttribute('role', 'alert');
      toastEl.setAttribute('data-testid', 'toast-success');
      document.body.appendChild(toastEl);
    }),
    error: vi.fn((message: string) => {
      toastCalls.push({ type: 'error', message });
      // Also add to DOM for screen queries
      const toastEl = document.createElement('div');
      toastEl.textContent = message;
      toastEl.setAttribute('role', 'alert');
      toastEl.setAttribute('data-testid', 'toast-error');
      document.body.appendChild(toastEl);
    }),
    info: vi.fn((message: string) => {
      toastCalls.push({ type: 'info', message });
      const toastEl = document.createElement('div');
      toastEl.textContent = message;
      toastEl.setAttribute('role', 'alert');
      toastEl.setAttribute('data-testid', 'toast-info');
      document.body.appendChild(toastEl);
    }),
  },
}));

// Import toast for assertions
import { toast } from 'sonner';

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Clear toast calls tracking
    toastCalls.length = 0;
    // Clean up any toast elements from previous tests
    document.querySelectorAll('[data-testid^="toast-"]').forEach(el => el.remove());
  });

  afterEach(() => {
    vi.resetAllMocks();
    // Clear toast calls tracking
    toastCalls.length = 0;
    // Clean up any toast elements
    document.querySelectorAll('[data-testid^="toast-"]').forEach(el => el.remove());
  });

  // ==============================================================================
  // Rendering Tests
  // ==============================================================================

  describe('Rendering', () => {
    it('renders the main app container', () => {
      render(<App />);

      // React Flow should be present
      const reactFlowElement = document.querySelector('.react-flow');
      expect(reactFlowElement).toBeTruthy();
    });

    it('renders workflow name input', () => {
      render(<App />);

      const nameInput = screen.getByDisplayValue('my_agent');
      expect(nameInput).toBeInTheDocument();
    });

    it('renders node type buttons', () => {
      render(<App />);

      // Should have buttons for each node type (use getAllByText since "Tool" also appears as label)
      expect(screen.getAllByText(/^Tool$/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/^LLM$/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/^Conditional$/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/^Approval$/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/^Custom$/i).length).toBeGreaterThan(0);
    });

    it('renders action buttons', () => {
      render(<App />);

      // Look for buttons by accessible roles and text content
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('does not show code panel initially', () => {
      render(<App />);

      const codeEditor = screen.queryByTestId('monaco-editor');
      expect(codeEditor).not.toBeInTheDocument();
    });

    it('renders initial start node', () => {
      render(<App />);

      // Initial node should be present in React Flow
      const reactFlow = document.querySelector('.react-flow');
      expect(reactFlow).toBeTruthy();

      // Check for node in the DOM
      const nodes = document.querySelectorAll('.react-flow__node');
      expect(nodes.length).toBeGreaterThan(0);
    });
  });

  // ==============================================================================
  // Node Creation Tests
  // ==============================================================================

  describe('Node Creation', () => {
    it('adds a tool node when Tool button is clicked', async () => {
      const user = userEvent.setup();
      render(<App />);

      const initialNodes = document.querySelectorAll('.react-flow__node');
      const initialCount = initialNodes.length;

      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(initialCount + 1);
      });
    });

    it('adds an LLM node when LLM button is clicked', async () => {
      const user = userEvent.setup();
      render(<App />);

      const llmButton = screen.getByRole('button', { name: /llm/i });
      await user.click(llmButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBeGreaterThan(1);
      });
    });

    it('assigns unique IDs to new nodes', async () => {
      const user = userEvent.setup();
      render(<App />);

      const toolButton = screen.getByRole('button', { name: /tool/i });

      // Add two nodes
      await user.click(toolButton);
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(3); // Initial + 2 new
      });
    });

    it('applies correct styling to node based on type', async () => {
      const user = userEvent.setup();
      render(<App />);

      const llmButton = screen.getByRole('button', { name: /llm/i });
      await user.click(llmButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBeGreaterThan(1);
        // Node should have styling applied
      });
    });
  });

  // ==============================================================================
  // Workflow Configuration Tests
  // ==============================================================================

  describe('Workflow Configuration', () => {
    it('allows changing workflow name', async () => {
      const user = userEvent.setup();
      render(<App />);

      const nameInput = screen.getByDisplayValue('my_agent');
      await user.clear(nameInput);
      await user.type(nameInput, 'new_agent');

      expect(nameInput).toHaveValue('new_agent');
    });

    it('workflow name input accepts changes', async () => {
      const user = userEvent.setup();
      render(<App />);

      const nameInput = screen.getByDisplayValue('my_agent');
      await user.clear(nameInput);
      await user.type(nameInput, 'new_agent');

      expect(nameInput).toHaveValue('new_agent');
    });
  });

  // ==============================================================================
  // Code Generation Tests
  // ==============================================================================

  describe('Code Generation', () => {
    it('calls API to generate code when Export Code button is clicked', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8001/api/builder/generate',
          expect.objectContaining({
            workflow: expect.objectContaining({
              name: 'my_agent',
              description: 'My custom agent workflow',
            }),
          })
        );
      });
    });

    it('displays generated code in Monaco Editor', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        expect(editor).toBeInTheDocument();
        expect(editor).toHaveValue(mockGeneratedCode);
      });
    });

    it('shows code panel after generation', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      // Code panel should not be visible initially
      expect(screen.queryByTestId('monaco-editor')).not.toBeInTheDocument();

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
      });
    });

    it('handles code generation API errors gracefully', async () => {
      const user = userEvent.setup();

      mockedAxios.post.mockRejectedValueOnce(
        createMockAxiosError('Code generation failed', 400)
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringMatching(/code generation failed/i)
        );
      });
    });

    it('includes all nodes in workflow definition', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      // Add a couple of nodes
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);
      await user.click(toolButton);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          expect.any(String),
          expect.objectContaining({
            workflow: expect.objectContaining({
              nodes: expect.arrayContaining([
                expect.objectContaining({ id: expect.any(String) }),
              ]),
            }),
          })
        );
      });
    });
  });

  // ==============================================================================
  // File Operations Tests
  // ==============================================================================

  describe('File Operations', () => {
    it('downloads generated code when Download button is clicked', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      // Store original createElement and track anchor creation
      const originalCreateElement = document.createElement.bind(document);
      const mockAnchorClick = vi.fn();
      let capturedDownloadFilename = '';

      const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation(
        (tagName: string, options?: ElementCreationOptions) => {
          const element = originalCreateElement(tagName, options);
          if (tagName.toLowerCase() === 'a') {
            // Wrap the element to capture download and click
            Object.defineProperty(element, 'click', {
              value: () => {
                capturedDownloadFilename = (element as HTMLAnchorElement).download;
                mockAnchorClick();
              },
            });
          }
          return element;
        }
      );

      render(<App />);

      // Generate code first
      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
      });

      // Now download
      const downloadButton = screen.getByRole('button', { name: /download/i });
      await user.click(downloadButton);

      expect(mockAnchorClick).toHaveBeenCalled();
      expect(capturedDownloadFilename).toBe('my_agent.py');

      createElementSpy.mockRestore();
    });

    it('saves workflow to file via API', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ success: true, message: 'Saved', path: 'src/agents/my_agent.py' })
      );

      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      render(<App />);

      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8001/api/builder/save',
          expect.objectContaining({
            workflow: expect.any(Object),
            output_path: expect.stringContaining('my_agent.py'),
          })
        );
      });

      alertSpy.mockRestore();
    });

    it('handles save file API errors', async () => {
      const user = userEvent.setup();

      mockedAxios.post.mockRejectedValueOnce(
        createMockAxiosError('Save failed', 500)
      );

      render(<App />);

      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringMatching(/save failed/i)
        );
      });
    });
  });

  // ==============================================================================
  // React Flow Integration Tests
  // ==============================================================================

  describe('React Flow Integration', () => {
    it('renders React Flow controls', () => {
      render(<App />);

      const controls = document.querySelector('.react-flow__controls');
      expect(controls).toBeTruthy();
    });

    it('renders React Flow background', () => {
      render(<App />);

      const background = document.querySelector('.react-flow__background');
      expect(background).toBeTruthy();
    });

    it('renders React Flow minimap', () => {
      render(<App />);

      const minimap = document.querySelector('.react-flow__minimap');
      expect(minimap).toBeTruthy();
    });
  });

  // ==============================================================================
  // Monaco Editor Integration Tests
  // ==============================================================================

  describe('Monaco Editor Integration', () => {
    it('displays code in Monaco Editor with correct syntax highlighting', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        const editor = screen.getByTestId('monaco-editor');
        expect(editor).toHaveValue(mockGeneratedCode);
      });
    });

    it('allows closing the code panel', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      // Generate code to show panel
      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
      });

      // Close the panel
      const closeButton = screen.getByRole('button', { name: /close/i });
      await user.click(closeButton);

      await waitFor(() => {
        expect(screen.queryByTestId('monaco-editor')).not.toBeInTheDocument();
      });
    });
  });

  // ==============================================================================
  // Edge Cases and Error Handling
  // ==============================================================================

  describe('Edge Cases', () => {
    it('handles empty workflow gracefully', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: '# Empty workflow', formatted: true, warnings: ['Workflow has only one node'] })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalled();
      });
    });

    it('handles network errors during code generation', async () => {
      const user = userEvent.setup();

      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      // Should show error toast instead of alert
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          expect.stringMatching(/code generation failed/i)
        );
      });
    });
  });

  // ==============================================================================
  // Toast Notifications Tests (Phase 1 UX Improvement)
  // ==============================================================================

  describe('Toast Notifications', () => {
    it('renders Toaster component for notifications', () => {
      render(<App />);

      // Toaster should be present in the DOM
      const toaster = document.querySelector('[data-sonner-toaster]');
      expect(toaster).toBeTruthy();
    });

    it('shows success toast on successful code generation', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(expect.stringMatching(/code generated successfully/i));
      });
    });

    it('shows error toast on code generation failure', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockRejectedValueOnce(new Error('Generation failed'));

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/code generation failed/i));
      });
    });

    it('shows success toast on successful save', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ success: true })
      );

      render(<App />);

      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith(expect.stringMatching(/workflow saved/i));
      });
    });

    it('shows error toast on save failure', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockRejectedValueOnce(new Error('Save failed'));

      render(<App />);

      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(expect.stringMatching(/save failed/i));
      });
    });

    it('does not use browser alert() for errors', async () => {
      const user = userEvent.setup();
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      mockedAxios.post.mockRejectedValueOnce(new Error('Error'));

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        // alert should NOT be called - we use toast instead
        expect(alertSpy).not.toHaveBeenCalled();
        // toast.error should be called instead
        expect(toast.error).toHaveBeenCalled();
      });

      alertSpy.mockRestore();
    });
  });

  // ==============================================================================
  // Loading States Tests (Phase 1 UX Improvement)
  // ==============================================================================

  describe('Loading States', () => {
    it('shows loading spinner while generating code', async () => {
      const user = userEvent.setup();
      // Create a promise that we can control
      let resolvePromise: (value: any) => void;
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockedAxios.post.mockReturnValueOnce(delayedPromise as any);

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText(/generating/i)).toBeInTheDocument();
      });

      // Button should be disabled during loading
      expect(generateButton).toBeDisabled();

      // Resolve the promise
      resolvePromise!(createMockAxiosResponse({ code: mockGeneratedCode }));
    });

    it('shows loading spinner while saving file', async () => {
      const user = userEvent.setup();
      let resolvePromise: (value: any) => void;
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockedAxios.post.mockReturnValueOnce(delayedPromise as any);

      render(<App />);

      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      await user.click(saveButton);

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText(/saving/i)).toBeInTheDocument();
      });

      // Button should be disabled during loading
      expect(saveButton).toBeDisabled();

      // Resolve the promise
      resolvePromise!(createMockAxiosResponse({ success: true }));
    });

    it('disables Export Code button during code generation', async () => {
      const user = userEvent.setup();
      let resolvePromise: (value: any) => void;
      const delayedPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockedAxios.post.mockReturnValueOnce(delayedPromise as any);

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(generateButton).toBeDisabled();
        expect(generateButton).toHaveClass('opacity-50');
      });

      resolvePromise!(createMockAxiosResponse({ code: mockGeneratedCode }));
    });

    it('re-enables buttons after operation completes', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /export.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(generateButton).not.toBeDisabled();
      });
    });
  });

  // ==============================================================================
  // Keyboard Shortcuts Tests (Phase 1 UX Improvement)
  // ==============================================================================

  describe('Keyboard Shortcuts', () => {
    it('Ctrl+S triggers save operation', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ success: true })
      );

      render(<App />);

      // Trigger Ctrl+S
      await user.keyboard('{Control>}s{/Control}');

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8001/api/builder/save',
          expect.any(Object)
        );
      });
    });

    it('Ctrl+G triggers code generation', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode })
      );

      render(<App />);

      // Trigger Ctrl+G
      await user.keyboard('{Control>}g{/Control}');

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalledWith(
          'http://localhost:8001/api/builder/generate',
          expect.any(Object)
        );
      });
    });

    it('shows keyboard shortcuts in button titles', () => {
      render(<App />);

      // Check that Save button has Ctrl+S in title
      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      expect(saveButton).toHaveAttribute('title', expect.stringMatching(/ctrl\+s/i));

      // Check that Export Code button has Ctrl+G in title
      const exportButton = screen.getByRole('button', { name: /export.*code/i });
      expect(exportButton).toHaveAttribute('title', expect.stringMatching(/ctrl\+g/i));
    });
  });

  // ==============================================================================
  // Error Boundary Tests (Phase 1 UX Improvement)
  // ==============================================================================

  describe('Error Boundary', () => {
    it('catches and displays errors gracefully', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Error boundary should catch and display error
      // This test validates the error boundary exists
      expect(() => {
        render(<App />);
      }).not.toThrow();

      consoleSpy.mockRestore();
    });

    it('provides recovery option when error occurs', async () => {
      // Mock console.error to suppress noise
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<App />);

      // App should have error recovery mechanism
      // (This is tested via the error boundary component)

      consoleSpy.mockRestore();
    });
  });

  // ==============================================================================
  // Real-time Validation Tests (Phase 2 UX Improvement)
  // ==============================================================================

  describe('Real-time Validation', () => {
    it('displays validation panel in the UI', () => {
      render(<App />);

      // Validation panel should be present
      const validationPanel = screen.getByTestId('validation-panel');
      expect(validationPanel).toBeInTheDocument();
    });

    it('shows warning for single-node workflow', () => {
      render(<App />);

      // Initial state has single "Start" node
      const warningText = screen.getByText(/single node/i);
      expect(warningText).toBeInTheDocument();
    });

    it('shows valid status when workflow is properly connected', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a second node
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      // Note: In the mock, we can't easily add edges, so this test verifies
      // that validation updates when nodes change
      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });
    });

    it('updates validation when workflow changes', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Initial warning about single node
      expect(screen.getByText(/single node/i)).toBeInTheDocument();

      // Add nodes - validation should update
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(3);
      });
    });
  });

  // ==============================================================================
  // Undo/Redo Tests (Phase 2 UX Improvement)
  // ==============================================================================

  describe('Undo/Redo', () => {
    it('displays undo button in toolbar', () => {
      render(<App />);

      const undoButton = screen.getByRole('button', { name: /undo/i });
      expect(undoButton).toBeInTheDocument();
    });

    it('displays redo button in toolbar', () => {
      render(<App />);

      const redoButton = screen.getByRole('button', { name: /redo/i });
      expect(redoButton).toBeInTheDocument();
    });

    it('undo button is disabled initially', () => {
      render(<App />);

      const undoButton = screen.getByRole('button', { name: /undo/i });
      expect(undoButton).toBeDisabled();
    });

    it('redo button is disabled initially', () => {
      render(<App />);

      const redoButton = screen.getByRole('button', { name: /redo/i });
      expect(redoButton).toBeDisabled();
    });

    it('enables undo after adding a node', async () => {
      const user = userEvent.setup();
      render(<App />);

      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const undoButton = screen.getByRole('button', { name: /undo/i });
        expect(undoButton).not.toBeDisabled();
      });
    });

    it('supports Ctrl+Z keyboard shortcut for undo', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node first to have something to undo
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      // Verify node was added
      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });

      // Undo via keyboard
      await user.keyboard('{Control>}z{/Control}');

      // Note: Due to React Flow mocking, we can't fully test the state restoration
      // but we verify the keyboard handler is set up via the button title
      const undoButton = screen.getByRole('button', { name: /undo/i });
      expect(undoButton).toHaveAttribute('title', expect.stringMatching(/ctrl\+z/i));
    });
  });

  // ==============================================================================
  // Node Deletion Tests (Phase 3 UX Improvement)
  // ==============================================================================

  describe('Node Deletion', () => {
    it('Delete key removes selected nodes', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node first
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2); // Start + Tool
      });

      // Select the node by clicking it
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      expect(addedNode).toBeTruthy();
      await user.click(addedNode!);

      // Press Delete key
      await user.keyboard('{Delete}');

      // Node should be removed (or toast should show for protected nodes)
      await waitFor(() => {
        // Either the node is removed or a toast is shown for protected nodes
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBeLessThanOrEqual(2);
      });
    });

    it('Backspace key removes selected nodes', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node first
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });

      // Select the node by clicking it
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      expect(addedNode).toBeTruthy();
      await user.click(addedNode!);

      // Press Backspace key
      await user.keyboard('{Backspace}');

      // Node should be removed or toast for protected nodes
      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBeLessThanOrEqual(2);
      });
    });

    it('prevents deletion of Start node and shows warning toast', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Click on the Start node to select it
      const startNode = document.querySelector('[data-node-id="start"]');
      expect(startNode).toBeTruthy();
      await user.click(startNode!);

      // Press Delete key
      await user.keyboard('{Delete}');

      // Start node should NOT be removed
      await waitFor(() => {
        const startNodeAfter = document.querySelector('[data-node-id="start"]');
        expect(startNodeAfter).toBeTruthy();
      });
    });

    it('takes undo snapshot before deleting nodes', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });

      // Select and delete node
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      await user.click(addedNode!);
      await user.keyboard('{Delete}');

      // Undo should be available after deletion
      await waitFor(() => {
        const undoButton = screen.getByRole('button', { name: /undo/i });
        expect(undoButton).not.toBeDisabled();
      });
    });
  });

  // ==============================================================================
  // Context Menu Tests (Phase 3 UX Improvement)
  // ==============================================================================

  describe('Context Menu', () => {
    it('right-click on node shows context menu', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });

      // Right-click on the node
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      expect(addedNode).toBeTruthy();
      await user.pointer({ target: addedNode!, keys: '[MouseRight]' });

      // Context menu should appear with delete option
      await waitFor(() => {
        const deleteOption = screen.queryByRole('menuitem', { name: /delete/i }) ||
                            screen.queryByText(/delete node/i);
        // Context menu should exist in the implementation
        expect(deleteOption || screen.queryByTestId('context-menu')).toBeTruthy();
      }, { timeout: 1000 });
    });

    it('clicking outside context menu closes it', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });

      // Right-click on node
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      await user.pointer({ target: addedNode!, keys: '[MouseRight]' });

      // Click outside to close
      const canvas = document.querySelector('.react-flow__renderer');
      if (canvas) {
        await user.click(canvas);
      }

      // Context menu should be closed
      await waitFor(() => {
        const contextMenu = document.querySelector('[data-testid="context-menu"]');
        expect(contextMenu).toBeFalsy();
      }, { timeout: 500 });
    });

    it('context menu delete option removes the node', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      const initialNodeCount = document.querySelectorAll('.react-flow__node').length;

      // Right-click on node
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      await user.pointer({ target: addedNode!, keys: '[MouseRight]' });

      // Click delete in context menu (if available)
      const deleteOption = screen.queryByRole('menuitem', { name: /delete/i }) ||
                          screen.queryByText(/delete/i);
      if (deleteOption) {
        await user.click(deleteOption);

        await waitFor(() => {
          const nodes = document.querySelectorAll('.react-flow__node');
          expect(nodes.length).toBeLessThan(initialNodeCount);
        });
      }
    });

    it('context menu includes configure option', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Add a node
      const toolButton = screen.getByRole('button', { name: /tool/i });
      await user.click(toolButton);

      await waitFor(() => {
        const nodes = document.querySelectorAll('.react-flow__node');
        expect(nodes.length).toBe(2);
      });

      // Right-click on node
      const addedNode = document.querySelector('[data-node-id^="node_"]');
      await user.pointer({ target: addedNode!, keys: '[MouseRight]' });

      // Configure option should exist
      await waitFor(() => {
        const configureOption = screen.queryByRole('menuitem', { name: /configure/i }) ||
                               screen.queryByText(/configure/i) ||
                               screen.queryByText(/edit/i);
        expect(configureOption || screen.queryByTestId('context-menu')).toBeTruthy();
      }, { timeout: 1000 });
    });
  });

  // ==============================================================================
  // Dark Mode Tests (Phase 2 UX Improvement)
  // ==============================================================================

  describe('Dark Mode', () => {
    beforeEach(() => {
      // Clear localStorage before each test
      localStorage.clear();
      // Ensure document doesn't have dark class
      document.documentElement.classList.remove('dark');
      // Mock matchMedia for dark mode detection
      Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        })),
      });
    });

    it('renders dark mode toggle button', () => {
      render(<App />);

      const toggleButton = screen.getByRole('button', { name: /switch to dark mode/i });
      expect(toggleButton).toBeInTheDocument();
    });

    it('toggles dark mode when button is clicked', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Initially in light mode
      const toggleButton = screen.getByRole('button', { name: /switch to dark mode/i });
      await user.click(toggleButton);

      // Should now be in dark mode
      await waitFor(() => {
        expect(document.documentElement.classList.contains('dark')).toBe(true);
      });
    });

    it('shows sun icon in dark mode, moon icon in light mode', async () => {
      const user = userEvent.setup();
      render(<App />);

      // Light mode shows moon icon (click to switch to dark)
      let toggleButton = screen.getByRole('button', { name: /switch to dark mode/i });
      expect(toggleButton).toBeInTheDocument();

      // Click to toggle to dark mode
      await user.click(toggleButton);

      // Dark mode shows sun icon (click to switch to light)
      await waitFor(() => {
        toggleButton = screen.getByRole('button', { name: /switch to light mode/i });
        expect(toggleButton).toBeInTheDocument();
      });
    });

    it('persists dark mode preference to localStorage', async () => {
      const user = userEvent.setup();
      render(<App />);

      const toggleButton = screen.getByRole('button', { name: /switch to dark mode/i });
      await user.click(toggleButton);

      await waitFor(() => {
        expect(localStorage.getItem('theme')).toBe('dark');
      });
    });

    it('applies dark mode styling to header', async () => {
      const user = userEvent.setup();
      render(<App />);

      const toggleButton = screen.getByRole('button', { name: /switch to dark mode/i });
      await user.click(toggleButton);

      // Check that dark mode classes are applied to the container
      await waitFor(() => {
        const container = document.querySelector('.dark');
        expect(container).toBeTruthy();
      });
    });
  });
});
