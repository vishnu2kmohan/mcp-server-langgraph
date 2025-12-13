/**
 * Redux Store Configuration
 *
 * Unified store using Redux Toolkit with RTK Query for API caching.
 * Coexists with existing Zustand stores for gradual migration.
 */

import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { api } from '../api';
import uiReducer from './slices/uiSlice';
import featureFlagsReducer from './slices/featureFlagsSlice';

export const store = configureStore({
  reducer: {
    // RTK Query API reducer
    [api.reducerPath]: api.reducer,
    // UI state
    ui: uiReducer,
    // Feature flags
    featureFlags: featureFlagsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(api.middleware),
  devTools: process.env.NODE_ENV !== 'production',
});

// Enable refetchOnFocus and refetchOnReconnect
setupListeners(store.dispatch);

// Infer types from store
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
