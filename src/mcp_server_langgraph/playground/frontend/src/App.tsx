/**
 * Playground Frontend Application
 *
 * Main application component that composes the layout and integrates
 * MCP Host context for multi-server management.
 */

import React from 'react';
import { MCPHostProvider } from './contexts/MCPHostContext';
import { Header, Sidebar } from './components/Layout';
import { SessionList } from './components/Sessions';
import { ChatInterface } from './components/Chat';
import { ObservabilityTabs } from './components/Observability';
import { ElicitationDialog, SamplingDialog } from './components/MCP';
import { useMCPElicitation } from './hooks/useMCPElicitation';
import { useMCPSampling } from './hooks/useMCPSampling';

function AppContent(): React.ReactElement {
  const {
    pendingElicitation,
    accept: acceptElicitation,
    decline: declineElicitation,
    cancel: cancelElicitation,
  } = useMCPElicitation();

  const {
    pendingSamplingRequest,
    approveSampling,
    rejectSampling,
  } = useMCPSampling();

  return (
    <div className="h-screen flex flex-col bg-white dark:bg-dark-bg">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar with Sessions */}
        <Sidebar>
          <SessionList />
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
        elicitation={pendingElicitation}
        onAccept={acceptElicitation}
        onDecline={declineElicitation}
        onCancel={cancelElicitation}
      />
      <SamplingDialog
        request={pendingSamplingRequest}
        onApprove={approveSampling}
        onReject={rejectSampling}
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
