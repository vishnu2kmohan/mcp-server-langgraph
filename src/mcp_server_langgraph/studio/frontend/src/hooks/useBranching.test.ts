/**
 * useBranching Tests
 *
 * TDD tests for conversation branching functionality.
 * Tests cover:
 * - Creating branches
 * - Switching between branches
 * - Branch navigation
 * - Branch metadata
 * - Branch deletion
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useBranching } from "./useBranching";

describe("useBranching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockMessages = [
    { id: "msg1", role: "user" as const, content: "Hello" },
    { id: "msg2", role: "assistant" as const, content: "Hi there!" },
    { id: "msg3", role: "user" as const, content: "How are you?" },
    { id: "msg4", role: "assistant" as const, content: "I'm doing well!" },
  ];

  describe("initialization", () => {
    it("should initialize with main branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      expect(result.current.currentBranch).toBeDefined();
      expect(result.current.currentBranch.id).toBe("main");
      expect(result.current.currentBranch.name).toBe("Main");
    });

    it("should return all branches", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      expect(result.current.branches).toHaveLength(1);
      expect(result.current.branches[0].id).toBe("main");
    });

    it("should include messages in main branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      expect(result.current.currentBranch.messages).toEqual(mockMessages);
    });
  });

  describe("creating branches", () => {
    it("should create a branch from a message", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      expect(result.current.branches).toHaveLength(2);
    });

    it("should include messages up to branch point", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      const newBranch = result.current.branches.find((b) => b.id !== "main");
      // Should include msg1 and msg2
      expect(newBranch?.messages).toHaveLength(2);
      expect(newBranch?.messages[0].id).toBe("msg1");
      expect(newBranch?.messages[1].id).toBe("msg2");
    });

    it("should switch to new branch after creation", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      expect(result.current.currentBranch.id).not.toBe("main");
    });

    it("should set branch parent reference", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      const newBranch = result.current.branches.find((b) => b.id !== "main");
      expect(newBranch?.parentBranchId).toBe("main");
      expect(newBranch?.branchPointMessageId).toBe("msg2");
    });

    it("should generate unique branch ID", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
        result.current.switchBranch("main");
        result.current.createBranch("msg2");
      });

      const branchIds = result.current.branches.map((b) => b.id);
      const uniqueIds = new Set(branchIds);
      expect(uniqueIds.size).toBe(branchIds.length);
    });

    it("should allow custom branch name", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2", "My Custom Branch");
      });

      const newBranch = result.current.branches.find((b) => b.id !== "main");
      expect(newBranch?.name).toBe("My Custom Branch");
    });

    it("should set creation timestamp", () => {
      const before = Date.now();
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });
      const after = Date.now();

      const newBranch = result.current.branches.find((b) => b.id !== "main");
      expect(newBranch?.createdAt).toBeGreaterThanOrEqual(before);
      expect(newBranch?.createdAt).toBeLessThanOrEqual(after);
    });
  });

  describe("switching branches", () => {
    it("should switch to specified branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      const branchId = result.current.currentBranch.id;

      act(() => {
        result.current.switchBranch("main");
      });

      expect(result.current.currentBranch.id).toBe("main");

      act(() => {
        result.current.switchBranch(branchId);
      });

      expect(result.current.currentBranch.id).toBe(branchId);
    });

    it("should return false when switching to non-existent branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      let success: boolean = true;
      act(() => {
        success = result.current.switchBranch("non-existent");
      });

      expect(success).toBe(false);
      expect(result.current.currentBranch.id).toBe("main");
    });

    it("should load correct messages for branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      // New branch should have 2 messages
      expect(result.current.currentBranch.messages).toHaveLength(2);

      act(() => {
        result.current.switchBranch("main");
      });

      // Main branch should have all messages
      expect(result.current.currentBranch.messages).toHaveLength(4);
    });
  });

  describe("branch metadata", () => {
    it("should track branch point indicator", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      // Check if msg2 has branches
      const branchPoints = result.current.getBranchPoints();
      expect(branchPoints).toContain("msg2");
    });

    it("should get branches for a message", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2", "Branch 1");
        result.current.switchBranch("main");
        result.current.createBranch("msg2", "Branch 2");
      });

      const branchesAtMsg2 = result.current.getBranchesAtMessage("msg2");
      expect(branchesAtMsg2).toHaveLength(2);
    });

    it("should return empty array for message with no branches", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      const branchesAtMsg1 = result.current.getBranchesAtMessage("msg1");
      expect(branchesAtMsg1).toHaveLength(0);
    });
  });

  describe("branch deletion", () => {
    it("should delete a branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      const branchId = result.current.currentBranch.id;

      act(() => {
        result.current.switchBranch("main");
        result.current.deleteBranch(branchId);
      });

      expect(result.current.branches).toHaveLength(1);
      expect(result.current.branches[0].id).toBe("main");
    });

    it("should not allow deleting main branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      let success: boolean = true;
      act(() => {
        success = result.current.deleteBranch("main");
      });

      expect(success).toBe(false);
      expect(result.current.branches).toHaveLength(1);
    });

    it("should switch to main when current branch is deleted", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      const branchId = result.current.currentBranch.id;

      act(() => {
        result.current.deleteBranch(branchId);
      });

      expect(result.current.currentBranch.id).toBe("main");
    });
  });

  describe("branch renaming", () => {
    it("should rename a branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2", "Original Name");
      });

      const branchId = result.current.currentBranch.id;

      act(() => {
        result.current.renameBranch(branchId, "New Name");
      });

      const branch = result.current.branches.find((b) => b.id === branchId);
      expect(branch?.name).toBe("New Name");
    });

    it("should not rename non-existent branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      let success: boolean = true;
      act(() => {
        success = result.current.renameBranch("non-existent", "New Name");
      });

      expect(success).toBe(false);
    });
  });

  describe("adding messages to branch", () => {
    it("should add message to current branch", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      // Create branch first
      act(() => {
        result.current.createBranch("msg2");
      });

      // Then add message in separate act to ensure state is updated
      act(() => {
        result.current.addMessageToBranch({
          id: "msg5",
          role: "user",
          content: "New message in branch",
        });
      });

      expect(result.current.currentBranch.messages).toHaveLength(3);
      expect(result.current.currentBranch.messages[2].content).toBe(
        "New message in branch",
      );
    });

    it("should not affect other branches when adding message", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      // Create branch first
      act(() => {
        result.current.createBranch("msg2");
      });

      // Then add message in separate act to ensure state is updated
      act(() => {
        result.current.addMessageToBranch({
          id: "msg5",
          role: "user",
          content: "New message in branch",
        });
      });

      const mainBranch = result.current.branches.find((b) => b.id === "main");
      expect(mainBranch?.messages).toHaveLength(4);
    });
  });

  describe("branch comparison", () => {
    it("should identify divergence point between branches", () => {
      const { result } = renderHook(() => useBranching(mockMessages));

      act(() => {
        result.current.createBranch("msg2");
      });

      const branchId = result.current.currentBranch.id;
      const divergence = result.current.getDivergencePoint("main", branchId);

      expect(divergence).toBe("msg2");
    });
  });
});
