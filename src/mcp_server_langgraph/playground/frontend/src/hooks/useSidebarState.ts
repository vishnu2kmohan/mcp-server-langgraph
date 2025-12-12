/**
 * useSidebarState Hook
 *
 * Manages sidebar collapsed/expanded state with localStorage persistence.
 * Supports both main sidebar state and individual section states.
 */

import { useState, useEffect, useCallback } from 'react';

const DEFAULT_STORAGE_KEY = 'sidebar-collapsed';
const SECTIONS_STORAGE_KEY = 'sidebar-sections';

export interface SectionStates {
  [key: string]: boolean;
}

export interface UseSidebarStateResult {
  isCollapsed: boolean;
  toggle: () => void;
  setCollapsed: (value: boolean) => void;
  sections: SectionStates;
  toggleSection: (sectionId: string) => void;
  setSectionCollapsed: (sectionId: string, value: boolean) => void;
}

function getInitialCollapsed(storageKey: string): boolean {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(storageKey);
    if (stored === 'true') return true;
    if (stored === 'false') return false;
  }
  return false; // Default to expanded
}

function getInitialSections(): SectionStates {
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(SECTIONS_STORAGE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch {
        return {};
      }
    }
  }
  return {};
}

export function useSidebarState(storageKey: string = DEFAULT_STORAGE_KEY): UseSidebarStateResult {
  const [isCollapsed, setIsCollapsed] = useState<boolean>(() => getInitialCollapsed(storageKey));
  const [sections, setSections] = useState<SectionStates>(() => getInitialSections());

  // Persist collapsed state
  useEffect(() => {
    localStorage.setItem(storageKey, String(isCollapsed));
  }, [isCollapsed, storageKey]);

  // Persist section states
  useEffect(() => {
    localStorage.setItem(SECTIONS_STORAGE_KEY, JSON.stringify(sections));
  }, [sections]);

  const toggle = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  const setCollapsed = useCallback((value: boolean) => {
    setIsCollapsed(value);
  }, []);

  const toggleSection = useCallback((sectionId: string) => {
    setSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }));
  }, []);

  const setSectionCollapsed = useCallback((sectionId: string, value: boolean) => {
    setSections((prev) => ({
      ...prev,
      [sectionId]: value,
    }));
  }, []);

  return {
    isCollapsed,
    toggle,
    setCollapsed,
    sections,
    toggleSection,
    setSectionCollapsed,
  };
}
