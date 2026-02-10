/**
 * StatusBar Test Fixtures
 *
 * Shared mocks and test data for StatusBar test shards.
 */
import { vi } from "vitest";

/**
 * Mock FeatureFlagToggle component
 * Used across all StatusBar test shards
 */
export const mockFeatureFlagToggle = () => {
  vi.mock("../FeatureFlagToggle", () => ({
    FeatureFlagToggle: ({ isDev }: { isDev: boolean }) => (
      <div data-testid="feature-flag-toggle" data-is-dev={isDev}>
        Feature Flag Toggle
      </div>
    ),
  }));
};
