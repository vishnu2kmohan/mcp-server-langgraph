/* eslint-disable react-refresh/only-export-components */
/**
 * ChatLoaderContext
 *
 * Provides chat route loader data to components rendered outside the route hierarchy.
 * This is needed because StudioShellLayout renders ConnectedConversationPanel directly
 * (based on isChatRoute detection), not as a child of the chat route's element.
 *
 * The ChatLoaderProvider is rendered as the chat route's element and provides
 * the loader data via context, which StudioShellLayout's children can consume.
 */

import { createContext, useContext, type ReactNode } from "react";
import { useLoaderData, Outlet } from "react-router";
import type { ChatLoaderData } from "../router/loaders";

// Context for chat loader data
const ChatLoaderContext = createContext<ChatLoaderData | null>(null);

/**
 * Provider component that wraps chat routes and provides loader data via context.
 * Renders an Outlet to allow child routes to render.
 */
export function ChatLoaderProvider() {
  const loaderData = useLoaderData() as ChatLoaderData;

  return (
    <ChatLoaderContext.Provider value={loaderData}>
      <Outlet />
    </ChatLoaderContext.Provider>
  );
}

/**
 * Hook to access chat loader data from context.
 * Returns null if not within a ChatLoaderProvider.
 */
export function useChatLoaderData(): ChatLoaderData | null {
  return useContext(ChatLoaderContext);
}

/**
 * Wrapper component for chat route elements that provides loader data.
 * Use this as the element for chat routes instead of empty fragments.
 */
export function ChatRouteElement({ children }: { children?: ReactNode }) {
  const loaderData = useLoaderData() as ChatLoaderData;

  return (
    <ChatLoaderContext.Provider value={loaderData}>
      {children ?? null}
    </ChatLoaderContext.Provider>
  );
}
