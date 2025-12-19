import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { RouterProvider } from "react-router";
import { store } from "./store";
import { router } from "./router";
import { PreferencesProvider } from "./contexts/PreferencesContext";
import { registerServiceWorker } from "./utils/serviceWorker";
import "./index.css";

// Register service worker for PWA offline support
if (import.meta.env.PROD) {
  registerServiceWorker();
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <PreferencesProvider>
      <Provider store={store}>
        <RouterProvider router={router} />
      </Provider>
    </PreferencesProvider>
  </React.StrictMode>,
);
