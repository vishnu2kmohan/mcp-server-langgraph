/**
 * executionModeSlice Tests
 *
 * Tests for Redux slice managing execution mode toggling and plan approval workflow.
 * Implements Ctrl/Cmd+Shift+M mode cycling (default → plan → auto_accept → bypass → default)
 * with OpenFGA permission enforcement for bypass mode.
 */

import { describe, it, expect } from "vitest";
import executionModeReducer, {
  setExecutionMode,
  cycleExecutionMode,
  setPlan,
  clearPlan,
  setPlanStatus,
  setUserIsAdmin,
  setHasBypassPermission,
  selectExecutionMode,
  selectCurrentPlan,
  selectPlanStatus,
  selectShowPlanApproval,
  selectUserIsAdmin,
  selectHasBypassPermission,
  selectCanBypass,
  type ExecutionModeState,
  type ExecutionPlan,
} from "./executionModeSlice";

describe("executionModeSlice", () => {
  const initialState: ExecutionModeState = {
    executionMode: "default",
    currentPlan: null,
    currentRoutingDecision: null,
    planStatus: "idle",
    userIsAdmin: false,
    hasBypassPermission: false,
  };

  // Sample plan for testing
  const samplePlan: ExecutionPlan = {
    planId: "plan-123",
    sessionId: "session-456",
    status: "awaiting_approval",
    complexity: "complicated",
    riskLevel: "medium",
    taskType: "code_generation",
    executorModel: "claude-opus-4-5",
    criticModel: "claude-sonnet-4",
    estimatedCost: "0.15",
    message: "Write a function to sort an array",
    toolsNeeded: ["code_executor", "file_writer"],
    thinkingBudget: "medium",
    critiqueRounds: 1,
    orchestrator: "standard",
    requiresApproval: true,
  };

  describe("Initial State", () => {
    it("should have correct initial state", () => {
      const state = executionModeReducer(undefined, { type: "unknown" });
      expect(state).toEqual(initialState);
    });

    it("should default to 'default' execution mode", () => {
      const state = executionModeReducer(undefined, { type: "unknown" });
      expect(state.executionMode).toBe("default");
    });

    it("should default to non-admin user", () => {
      const state = executionModeReducer(undefined, { type: "unknown" });
      expect(state.userIsAdmin).toBe(false);
    });
  });

  describe("setExecutionMode", () => {
    it("should set execution mode to 'plan'", () => {
      const state = executionModeReducer(
        initialState,
        setExecutionMode("plan"),
      );
      expect(state.executionMode).toBe("plan");
    });

    it("should set execution mode to 'auto_accept'", () => {
      const state = executionModeReducer(
        initialState,
        setExecutionMode("auto_accept"),
      );
      expect(state.executionMode).toBe("auto_accept");
    });

    it("should set execution mode to 'bypass' when user is admin", () => {
      const adminState = { ...initialState, userIsAdmin: true };
      const state = executionModeReducer(adminState, setExecutionMode("bypass"));
      expect(state.executionMode).toBe("bypass");
    });

    it("should NOT set execution mode to 'bypass' when user is not admin", () => {
      const state = executionModeReducer(
        initialState,
        setExecutionMode("bypass"),
      );
      // Should remain at default since bypass requires admin
      expect(state.executionMode).toBe("default");
    });
  });

  describe("cycleExecutionMode", () => {
    it("should cycle from default → plan", () => {
      const state = executionModeReducer(initialState, cycleExecutionMode());
      expect(state.executionMode).toBe("plan");
    });

    it("should cycle from plan → auto_accept", () => {
      const planState = { ...initialState, executionMode: "plan" as const };
      const state = executionModeReducer(planState, cycleExecutionMode());
      expect(state.executionMode).toBe("auto_accept");
    });

    it("should cycle from auto_accept → default for non-admin", () => {
      const autoState = {
        ...initialState,
        executionMode: "auto_accept" as const,
      };
      const state = executionModeReducer(autoState, cycleExecutionMode());
      // Skip bypass for non-admin, go to default
      expect(state.executionMode).toBe("default");
    });

    it("should cycle from auto_accept → bypass for admin", () => {
      const adminAutoState = {
        ...initialState,
        executionMode: "auto_accept" as const,
        userIsAdmin: true,
      };
      const state = executionModeReducer(adminAutoState, cycleExecutionMode());
      expect(state.executionMode).toBe("bypass");
    });

    it("should cycle from bypass → default for admin", () => {
      const bypassState = {
        ...initialState,
        executionMode: "bypass" as const,
        userIsAdmin: true,
      };
      const state = executionModeReducer(bypassState, cycleExecutionMode());
      expect(state.executionMode).toBe("default");
    });

    it("should complete full cycle for admin: default → plan → auto_accept → bypass → default", () => {
      let state: ExecutionModeState = { ...initialState, userIsAdmin: true };

      // default → plan
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("plan");

      // plan → auto_accept
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("auto_accept");

      // auto_accept → bypass
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("bypass");

      // bypass → default
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("default");
    });

    it("should complete full cycle for non-admin: default → plan → auto_accept → default", () => {
      let state: ExecutionModeState = { ...initialState, userIsAdmin: false };

      // default → plan
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("plan");

      // plan → auto_accept
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("auto_accept");

      // auto_accept → default (skip bypass)
      state = executionModeReducer(state, cycleExecutionMode());
      expect(state.executionMode).toBe("default");
    });
  });

  describe("setUserIsAdmin", () => {
    it("should set userIsAdmin to true", () => {
      const state = executionModeReducer(initialState, setUserIsAdmin(true));
      expect(state.userIsAdmin).toBe(true);
    });

    it("should set userIsAdmin to false", () => {
      const adminState = { ...initialState, userIsAdmin: true };
      const state = executionModeReducer(adminState, setUserIsAdmin(false));
      expect(state.userIsAdmin).toBe(false);
    });

    it("should reset bypass mode to default when admin is revoked", () => {
      const bypassState = {
        ...initialState,
        executionMode: "bypass" as const,
        userIsAdmin: true,
      };
      const state = executionModeReducer(bypassState, setUserIsAdmin(false));
      expect(state.userIsAdmin).toBe(false);
      expect(state.executionMode).toBe("default");
    });
  });

  describe("Plan Management", () => {
    it("should set plan and update status to awaiting_approval", () => {
      const state = executionModeReducer(initialState, setPlan(samplePlan));

      expect(state.currentPlan).toEqual(samplePlan);
      expect(state.planStatus).toBe("awaiting_approval");
    });

    it("should clear plan and reset status to idle", () => {
      const stateWithPlan = {
        ...initialState,
        currentPlan: samplePlan,
        planStatus: "awaiting_approval" as const,
      };

      const state = executionModeReducer(stateWithPlan, clearPlan());

      expect(state.currentPlan).toBeNull();
      expect(state.planStatus).toBe("idle");
    });

    it("should update plan status to approved", () => {
      const stateWithPlan = {
        ...initialState,
        currentPlan: samplePlan,
        planStatus: "awaiting_approval" as const,
      };

      const state = executionModeReducer(
        stateWithPlan,
        setPlanStatus("approved"),
      );

      expect(state.planStatus).toBe("approved");
    });

    it("should update plan status to rejected", () => {
      const stateWithPlan = {
        ...initialState,
        currentPlan: samplePlan,
        planStatus: "awaiting_approval" as const,
      };

      const state = executionModeReducer(
        stateWithPlan,
        setPlanStatus("rejected"),
      );

      expect(state.planStatus).toBe("rejected");
    });

    it("should update currentPlan.status when setPlanStatus is called", () => {
      const stateWithPlan = {
        ...initialState,
        currentPlan: samplePlan,
        planStatus: "awaiting_approval" as const,
      };

      const state = executionModeReducer(
        stateWithPlan,
        setPlanStatus("approved"),
      );

      expect(state.currentPlan?.status).toBe("approved");
    });
  });

  describe("Selectors", () => {
    const mockRootState = {
      executionMode: {
        executionMode: "plan" as const,
        currentPlan: samplePlan,
        planStatus: "awaiting_approval" as const,
        userIsAdmin: true,
      },
    };

    it("selectExecutionMode should return current execution mode", () => {
      const result = selectExecutionMode(mockRootState);
      expect(result).toBe("plan");
    });

    it("selectCurrentPlan should return current plan", () => {
      const result = selectCurrentPlan(mockRootState);
      expect(result).toEqual(samplePlan);
    });

    it("selectPlanStatus should return plan status", () => {
      const result = selectPlanStatus(mockRootState);
      expect(result).toBe("awaiting_approval");
    });

    it("selectUserIsAdmin should return admin status", () => {
      const result = selectUserIsAdmin(mockRootState);
      expect(result).toBe(true);
    });

    it("selectShowPlanApproval should return true when plan requires approval", () => {
      const result = selectShowPlanApproval(mockRootState);
      expect(result).toBe(true);
    });

    it("selectShowPlanApproval should return false when no plan", () => {
      const noPlanState = {
        executionMode: {
          executionMode: "default" as const,
          currentPlan: null,
          planStatus: "idle" as const,
          userIsAdmin: false,
        },
      };
      const result = selectShowPlanApproval(noPlanState);
      expect(result).toBe(false);
    });

    it("selectShowPlanApproval should return false when plan does not require approval", () => {
      const autoApprovedState = {
        executionMode: {
          executionMode: "auto_accept" as const,
          currentPlan: { ...samplePlan, requiresApproval: false },
          planStatus: "idle" as const,
          userIsAdmin: false,
        },
      };
      const result = selectShowPlanApproval(autoApprovedState);
      expect(result).toBe(false);
    });
  });

  describe("Edge Cases", () => {
    it("should handle setting same mode without error", () => {
      const state = executionModeReducer(
        initialState,
        setExecutionMode("default"),
      );
      expect(state.executionMode).toBe("default");
    });

    it("should handle clearing plan when no plan exists", () => {
      const state = executionModeReducer(initialState, clearPlan());
      expect(state.currentPlan).toBeNull();
      expect(state.planStatus).toBe("idle");
    });

    it("should handle setting plan status when no plan exists", () => {
      // Should not crash, just update status
      const state = executionModeReducer(
        initialState,
        setPlanStatus("approved"),
      );
      expect(state.planStatus).toBe("approved");
      expect(state.currentPlan).toBeNull();
    });
  });

  describe("setHasBypassPermission (OpenFGA)", () => {
    it("should set hasBypassPermission to true", () => {
      const state = executionModeReducer(
        initialState,
        setHasBypassPermission(true),
      );
      expect(state.hasBypassPermission).toBe(true);
    });

    it("should set hasBypassPermission to false", () => {
      const permittedState = { ...initialState, hasBypassPermission: true };
      const state = executionModeReducer(
        permittedState,
        setHasBypassPermission(false),
      );
      expect(state.hasBypassPermission).toBe(false);
    });

    it("should reset bypass mode when permission is revoked (and no admin)", () => {
      const bypassState = {
        ...initialState,
        executionMode: "bypass" as const,
        hasBypassPermission: true,
      };
      const state = executionModeReducer(
        bypassState,
        setHasBypassPermission(false),
      );
      expect(state.executionMode).toBe("default");
      expect(state.hasBypassPermission).toBe(false);
    });

    it("should NOT reset bypass mode when permission is revoked but user is admin", () => {
      const bypassState = {
        ...initialState,
        executionMode: "bypass" as const,
        hasBypassPermission: true,
        userIsAdmin: true,
      };
      const state = executionModeReducer(
        bypassState,
        setHasBypassPermission(false),
      );
      // Bypass should remain because user is admin
      expect(state.executionMode).toBe("bypass");
      expect(state.hasBypassPermission).toBe(false);
    });

    it("should allow bypass mode with hasBypassPermission (not just admin)", () => {
      const permittedState = { ...initialState, hasBypassPermission: true };
      const state = executionModeReducer(
        permittedState,
        setExecutionMode("bypass"),
      );
      expect(state.executionMode).toBe("bypass");
    });
  });

  describe("selectCanBypass", () => {
    it("should return true when hasBypassPermission is true", () => {
      const state = {
        executionMode: { ...initialState, hasBypassPermission: true },
      };
      expect(selectCanBypass(state)).toBe(true);
    });

    it("should return true when userIsAdmin is true", () => {
      const state = {
        executionMode: { ...initialState, userIsAdmin: true },
      };
      expect(selectCanBypass(state)).toBe(true);
    });

    it("should return true when both are true", () => {
      const state = {
        executionMode: {
          ...initialState,
          hasBypassPermission: true,
          userIsAdmin: true,
        },
      };
      expect(selectCanBypass(state)).toBe(true);
    });

    it("should return false when neither is true", () => {
      const state = {
        executionMode: initialState,
      };
      expect(selectCanBypass(state)).toBe(false);
    });
  });

  describe("selectHasBypassPermission", () => {
    it("should return hasBypassPermission value", () => {
      const state = {
        executionMode: { ...initialState, hasBypassPermission: true },
      };
      expect(selectHasBypassPermission(state)).toBe(true);
    });
  });
});
