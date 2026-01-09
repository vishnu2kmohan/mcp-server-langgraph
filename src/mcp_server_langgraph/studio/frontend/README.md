# Studio Frontend

Unified Studio Frontend for MCP Server LangGraph - Consolidates Builder and Playground.

## Quick Start

```bash
# Install dependencies
npm install

# Development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## Testing

### Unit Tests (Vitest)

```bash
npm test                 # Watch mode
npm run test:run         # Single run
npm run test:coverage    # With coverage
```

### E2E Tests (Playwright)

```bash
npm run test:e2e         # Run all E2E tests
npm run test:e2e:ui      # Interactive UI mode
npm run test:e2e:headed  # Show browser
```

### Testing Documentation

For comprehensive testing patterns and guidelines, see:

- **Testing Patterns**: `docs-internal/frontend/testing/TESTING_PATTERNS.md`
  - Provider wrappers, mock factories, common scenarios

- **OOM Prevention**: `docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md`
  - Critical patterns to avoid memory issues in Vitest tests
  - High-risk dependencies and safe mocking patterns

## Project Structure

```
src/
├── ai/                 # AI features (suggestions, command palette)
├── canvas/             # Canvas workspace components
├── compliance/         # Compliance dashboard panels
├── components/         # Shared UI components
├── contexts/           # React contexts
├── conversation/       # Chat/conversation components
├── help/               # Help and accessibility
├── hooks/              # Custom React hooks
├── layout/             # Layout components (StudioShell, TopBar, etc.)
├── pages/              # Page components
├── router/             # React Router configuration
├── store/              # Redux store and slices
├── types/              # TypeScript types
└── utils/              # Utility functions
```

## Architecture

The frontend uses a **Studio Shell Layout** pattern:

- **ActivityBar**: Left navigation (Chat, Workflows, Agents, etc.)
- **SessionNav**: Session/conversation list
- **ConversationPanel**: Chat messages and input
- **CanvasWorkspace**: Artifact editing and preview
- **TopBar**: Persona-aware header with user menu
- **StatusBar**: Connection status, model, tokens

## Internal Documentation

Additional frontend-specific documentation is in `docs-internal/frontend/`:

- **`DESIGN_SYSTEM.md`** - Design tokens, UI components, AI-Native patterns
  - Semantic colors, CVA variants, accessibility
  - AIEmptyState, CommandPaletteContext, WidgetArtifact
  - Chat Input features and feature flags
- `FRONTEND_API_AUDIT.md` - API endpoint usage
- `STATE_MANAGEMENT_PATTERNS.md` - Redux patterns
- `MCP_CONNECTIONS_FEATURE.md` - MCP connections spec
- `feature-flags-mapping.md` - Feature flag documentation
- `bundle-baseline.md` - Bundle size tracking

## Metrics

Lighthouse audit results are stored in `.metrics/`:

- `lighthouse-appshell.json`
- `lighthouse-studio-shell.json`
