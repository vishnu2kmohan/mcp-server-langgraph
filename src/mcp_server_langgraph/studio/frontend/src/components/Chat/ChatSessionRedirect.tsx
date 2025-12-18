/**
 * ChatSessionRedirect - Redirect /studio/chat/:sessionId to /studio/chat?session=:sessionId
 *
 * This component handles the URL pattern conversion from path-based session IDs
 * to query parameter-based session IDs, maintaining backward compatibility.
 */

import { Navigate, useParams } from "react-router";

export function ChatSessionRedirect() {
  const { sessionId } = useParams<{ sessionId: string }>();

  if (!sessionId) {
    return <Navigate to="/studio/chat" replace />;
  }

  return <Navigate to={`/studio/chat?session=${sessionId}`} replace />;
}
