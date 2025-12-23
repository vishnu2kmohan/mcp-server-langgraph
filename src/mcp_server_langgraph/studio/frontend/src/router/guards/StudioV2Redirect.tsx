/**
 * StudioV2Redirect
 *
 * Redirects /studio/v2/* routes to /studio/*
 *
 * This provides backward compatibility for any bookmarks or links
 * that still reference the old /studio/v2/* URLs.
 */

import { Navigate, useLocation } from "react-router";

export function StudioV2Redirect() {
  const { pathname, search, hash } = useLocation();

  // Map /studio/v2/* to /studio/*
  const newPath = pathname.replace(/^\/studio\/v2/, "/studio");

  // Preserve query params and hash
  return <Navigate to={`${newPath}${search}${hash}`} replace />;
}

export default StudioV2Redirect;
