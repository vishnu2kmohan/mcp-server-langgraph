/**
 * Auth Context
 *
 * React context for sharing authentication state across the application.
 * Provides user info, login/logout actions, and auth status.
 */

import React, { createContext, useContext, ReactNode } from 'react';
import { useAuth, UseAuthResult } from '../hooks/useAuth';

// =============================================================================
// Context
// =============================================================================

const AuthContext = createContext<UseAuthResult | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps): React.ReactElement {
  const auth = useAuth({ autoLogin: true });

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useAuthContext(): UseAuthResult {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within AuthProvider');
  }
  return context;
}

// =============================================================================
// Exports
// =============================================================================

export { AuthContext };
