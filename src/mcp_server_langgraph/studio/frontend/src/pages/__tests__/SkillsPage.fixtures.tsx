import { vi } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import { api } from "../../api";

// Mock RTK Query hooks
export const mockListMarketplaceSkillsQuery = vi.fn(() => ({
  data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
}));

export const mockListInstalledSkillsQuery = vi.fn(() => ({
  data: { skills: [], count: 0 },
  isLoading: false,
  refetch: vi.fn(),
}));

export const mockCheckSkillUpdatesQuery = vi.fn(() => ({
  data: [],
  isLoading: false,
  refetch: vi.fn(),
}));

export const mockInstallSkillMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);
export const mockUninstallSkillMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);
export const mockApplySkillUpdatesMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);

// Mock marketplace management hooks
export const mockListMarketplacesQuery = vi.fn(() => ({
  data: {
    marketplaces: [
      {
        name: "anthropic",
        uri: "https://github.com/anthropics/skills-marketplace",
        type: "github",
        trusted: true,
        autoSync: true,
        requiresApproval: false,
      },
    ],
  },
  isLoading: false,
  error: null,
  refetch: vi.fn(),
}));

export const mockAddMarketplaceMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);
export const mockRemoveMarketplaceMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);
export const mockSyncMarketplaceMutation = vi.fn(() => [
  vi.fn(),
  { isLoading: false },
]);

// Mock useFeatureFlags hook
export const mockUseFeatureFlags = vi.fn(() => ({
  flags: { skills_marketplace: true },
  isLoading: false,
  isError: false,
  isEnabled: (flag: string) => flag === "skills_marketplace",
}));

// Helper to create a test store
export const createTestStore = () => {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
};

// Mock skill data
export const mockSkills = [
  {
    name: "web-research",
    description: "Search the web for information",
    version: "1.0.0",
    author: "Anthropic",
    tags: ["research", "web"],
  },
  {
    name: "code-review",
    description: "Review and analyze code",
    version: "2.1.0",
    author: "Community",
    tags: ["development", "code"],
  },
];

export function resetAllMocks() {
  mockListMarketplaceSkillsQuery.mockReturnValue({
    data: { skills: [], total: 0, marketplace: "anthropic", cached: false },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  });
  mockListInstalledSkillsQuery.mockReturnValue({
    data: { skills: [], count: 0 },
    isLoading: false,
    refetch: vi.fn(),
  });
  mockCheckSkillUpdatesQuery.mockReturnValue({
    data: [],
    isLoading: false,
    refetch: vi.fn(),
  });
  mockInstallSkillMutation.mockReturnValue([vi.fn(), { isLoading: false }]);
  mockUninstallSkillMutation.mockReturnValue([vi.fn(), { isLoading: false }]);
  mockApplySkillUpdatesMutation.mockReturnValue([
    vi.fn(),
    { isLoading: false },
  ]);
  mockUseFeatureFlags.mockReturnValue({
    flags: { skills_marketplace: true },
    isLoading: false,
    isError: false,
    isEnabled: (flag: string) => flag === "skills_marketplace",
  });
}
