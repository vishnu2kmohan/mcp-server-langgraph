/**
 * Artifact Slice Tests
 *
 * TDD tests for artifact Redux slice.
 */

import { describe, it, expect } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import artifactReducer, {
  initialArtifactState,
  addArtifact,
  removeArtifact,
  updateArtifact,
  selectArtifact,
  clearArtifactSelection,
  clearArtifacts,
  selectArtifacts,
  selectSelectedArtifactId,
  selectArtifactById,
  selectArtifactsByType,
  selectSelectedArtifact,
} from "./artifactSlice";
import type { ArtifactSliceState } from "./artifactSlice";
import type {
  CodeArtifact,
  JSONArtifact,
  ChartArtifact,
} from "../../types/artifacts";

// Helper to create a test store
const createTestStore = (preloadedState?: Partial<ArtifactSliceState>) => {
  return configureStore({
    reducer: { artifact: artifactReducer },
    preloadedState: preloadedState
      ? { artifact: { ...initialArtifactState, ...preloadedState } }
      : undefined,
  });
};

describe("artifactSlice", () => {
  describe("Initial State", () => {
    it("should have empty artifacts array", () => {
      const store = createTestStore();
      expect(selectArtifacts(store.getState())).toEqual([]);
    });

    it("should have no selected artifact", () => {
      const store = createTestStore();
      expect(selectSelectedArtifactId(store.getState())).toBeNull();
    });
  });

  describe("addArtifact", () => {
    it("should add a code artifact", () => {
      const store = createTestStore();
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: 'console.log("hello");',
        config: {
          language: "javascript",
        },
      };

      store.dispatch(addArtifact(artifact));

      const artifacts = selectArtifacts(store.getState());
      expect(artifacts).toHaveLength(1);
      expect(artifacts[0]).toEqual(artifact);
    });

    it("should add a JSON artifact", () => {
      const store = createTestStore();
      const artifact: JSONArtifact = {
        id: "json-1",
        type: "json",
        data: { foo: "bar", count: 42 },
      };

      store.dispatch(addArtifact(artifact));

      const artifacts = selectArtifacts(store.getState());
      expect(artifacts).toHaveLength(1);
      expect(artifacts[0]).toEqual(artifact);
    });

    it("should add multiple artifacts", () => {
      const store = createTestStore();
      const artifact1: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: 'print("hello")',
        config: { language: "python" },
      };

      const artifact2: JSONArtifact = {
        id: "json-1",
        type: "json",
        data: { status: "ok" },
      };

      store.dispatch(addArtifact(artifact1));
      store.dispatch(addArtifact(artifact2));

      const artifacts = selectArtifacts(store.getState());
      expect(artifacts).toHaveLength(2);
      expect(artifacts[0].id).toBe("code-1");
      expect(artifacts[1].id).toBe("json-1");
    });
  });

  describe("removeArtifact", () => {
    it("should remove artifact by id", () => {
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test",
        config: { language: "javascript" },
      };

      const store = createTestStore({ artifacts: [artifact] });
      expect(selectArtifacts(store.getState())).toHaveLength(1);

      store.dispatch(removeArtifact("code-1"));
      expect(selectArtifacts(store.getState())).toHaveLength(0);
    });

    it("should do nothing if artifact not found", () => {
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test",
        config: { language: "javascript" },
      };

      const store = createTestStore({ artifacts: [artifact] });
      store.dispatch(removeArtifact("non-existent"));

      expect(selectArtifacts(store.getState())).toHaveLength(1);
    });

    it("should clear selection if removing selected artifact", () => {
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test",
        config: { language: "javascript" },
      };

      const store = createTestStore({
        artifacts: [artifact],
        selectedArtifactId: "code-1",
      });

      expect(selectSelectedArtifactId(store.getState())).toBe("code-1");

      store.dispatch(removeArtifact("code-1"));
      expect(selectSelectedArtifactId(store.getState())).toBeNull();
    });
  });

  describe("updateArtifact", () => {
    it("should update artifact data", () => {
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "old code",
        config: { language: "javascript" },
      };

      const store = createTestStore({ artifacts: [artifact] });
      store.dispatch(
        updateArtifact({ id: "code-1", updates: { data: "new code" } }),
      );

      const updated = selectArtifacts(store.getState())[0] as CodeArtifact;
      expect(updated.data).toBe("new code");
      expect(updated.config.language).toBe("javascript"); // Other properties preserved
    });

    it("should update artifact title", () => {
      const artifact: JSONArtifact = {
        id: "json-1",
        type: "json",
        data: { test: true },
      };

      const store = createTestStore({ artifacts: [artifact] });
      store.dispatch(
        updateArtifact({ id: "json-1", updates: { title: "Test Data" } }),
      );

      const updated = selectArtifacts(store.getState())[0];
      expect(updated.title).toBe("Test Data");
    });

    it("should do nothing if artifact not found", () => {
      const store = createTestStore();
      store.dispatch(
        updateArtifact({ id: "non-existent", updates: { title: "Test" } }),
      );
      expect(selectArtifacts(store.getState())).toHaveLength(0);
    });
  });

  describe("selectArtifact", () => {
    it("should select artifact by id", () => {
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test",
        config: { language: "javascript" },
      };

      const store = createTestStore({ artifacts: [artifact] });
      store.dispatch(selectArtifact("code-1"));

      expect(selectSelectedArtifactId(store.getState())).toBe("code-1");
    });

    it("should change selection", () => {
      const artifact1: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test1",
        config: { language: "javascript" },
      };

      const artifact2: CodeArtifact = {
        id: "code-2",
        type: "code",
        data: "test2",
        config: { language: "python" },
      };

      const store = createTestStore({ artifacts: [artifact1, artifact2] });

      store.dispatch(selectArtifact("code-1"));
      expect(selectSelectedArtifactId(store.getState())).toBe("code-1");

      store.dispatch(selectArtifact("code-2"));
      expect(selectSelectedArtifactId(store.getState())).toBe("code-2");
    });
  });

  describe("clearArtifactSelection", () => {
    it("should clear selected artifact", () => {
      const artifact: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test",
        config: { language: "javascript" },
      };

      const store = createTestStore({
        artifacts: [artifact],
        selectedArtifactId: "code-1",
      });

      expect(selectSelectedArtifactId(store.getState())).toBe("code-1");

      store.dispatch(clearArtifactSelection());
      expect(selectSelectedArtifactId(store.getState())).toBeNull();
    });
  });

  describe("clearArtifacts", () => {
    it("should remove all artifacts", () => {
      const artifact1: CodeArtifact = {
        id: "code-1",
        type: "code",
        data: "test1",
        config: { language: "javascript" },
      };

      const artifact2: JSONArtifact = {
        id: "json-1",
        type: "json",
        data: { test: true },
      };

      const store = createTestStore({
        artifacts: [artifact1, artifact2],
        selectedArtifactId: "code-1",
      });

      expect(selectArtifacts(store.getState())).toHaveLength(2);

      store.dispatch(clearArtifacts());
      expect(selectArtifacts(store.getState())).toHaveLength(0);
      expect(selectSelectedArtifactId(store.getState())).toBeNull();
    });
  });

  describe("Selectors", () => {
    describe("selectArtifactById", () => {
      it("should return artifact by id", () => {
        const artifact: CodeArtifact = {
          id: "code-1",
          type: "code",
          data: "test",
          config: { language: "javascript" },
        };

        const store = createTestStore({ artifacts: [artifact] });
        const found = selectArtifactById("code-1")(store.getState());

        expect(found).toEqual(artifact);
      });

      it("should return undefined if not found", () => {
        const store = createTestStore();
        const found = selectArtifactById("non-existent")(store.getState());
        expect(found).toBeUndefined();
      });
    });

    describe("selectArtifactsByType", () => {
      it("should return artifacts of specific type", () => {
        const codeArtifact: CodeArtifact = {
          id: "code-1",
          type: "code",
          data: "test",
          config: { language: "javascript" },
        };

        const jsonArtifact: JSONArtifact = {
          id: "json-1",
          type: "json",
          data: { test: true },
        };

        const chartArtifact: ChartArtifact = {
          id: "chart-1",
          type: "chart",
          data: [{ x: 1, y: 2 }],
          config: { chartType: "line" },
        };

        const store = createTestStore({
          artifacts: [codeArtifact, jsonArtifact, chartArtifact],
        });

        const codeArtifacts = selectArtifactsByType("code")(store.getState());
        expect(codeArtifacts).toHaveLength(1);
        expect(codeArtifacts[0].id).toBe("code-1");

        const jsonArtifacts = selectArtifactsByType("json")(store.getState());
        expect(jsonArtifacts).toHaveLength(1);
        expect(jsonArtifacts[0].id).toBe("json-1");
      });

      it("should return empty array if no artifacts of type", () => {
        const store = createTestStore();
        const artifacts = selectArtifactsByType("mermaid")(store.getState());
        expect(artifacts).toEqual([]);
      });
    });

    describe("selectSelectedArtifact", () => {
      it("should return selected artifact", () => {
        const artifact: CodeArtifact = {
          id: "code-1",
          type: "code",
          data: "test",
          config: { language: "javascript" },
        };

        const store = createTestStore({
          artifacts: [artifact],
          selectedArtifactId: "code-1",
        });

        const selected = selectSelectedArtifact(store.getState());
        expect(selected).toEqual(artifact);
      });

      it("should return null if no selection", () => {
        const store = createTestStore();
        const selected = selectSelectedArtifact(store.getState());
        expect(selected).toBeNull();
      });
    });
  });
});
