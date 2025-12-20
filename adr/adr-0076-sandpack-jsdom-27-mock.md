# ADR-0076: Sandpack Mock for jsdom 27 Compatibility

## Status

Accepted

## Date

2025-12-19

## Context

During the frontend stack upgrade to Vitest 4 and jsdom 27, we encountered test failures caused by an incompatibility between jsdom 27's CSS parser and the Stitches CSS-in-JS library used by `@codesandbox/sandpack-react`.

### Problem Analysis

1. **jsdom 27 uses @acemir/cssom**: This CSS parser has stricter parsing rules than previous versions.

2. **Stitches CSS-in-JS syntax**: Stitches (used internally by Sandpack) generates CSS rules like `--sxs{--sxs:6}` which are valid CSS custom properties but fail @acemir/cssom parsing.

3. **Module initialization timing**: The error occurs at module import time when Stitches initializes, before any test setup code can patch the CSS behavior.

4. **Worker crashes**: The CSS parsing errors caused Node.js worker processes to crash with `uv__stream_destroy: Assertion failed`, preventing test execution.

### Affected Components

Components using Sandpack experienced test failures:
- `ChatPage.tsx` - Uses code sandbox preview
- `ArtifactRenderer.tsx` - Renders code artifacts
- `SandpackExecutor.tsx` - Executes code in sandbox
- `ChatMessage.tsx` - Displays code blocks with Sandpack

### Alternative Approaches Considered

1. **CSS Patching in setup.ts**: Attempted to mock `CSSStyleSheet.prototype.insertRule` and related methods. Failed because Stitches runs during module import, before setup.ts executes.

2. **jsdom 25 (downgrade)**: Would avoid the issue but prevents using latest jsdom features and security fixes.

3. **Different CSS parser**: @acemir/cssom is bundled with jsdom 27; replacing it is not straightforward.

## Decision

Create a complete mock for `@codesandbox/sandpack-react` that provides test-friendly implementations without loading Stitches CSS-in-JS.

### Implementation

1. **Mock file location**: `src/mocks/components/sandpack-react.ts`

2. **Vitest alias configuration** in `vitest.config.ts`:
   ```typescript
   resolve: {
     alias: {
       "@codesandbox/sandpack-react": path.resolve(
         __dirname,
         "./src/mocks/components/sandpack-react.ts",
       ),
     },
   },
   ```

3. **Mock components provided**:
   - `SandpackProvider` - Context provider with mock state
   - `SandpackLayout` - Simple flex container
   - `SandpackPreview` - Placeholder preview area
   - `SandpackCodeEditor` - Code display in pre tag
   - `SandpackConsole` - Console output placeholder
   - `SandpackFileExplorer` - File explorer placeholder
   - `SandpackThemeProvider` - Pass-through wrapper
   - `useSandpack` - Hook returning mock context

4. **Theme exports**:
   - `nightOwl`, `cobalt2`, `githubLight`, `sandpackDark` - Empty theme objects

### Files Created/Modified

| File | Change |
|------|--------|
| `src/mocks/components/sandpack-react.ts` | New mock implementation (230 lines) |
| `vitest.config.ts` | Added Sandpack alias (lines 96-99) |

## Consequences

### Positive

1. **Tests execute successfully**: 151+ tests that previously crashed now pass
2. **No Stitches loading**: Avoids CSS-in-JS initialization entirely
3. **Fast execution**: Mock is lightweight with no external dependencies
4. **Stable**: Not affected by upstream Sandpack or Stitches changes
5. **Type-safe**: Mock includes TypeScript types matching Sandpack API

### Negative

1. **Sandpack functionality not tested**: The mock does not test actual Sandpack behavior
2. **Mock maintenance**: If Sandpack API changes, mock needs updates
3. **Test coverage gap**: Code editor, preview, and console features are not validated in unit tests

### Mitigations

1. **E2E tests**: Playwright E2E tests exercise actual Sandpack functionality in real browser
2. **Manual testing**: Development server uses real Sandpack for visual verification
3. **API monitoring**: Component interfaces document expected Sandpack props

## Removal Criteria

This mock can be removed when ANY of the following conditions are met:

1. **jsdom fixes CSS parsing**: @acemir/cssom accepts Stitches CSS syntax
2. **Stitches updates syntax**: Stitches generates CSS compatible with strict parsers
3. **Sandpack removes Stitches**: Sandpack migrates to different styling solution
4. **Alternative testing environment**: Switch to happy-dom or other jsdom alternative

Track upstream issues:
- jsdom: https://github.com/jsdom/jsdom/issues
- Stitches: https://github.com/stitchesjs/stitches/issues
- Sandpack: https://github.com/codesandbox/sandpack/issues

## References

- [jsdom 27 Release Notes](https://github.com/jsdom/jsdom/releases)
- [Stitches CSS-in-JS](https://stitches.dev/)
- [Sandpack React Library](https://sandpack.codesandbox.io/)
- [Vitest Module Mocking](https://vitest.dev/guide/mocking.html)

## Known Issue: Worker Crash on Cleanup

After test completion, an intermittent libuv assertion failure may occur:

```
node: src/unix/stream.c:456: uv__stream_destroy: Assertion
`!uv__io_active(&stream->io_watcher, POLLIN | POLLOUT)' failed.
```

### Behavior

- All tests complete and pass correctly BEFORE the crash
- The crash occurs during worker process cleanup, NOT during tests
- Does NOT affect test results or coverage
- Non-deterministic - may not occur on every run

### Root Cause

This is a libuv race condition where stream handles are still active when
the worker process attempts to exit. It's triggered by jsdom's interaction
with native I/O operations. Common triggers include:

1. MSW (Mock Service Worker) cleanup
2. WebSocket mock cleanup
3. Service Worker registration mocks

### Mitigations Implemented

1. Service worker mock in `setup.ts` to prevent undefined property access
2. Global unhandledRejection/uncaughtException handlers
3. Using `pool: 'forks'` for better process isolation

### Tracking

- Node.js issue: https://github.com/nodejs/node/issues/30507
- Vitest issue: https://github.com/vitest-dev/vitest/issues/1171

### Status

**Accepted risk** - The crash is cosmetic and doesn't affect test reliability.
All 5600+ tests pass correctly before the worker cleanup crash.

## Related ADRs

- ADR-0044: Test Infrastructure Quick Wins
- ADR-0052: pytest-xdist Isolation Strategy
