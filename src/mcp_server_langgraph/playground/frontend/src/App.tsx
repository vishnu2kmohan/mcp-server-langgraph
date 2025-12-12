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
