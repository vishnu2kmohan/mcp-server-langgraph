/**
 * Playground Frontend Application
 *
 * Main application component that composes the layout and integrates
 * MCP Host context for multi-server management.
 */

import React, { useState, useCallback } from 'react';
import { MCPHostProvider } from './contexts/MCPHostContext';
import { AuthProvider } from './contexts/AuthContext';
import { Header, Sidebar } from './components/Layout';
import { SessionList, CreateSessionModal, SessionExportButtons } from './components/Sessions';
import { ChatInterface } from './components/Chat';
import { ObservabilityTabs } from './components/Observability';
import { ElicitationDialog, SamplingDialog } from './components/MCP';
import { useMCPElicitation } from './hooks/useMCPElicitation';
import { useMCPSampling } from './hooks/useMCPSampling';
import { useSession } from './hooks/useSession';
import { useSidebarState } from './hooks/useSidebarState';
import { useDarkMode } from './hooks/useDarkMode';
import { useServiceWorker } from './hooks/useServiceWorker';
import {
  FeatureHint,
  useFeatureDiscovery,
  HelpPanel,
} from '../../../shared/frontend/src/components';
import { useFTUXAnalytics } from '../../../shared/frontend/src/hooks/useFTUXAnalytics';

// Inline HelpCircle icon (Playground doesn't use lucide-react)
function HelpCircleIcon({ size = 24 }: { size?: number }): React.ReactElement {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function AppContent(): React.ReactElement {
  // Session management
  const {
    sessions,
    activeSession,
    isLoading: isSessionLoading,
    createSession,
    selectSession,
    deleteSession,
  } = useSession({ autoLoad: true });

  // Sidebar state with localStorage persistence
  const { isCollapsed: isSidebarCollapsed, toggle: toggleSidebar } = useSidebarState();

  // Dark mode with keyboard shortcut (Ctrl+Shift+T)
  useDarkMode({ enableKeyboardShortcut: true });

  // Service worker for offline support
  const { isOffline, hasUpdate, updateServiceWorker } = useServiceWorker();

  // Modal state for creating new sessions
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // FTUX Analytics and Help Panel
  const ftuxAnalytics = useFTUXAnalytics({ totalOnboardingSteps: 3 });
  const [isHelpPanelOpen, setIsHelpPanelOpen] = useState(false);

  // Feature hints for progressive disclosure
  const featureHints = [
    {
      featureId: 'mcp-servers',
      title: 'Connect MCP Servers',
      description: 'Use the Resource Browser to connect and manage MCP servers for extended capabilities.',
    },
    {
      featureId: 'sessions',
      title: 'Organize with Sessions',
      description: 'Create sessions to organize your conversations and maintain context.',
    },
    {
      featureId: 'observability',
      title: 'Monitor Performance',
      description: 'Check the Observability panel to see traces, metrics, and performance data.',
    },
  ];

  const { currentHint, dismissHint } = useFeatureDiscovery(featureHints);

  // Help panel content
  const helpSections = [
    { id: 'basics', title: 'Getting Started', icon: '📚' },
    { id: 'mcp', title: 'MCP Servers', icon: '🔌' },
    { id: 'sessions', title: 'Sessions', icon: '💬' },
  ];

  const helpArticles = [
    { id: 'h1', title: 'Starting a Conversation', content: 'Type your message in the chat input and press Enter or click Send. The AI will respond based on your configured agent.', category: 'basics' },
    { id: 'h2', title: 'Creating Sessions', content: 'Click "+ New Session" in the sidebar to create a new conversation context. Each session maintains its own history.', category: 'sessions' },
    { id: 'h3', title: 'Connecting MCP Servers', content: 'MCP (Model Context Protocol) servers extend AI capabilities. Use the Resource Browser to discover and connect available servers.', category: 'mcp' },
    { id: 'h4', title: 'Using Tools', content: 'When connected to MCP servers, additional tools become available. The AI can use these tools to perform actions on your behalf.', category: 'mcp' },
  ];

  const keyboardShortcuts = [
    { keys: ['Ctrl', 'Shift', 'T'], description: 'Toggle dark mode' },
    { keys: ['Enter'], description: 'Send message' },
    { keys: ['Shift', 'Enter'], description: 'New line in message' },
    { keys: ['Esc'], description: 'Close dialogs' },
  ];

  // MCP elicitation handlers
  const {
    currentElicitation,
    accept: acceptElicitation,
    decline: declineElicitation,
    cancel: cancelElicitation,
  } = useMCPElicitation();

  // MCP sampling handlers
  const {
    currentRequest: currentSamplingRequest,
    approve: approveSampling,
    reject: rejectSampling,
  } = useMCPSampling();

  // Session handlers
  const handleCreateSession = useCallback(
    async (name: string) => {
      try {
        await createSession(name);
      } catch (error) {
        console.error('Failed to create session:', error);
      }
    },
    [createSession]
  );

  const handleSelectSession = useCallback(
    (sessionId: string) => {
      selectSession(sessionId);
    },
    [selectSession]
  );

  const handleDeleteSession = useCallback(
    (sessionId: string) => {
      deleteSession(sessionId);
    },
    [deleteSession]
  );

  // Import sessions handler
  const handleImportSessions = useCallback(
    (importedSessions: Array<{ id: string; title: string; messages: unknown[] }>) => {
      // For now, just log - full implementation would merge with existing sessions
      console.log('Imported sessions:', importedSessions);
      // TODO: Implement session import via useSession hook when backend supports it
    },
    []
  );

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-dark-bg">
      {/* Offline Banner */}
      {isOffline && (
        <div className="bg-warning-500 text-white px-4 py-2 text-center text-sm">
          You are currently offline. Some features may be unavailable.
        </div>
      )}

      {/* Update Available Banner */}
      {hasUpdate && (
        <div className="bg-primary-500 text-white px-4 py-2 text-center text-sm flex items-center justify-center gap-4">
          <span>A new version is available.</span>
          <button
            onClick={updateServiceWorker}
            className="px-3 py-1 bg-white text-primary-600 rounded text-sm font-medium hover:bg-primary-50"
          >
            Update Now
          </button>
        </div>
      )}

      {/* Header */}
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar with Sessions */}
        <Sidebar
          title="Sessions"
          collapsed={isSidebarCollapsed}
          onToggle={toggleSidebar}
        >
          {/* New Session Button */}
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="w-full mb-2 btn btn-primary text-sm"
          >
            + New Session
          </button>
          <SessionList
            sessions={sessions}
            selectedId={activeSession?.id}
            isLoading={isSessionLoading}
            onSelect={handleSelectSession}
            onDelete={handleDeleteSession}
          />
          {/* Export/Import Controls */}
          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-dark-border">
            <SessionExportButtons
              sessions={sessions}
              onImport={handleImportSessions}
              variant="compact"
            />
          </div>
        </Sidebar>

        {/* Main Content Area */}
        <main className="flex-1 flex overflow-hidden" role="main">
          {/* Chat Interface */}
          <div className="flex-1 flex flex-col min-w-0">
            <ChatInterface />
          </div>

          {/* Observability Panel */}
          <div className="w-80 border-l border-gray-200 dark:border-dark-border flex flex-col">
            <ObservabilityTabs />
          </div>
        </main>
      </div>

      {/* MCP Dialogs */}
      <ElicitationDialog
        elicitation={currentElicitation}
        onAccept={acceptElicitation}
        onDecline={declineElicitation}
        onCancel={cancelElicitation}
      />
      <SamplingDialog
        request={currentSamplingRequest}
        onApprove={() => approveSampling(undefined)}
        onReject={rejectSampling}
      />

      {/* Session Create Modal */}
      <CreateSessionModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateSession}
      />

      {/* Help Panel (FTUX) */}
      <HelpPanel
        isOpen={isHelpPanelOpen}
        onClose={() => setIsHelpPanelOpen(false)}
        articles={helpArticles}
        sections={helpSections}
        keyboardShortcuts={keyboardShortcuts}
      />

      {/* Feature Hints (FTUX Progressive Disclosure) */}
      {currentHint && (
        <div className="fixed bottom-4 left-4 z-40 max-w-sm">
          <FeatureHint
            featureId={currentHint.featureId}
            title={currentHint.title}
            description={currentHint.description}
            onAction={() => {
              ftuxAnalytics.trackHintActionTaken(currentHint.featureId, 'try_it');
              dismissHint(currentHint.featureId);
            }}
            actionLabel="Got it!"
          />
        </div>
      )}

      {/* Help Button (floating) */}
      <button
        onClick={() => setIsHelpPanelOpen(true)}
        className="fixed bottom-4 right-4 z-40 p-3 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
        aria-label="Open help"
      >
        <HelpCircleIcon size={24} />
      </button>
    </div>
  );
}

export function App(): React.ReactElement {
  return (
    <AuthProvider>
      <MCPHostProvider>
        <AppContent />
      </MCPHostProvider>
    </AuthProvider>
  );
}
