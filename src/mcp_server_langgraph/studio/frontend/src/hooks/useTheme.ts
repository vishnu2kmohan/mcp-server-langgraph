/**
 * useTheme Hook
 *
 * Manages theme state and applies dark/light mode to the document.
 * Defaults to dark mode but respects user preferences once set.
 */

import { useEffect, useCallback } from "react";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import {
  setTheme as setThemeAction,
  selectTheme,
} from "../store/slices/uiSlice";

export interface UseThemeReturn {
  theme: "light" | "dark" | "system";
  isDark: boolean;
  setTheme: (theme: "light" | "dark" | "system") => void;
  toggleTheme: () => void;
}

/**
 * Hook to manage and apply theme to the document
 */
export function useTheme(): UseThemeReturn {
  const dispatch = useAppDispatch();
  const theme = useAppSelector(selectTheme);

  // Determine if dark mode should be applied
  const getEffectiveTheme = useCallback((): boolean => {
    if (theme === "dark") return true;
    if (theme === "light") return false;
    // For "system", check system preference
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return true; // Default to dark if can't detect
  }, [theme]);

  const isDark = getEffectiveTheme();

  // Apply theme class to document
  useEffect(() => {
    const applyTheme = () => {
      const shouldBeDark = getEffectiveTheme();
      if (shouldBeDark) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    };

    applyTheme();

    // Listen for system theme changes when in "system" mode
    if (
      theme === "system" &&
      typeof window !== "undefined" &&
      window.matchMedia
    ) {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleChange = () => applyTheme();

      mediaQuery.addEventListener("change", handleChange);
      return () => mediaQuery.removeEventListener("change", handleChange);
    }
    return undefined;
  }, [theme, getEffectiveTheme]);

  // Set theme action
  const setTheme = useCallback(
    (newTheme: "light" | "dark" | "system") => {
      dispatch(setThemeAction(newTheme));
    },
    [dispatch],
  );

  // Toggle between light and dark
  const toggleTheme = useCallback(() => {
    const newTheme = isDark ? "light" : "dark";
    dispatch(setThemeAction(newTheme));
  }, [dispatch, isDark]);

  return {
    theme,
    isDark,
    setTheme,
    toggleTheme,
  };
}

export default useTheme;
