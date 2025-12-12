/**
 * Header Component
 *
 * Application header with title, dark mode toggle, connection status, and auth controls.
 */

import React, { useState, useCallback } from 'react';
import { useDarkMode } from '../../hooks/useDarkMode';
import { useMCPHost } from '../../contexts/MCPHostContext';
import { useAuthContext } from '../../contexts/AuthContext';
import { LoginForm } from '../Auth';

// Icons as SVG components
function SunIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z"
      />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z"
      />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"
      />
    </svg>
  );
}

function ConnectionDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    connected: 'bg-success-500',
    connecting: 'bg-warning-500 animate-pulse',
    disconnected: 'bg-gray-400',
    error: 'bg-error-500',
  };

  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${colors[status] || colors.disconnected}`}
      aria-hidden="true"
    />
  );
}

export function Header(): React.ReactElement {
  const { isDark, toggle } = useDarkMode();
  const { servers, pendingElicitations } = useMCPHost();
  const { user, isAuthenticated, isLoading: isAuthLoading, error: authError, login, logout, clearError } = useAuthContext();

  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  const handleLogin = useCallback(
    async (username: string, password: string) => {
      await login({ username, password });
    },
    [login]
  );

  const handleOpenLogin = useCallback(() => {
    clearError();
    setIsLoginModalOpen(true);
  }, [clearError]);

  const handleCloseLogin = useCallback(() => {
    setIsLoginModalOpen(false);
    clearError();
  }, [clearError]);

  // Get overall connection status
  const connectedCount = Array.from(servers.values()).filter(
    (s) => s.status === 'connected'
  ).length;
  const totalCount = servers.size;
  const overallStatus =
    connectedCount > 0 ? 'connected' : totalCount > 0 ? 'error' : 'disconnected';

  const alertCount = pendingElicitations.length;

  return (
    <header
      className="h-16 flex items-center justify-between px-6 bg-white dark:bg-dark-surface border-b border-gray-200 dark:border-dark-border"
      role="banner"
    >
      {/* Left: Title */}
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-dark-text">
          Interactive Playground
        </h1>
      </div>

      {/* Right: Status and Controls */}
      <div className="flex items-center gap-4">
        {/* Connection Status */}
        <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-dark-textSecondary">
          <ConnectionDot status={overallStatus} />
          <span>
            {overallStatus === 'connected'
              ? `Connected (${connectedCount})`
              : overallStatus === 'error'
              ? 'Connection Error'
              : 'Disconnected'}
          </span>
        </div>

        {/* Alert Badge */}
        {alertCount > 0 && (
          <div className="badge badge-warning">
            {alertCount} pending
          </div>
        )}

        {/* Dark Mode Toggle */}
        <button
          onClick={toggle}
          className="btn btn-ghost p-2"
          aria-label="Toggle dark mode"
        >
          {isDark ? (
            <SunIcon className="w-5 h-5" />
          ) : (
            <MoonIcon className="w-5 h-5" />
          )}
        </button>

        {/* Auth Controls */}
        <div className="flex items-center gap-2 pl-2 border-l border-gray-200 dark:border-dark-border">
          {isAuthLoading ? (
            <span className="text-sm text-gray-500 dark:text-dark-textMuted">Loading...</span>
          ) : isAuthenticated && user ? (
            <>
              <div className="flex items-center gap-2">
                <UserIcon className="w-5 h-5 text-gray-600 dark:text-dark-textSecondary" />
                <span className="text-sm text-gray-700 dark:text-dark-textSecondary">
                  {user.username}
                </span>
              </div>
              <button
                onClick={() => logout()}
                className="btn btn-ghost text-sm"
              >
                Sign Out
              </button>
            </>
          ) : (
            <button
              onClick={handleOpenLogin}
              className="btn btn-primary text-sm"
            >
              Sign In
            </button>
          )}
        </div>
      </div>

      {/* Login Modal */}
      <LoginForm
        isOpen={isLoginModalOpen}
        onClose={handleCloseLogin}
        onLogin={handleLogin}
        isLoading={isAuthLoading}
        error={authError}
      />
    </header>
  );
}
