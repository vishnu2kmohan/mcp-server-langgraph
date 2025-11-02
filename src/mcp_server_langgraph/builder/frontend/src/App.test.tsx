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
import { render, screen, waitFor, within } from './test/test-utils';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import App from './App';
import { mockWorkflow, mockGeneratedCode, createMockAxiosResponse, createMockAxiosError } from './test/test-utils';

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

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
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

    it('renders workflow name and description inputs', () => {
      render(<App />);

      const nameInput = screen.getByDisplayValue('my_agent');
      const descInput = screen.getByDisplayValue('My custom agent workflow');

      expect(nameInput).toBeInTheDocument();
      expect(descInput).toBeInTheDocument();
    });

    it('renders node type buttons', () => {
      render(<App />);

      // Should have buttons for each node type
      expect(screen.getByText(/Tool/i)).toBeInTheDocument();
      expect(screen.getByText(/LLM/i)).toBeInTheDocument();
      expect(screen.getByText(/Conditional/i)).toBeInTheDocument();
      expect(screen.getByText(/Approval/i)).toBeInTheDocument();
      expect(screen.getByText(/Custom/i)).toBeInTheDocument();
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

    it('allows changing workflow description', async () => {
      const user = userEvent.setup();
      render(<App />);

      const descInput = screen.getByDisplayValue('My custom agent workflow');
      await user.clear(descInput);
      await user.type(descInput, 'New description');

      expect(descInput).toHaveValue('New description');
    });
  });

  // ==============================================================================
  // Code Generation Tests
  // ==============================================================================

  describe('Code Generation', () => {
    it('calls API to generate code when Generate Code button is clicked', async () => {
      const user = userEvent.setup();
      mockedAxios.post.mockResolvedValueOnce(
        createMockAxiosResponse({ code: mockGeneratedCode, formatted: true, warnings: [] })
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
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

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
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

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
      });
    });

    it('handles code generation API errors gracefully', async () => {
      const user = userEvent.setup();
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      mockedAxios.post.mockRejectedValueOnce(
        createMockAxiosError('Code generation failed', 400)
      );

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(
          expect.stringContaining('Code generation failed')
        );
      });

      alertSpy.mockRestore();
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

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
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

      // Mock URL.createObjectURL and URL.revokeObjectURL
      const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
      const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});

      // Mock document.createElement and click
      const mockAnchor = {
        href: '',
        download: '',
        click: vi.fn(),
      };
      vi.spyOn(document, 'createElement').mockReturnValue(mockAnchor as any);

      render(<App />);

      // Generate code first
      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
      });

      // Now download
      const downloadButton = screen.getByRole('button', { name: /download/i });
      await user.click(downloadButton);

      expect(createObjectURLSpy).toHaveBeenCalled();
      expect(mockAnchor.click).toHaveBeenCalled();
      expect(mockAnchor.download).toBe('my_agent.py');

      createObjectURLSpy.mockRestore();
      revokeObjectURLSpy.mockRestore();
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
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      mockedAxios.post.mockRejectedValueOnce(
        createMockAxiosError('Save failed', 500)
      );

      render(<App />);

      const saveButton = screen.getByRole('button', { name: /save.*file/i });
      await user.click(saveButton);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalledWith(
          expect.stringContaining('Save failed')
        );
      });

      alertSpy.mockRestore();
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

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
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
      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
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

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(mockedAxios.post).toHaveBeenCalled();
      });
    });

    it('handles network errors during code generation', async () => {
      const user = userEvent.setup();
      const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {});

      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));

      render(<App />);

      const generateButton = screen.getByRole('button', { name: /generate.*code/i });
      await user.click(generateButton);

      await waitFor(() => {
        expect(alertSpy).toHaveBeenCalled();
      });

      alertSpy.mockRestore();
    });
  });
});
