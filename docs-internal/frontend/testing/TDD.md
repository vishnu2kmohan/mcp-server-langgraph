# Test-Driven Development (TDD) Guidelines

This document describes the TDD workflow for the Studio Frontend codebase.

## Table of Contents

- [Red-Green-Refactor Cycle](#red-green-refactor-cycle)
- [Writing Effective Tests](#writing-effective-tests)
- [Test Naming Conventions](#test-naming-conventions)
- [Coverage Requirements](#coverage-requirements)

---

## Red-Green-Refactor Cycle

TDD follows a strict three-phase cycle:

### 1. RED: Write a Failing Test

```typescript
it("should display error message when save fails", async () => {
  // Arrange: Setup mocks to simulate failure
  vi.spyOn(global, "fetch").mockRejectedValueOnce(new Error("Network error"));

  // Act: Trigger the save action
  await user.click(screen.getByTestId("save-button"));

  // Assert: Verify error is displayed
  await waitFor(() => {
    expect(screen.getByText(/network error/i)).toBeInTheDocument();
  });
});
```

**Run the test to verify it fails** - This proves the test is valid.

### 2. GREEN: Write Minimal Code to Pass

Implement just enough code to make the test pass. Don't add features not covered by tests.

### 3. REFACTOR: Improve Code Quality

Clean up the implementation while keeping all tests green:
- Remove duplication
- Improve naming
- Extract functions
- Run tests after each change

---

## Writing Effective Tests

### GIVEN-WHEN-THEN Structure

```typescript
it("should show saved status after successful save", async () => {
  // GIVEN: A component with artifacts
  const store = createTestStore({ artifacts: [mockArtifact] });
  render(<MyComponent />, { wrapper: createWrapper(store) });

  // WHEN: User saves content
  await user.click(screen.getByTestId("save-button"));

  // THEN: Saved indicator appears
  await waitFor(() => {
    expect(screen.getByText(/saved/i)).toBeInTheDocument();
  });
});
```

### Test One Thing Per Test

```typescript
// Good: Focused tests
it("should show loading indicator during save", async () => { /* ... */ });
it("should show success message after save", async () => { /* ... */ });
it("should show error message when save fails", async () => { /* ... */ });

// Bad: Testing multiple behaviors
it("should handle save operation", async () => {
  // Shows loading, then success, and handles errors...
});
```

---

## Test Naming Conventions

Use descriptive names that explain WHAT and WHY:

```typescript
// Pattern: should [expected behavior] when [condition]
it("should display error message when network request fails")
it("should disable submit button when form is invalid")
it("should call onSave callback when save completes successfully")
```

---

## Coverage Requirements

| Category | Minimum | Target |
|----------|---------|--------|
| Redux Slices | 95% | 100% |
| Connected Components | 70% | 80% |
| UI Components | 80% | 85% |
| Hooks | 90% | 95% |
| Utilities | 95% | 100% |

---

## Related Documentation

- [Testing Patterns](./TESTING_PATTERNS.md)
- [Test Isolation](./TEST_ISOLATION.md)
- [OOM Prevention](./TESTING_OOM_PREVENTION.md)
