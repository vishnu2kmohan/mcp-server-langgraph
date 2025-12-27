import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { RouterProvider } from "react-router";
import { store } from "./store";
import { router } from "./router";
import { PreferencesProvider } from "./contexts/PreferencesContext";
import { FeatureFlagProvider } from "./contexts/FeatureFlagContext";
import { TelemetryProvider } from "./contexts/TelemetryContext";
import { ConnectedAIIntelligenceProvider } from "./contexts";
import { PermissionCacheProvider } from "./hooks/usePermissionCache";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { sessionTelemetry } from "./utils/sessionTelemetry";
import "./index.css";

// NOTE: Service worker registration is deferred until after authentication
// to avoid precaching ~130+ assets for unauthenticated users on the login page.
// See App.tsx for the deferred registration logic.

// Global error handler for ErrorBoundary - integrates with telemetry
const handleGlobalError = (
  error: Error,
  errorInfo: { componentStack?: string },
) => {
  // Track error in session telemetry
  sessionTelemetry.trackSessionCreation({
    success: false,
    durationMs: 0,
    error: `[ErrorBoundary] ${error.message}`,
  });

  // Log to console in development
  if (import.meta.env.DEV) {
    console.error("[Global Error Boundary]", error, errorInfo);
  }
};

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PreferencesProvider>
      <TelemetryProvider autoStartWebVitals>
        <Provider store={store}>
          <FeatureFlagProvider>
            <PermissionCacheProvider>
              <ConnectedAIIntelligenceProvider>
                <ErrorBoundary
                  name="GlobalErrorBoundary"
                  onError={handleGlobalError}
                  showDetails={import.meta.env.DEV}
                >
                  <RouterProvider router={router} />
                </ErrorBoundary>
              </ConnectedAIIntelligenceProvider>
            </PermissionCacheProvider>
          </FeatureFlagProvider>
        </Provider>
      </TelemetryProvider>
    </PreferencesProvider>
  </React.StrictMode>,
);
