# React Router Integration

This document describes how to test components that use React Router v7 features.

## Table of Contents

- [Testing with Loaders](#testing-with-loaders)
- [Mocking Router Hooks](#mocking-router-hooks)
- [Testing Navigation](#testing-navigation)
- [Data Router Patterns](#data-router-patterns)

---

## Testing with Loaders

Components using `useRouteLoaderData` need router mocking:

```typescript
// Define mock data
const mockLoaderData: ChatLoaderData = {
  sessionId: "session-123",
  messages: [],
  artifacts: [createMockArtifact()],
};

// Mock the router
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") return mockLoaderData;
      return undefined;
    }),
  };
});

// Test the component
it("should display artifacts from loader", () => {
  render(<ConnectedCanvasPanel />, { wrapper });
  expect(screen.getByTestId("artifact-tab-artifact-1")).toBeInTheDocument();
});
```

---

## Mocking Router Hooks

### useRevalidator

```typescript
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRevalidator: vi.fn(() => ({
      revalidate: vi.fn(),
      state: "idle", // "idle" | "loading"
    })),
  };
});
```

### useNavigate

```typescript
const mockNavigate = vi.fn();

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Test navigation
it("should navigate to session on click", async () => {
  await user.click(screen.getByText("New Chat"));
  expect(mockNavigate).toHaveBeenCalledWith("/studio/v2/chat/new-session-id");
});
```

### useParams

```typescript
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useParams: () => ({ sessionId: "test-session-123" }),
  };
});
```

---

## Testing Navigation

### Testing Route Changes

```typescript
describe("Navigation", () => {
  it("should update URL when selecting artifact", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/studio/v2/chat/session-1"]}>
        <Routes>
          <Route path="/studio/v2/chat/:sessionId" element={<ChatPage />} />
        </Routes>
      </MemoryRouter>
    );

    await user.click(screen.getByTestId("artifact-tab-2"));

    // Verify navigation occurred
    expect(mockNavigate).toHaveBeenCalled();
  });
});
```

### Testing with Outlets

```typescript
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <MemoryRouter>
    <Routes>
      <Route path="/" element={<>{children}<Outlet /></>}>
        <Route path="nested" element={<div>Nested Content</div>} />
      </Route>
    </Routes>
  </MemoryRouter>
);
```

---

## Data Router Patterns

### Loader Integration in Tests

```typescript
// For components that use loader data directly
const createTestRouter = (loaderData: ChatLoaderData) => {
  return createMemoryRouter([
    {
      path: "/",
      element: <ChatPage />,
      loader: () => loaderData,
    },
  ]);
};

it("should render with loader data", async () => {
  const router = createTestRouter(mockLoaderData);
  render(<RouterProvider router={router} />);

  await waitFor(() => {
    expect(screen.getByText("Session Title")).toBeInTheDocument();
  });
});
```

### Testing Revalidation

```typescript
it("should revalidate after save", async () => {
  const mockRevalidate = vi.fn();
  vi.mocked(useRevalidator).mockReturnValue({
    revalidate: mockRevalidate,
    state: "idle",
  });

  render(<ConnectedCanvasPanel />, { wrapper });

  await user.click(screen.getByTestId("save-button"));

  await waitFor(() => {
    expect(mockRevalidate).toHaveBeenCalled();
  });
});
```

---

## Related Documentation

- [Testing Patterns](./TESTING_PATTERNS.md)
- [Component Architecture](./ARCHITECTURE.md)
