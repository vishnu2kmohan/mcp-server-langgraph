/**
 * useBranching Hook
 *
 * Manages conversation branching for exploring alternative conversation paths.
 * Features:
 * - Create branches from any message
 * - Switch between branches
 * - Branch metadata (parent, creation time)
 * - Branch navigation and comparison
 * - Branch deletion and renaming
 */

import { useState, useCallback, useMemo } from "react";

// ==============================================================================
// Types
// ==============================================================================

export interface BranchMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  [key: string]: unknown;
}

export interface Branch {
  /** Unique branch identifier */
  id: string;
  /** Display name */
  name: string;
  /** Messages in this branch */
  messages: BranchMessage[];
  /** Parent branch ID (null for main) */
  parentBranchId: string | null;
  /** Message ID where branch was created */
  branchPointMessageId: string | null;
  /** Creation timestamp */
  createdAt: number;
}

export interface BranchingState {
  /** All branches */
  branches: Branch[];
  /** Currently active branch */
  currentBranch: Branch;
  /** Create a new branch from a message */
  createBranch: (messageId: string, name?: string) => void;
  /** Switch to a different branch */
  switchBranch: (branchId: string) => boolean;
  /** Delete a branch */
  deleteBranch: (branchId: string) => boolean;
  /** Rename a branch */
  renameBranch: (branchId: string, newName: string) => boolean;
  /** Add a message to the current branch */
  addMessageToBranch: (message: BranchMessage) => void;
  /** Get all message IDs that have branches */
  getBranchPoints: () => string[];
  /** Get all branches that start from a specific message */
  getBranchesAtMessage: (messageId: string) => Branch[];
  /** Get the divergence point between two branches */
  getDivergencePoint: (branchId1: string, branchId2: string) => string | null;
}

// ==============================================================================
// Helper Functions
// ==============================================================================

function generateBranchId(): string {
  return `branch-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function generateBranchName(branchNumber: number): string {
  return `Branch ${branchNumber}`;
}

// ==============================================================================
// Hook
// ==============================================================================

export function useBranching(initialMessages: BranchMessage[]): BranchingState {
  // Initialize branches state with main branch
  const [branches, setBranches] = useState<Branch[]>(() => [
    {
      id: "main",
      name: "Main",
      messages: [...initialMessages], // Copy to avoid reference issues
      parentBranchId: null,
      branchPointMessageId: null,
      createdAt: Date.now(),
    },
  ]);
  const [currentBranchId, setCurrentBranchId] = useState("main");

  // Get current branch
  const currentBranch = useMemo(() => {
    const branch = branches.find((b) => b.id === currentBranchId);
    return branch || branches[0];
  }, [branches, currentBranchId]);

  // Create a new branch from a message
  const createBranch = useCallback(
    (messageId: string, name?: string) => {
      // Find the message index in current branch
      const messageIndex = currentBranch.messages.findIndex(
        (m) => m.id === messageId,
      );

      if (messageIndex === -1) return;

      // Get messages up to and including the branch point
      const branchMessages = currentBranch.messages.slice(0, messageIndex + 1);

      // Generate branch ID and name
      const branchId = generateBranchId();
      const branchName = name || generateBranchName(branches.length);

      const newBranch: Branch = {
        id: branchId,
        name: branchName,
        messages: [...branchMessages],
        parentBranchId: currentBranch.id,
        branchPointMessageId: messageId,
        createdAt: Date.now(),
      };

      setBranches((prev) => [...prev, newBranch]);
      setCurrentBranchId(branchId);
    },
    [currentBranch, branches.length],
  );

  // Switch to a different branch
  const switchBranch = useCallback(
    (branchId: string): boolean => {
      const branch = branches.find((b) => b.id === branchId);
      if (!branch) return false;

      setCurrentBranchId(branchId);
      return true;
    },
    [branches],
  );

  // Delete a branch
  const deleteBranch = useCallback(
    (branchId: string): boolean => {
      // Cannot delete main branch
      if (branchId === "main") return false;

      const branchExists = branches.some((b) => b.id === branchId);
      if (!branchExists) return false;

      setBranches((prev) => prev.filter((b) => b.id !== branchId));

      // If deleting current branch, switch to main
      if (currentBranchId === branchId) {
        setCurrentBranchId("main");
      }

      return true;
    },
    [branches, currentBranchId],
  );

  // Rename a branch
  const renameBranch = useCallback(
    (branchId: string, newName: string): boolean => {
      const branchExists = branches.some((b) => b.id === branchId);
      if (!branchExists) return false;

      setBranches((prev) =>
        prev.map((b) => (b.id === branchId ? { ...b, name: newName } : b)),
      );

      return true;
    },
    [branches],
  );

  // Add a message to the current branch
  const addMessageToBranch = useCallback(
    (message: BranchMessage) => {
      setBranches((prev) =>
        prev.map((b) =>
          b.id === currentBranchId
            ? { ...b, messages: [...b.messages, message] }
            : b,
        ),
      );
    },
    [currentBranchId],
  );

  // Get all message IDs that have branches
  const getBranchPoints = useCallback((): string[] => {
    const branchPoints = new Set<string>();

    branches.forEach((branch) => {
      if (branch.branchPointMessageId) {
        branchPoints.add(branch.branchPointMessageId);
      }
    });

    return Array.from(branchPoints);
  }, [branches]);

  // Get all branches that start from a specific message
  const getBranchesAtMessage = useCallback(
    (messageId: string): Branch[] => {
      return branches.filter((b) => b.branchPointMessageId === messageId);
    },
    [branches],
  );

  // Get the divergence point between two branches
  const getDivergencePoint = useCallback(
    (branchId1: string, branchId2: string): string | null => {
      const branch1 = branches.find((b) => b.id === branchId1);
      const branch2 = branches.find((b) => b.id === branchId2);

      if (!branch1 || !branch2) return null;

      // If one is the parent of the other, return the branch point
      if (branch2.parentBranchId === branchId1) {
        return branch2.branchPointMessageId;
      }
      if (branch1.parentBranchId === branchId2) {
        return branch1.branchPointMessageId;
      }

      // Find last common message
      const messages1 = branch1.messages;
      const messages2 = branch2.messages;

      let lastCommonId: string | null = null;
      const minLength = Math.min(messages1.length, messages2.length);

      for (let i = 0; i < minLength; i++) {
        if (messages1[i].id === messages2[i].id) {
          lastCommonId = messages1[i].id;
        } else {
          break;
        }
      }

      return lastCommonId;
    },
    [branches],
  );

  return {
    branches,
    currentBranch,
    createBranch,
    switchBranch,
    deleteBranch,
    renameBranch,
    addMessageToBranch,
    getBranchPoints,
    getBranchesAtMessage,
    getDivergencePoint,
  };
}

export default useBranching;
