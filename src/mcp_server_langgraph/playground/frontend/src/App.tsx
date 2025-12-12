/**
 * Playground Frontend Application
 *
 * Main application component that composes the layout and integrates
 * MCP Host context for multi-server management.
 */

import React, { useState, useCallback } from 'react';
import { MCPHostProvider } from './contexts/MCPHostContext';
import { Header, Sidebar } from './components/Layout';
import { SessionList, CreateSessionModal } from './components/Sessions';
import { ChatInterface } from './components/Chat';
import { ObservabilityTabs } from './components/Observability';
import { ElicitationDialog, SamplingDialog } from './components/MCP';
import { useMCPElicitation } from './hooks/useMCPElicitation';
import { useMCPSampling } from './hooks/useMCPSampling';
import { useSession } from './hooks/useSession';

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

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-dark-bg">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar with Sessions */}
        <Sidebar>
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
    <MCPHostProvider>
      <AppContent />
    </MCPHostProvider>
  );
}
