# ADR-0093: Chat Input Component Unification

| Status | Accepted |
|--------|----------|
| Date | 2026-01-06 |
| Authors | Claude Opus 4.5 |
| Deciders | Frontend Architecture |
| Consulted | UX Design, Product |
| Informed | All Contributors |

## Context and Problem Statement

The frontend had two separate chat input implementations:

1. **ChatDocument.tsx**: 230+ lines of duplicate RichTextInput code with pill container styling
2. **ChatInputForm.tsx**: Feature-complete chat input component with all integrations

Both implementations needed to maintain:
- `submitOnEnter` preference from `uiSlice` (never hardcoded - user preference)
- Voice input button (outside input, in controls row)
- File upload with drag-drop (outside input, in controls row)
- Slash commands menu
- Inline AI suggestions (ghost text, Tab to accept)
- Model selector dropdown
- Reasoning effort selector (for thinking models)
- URL fetch indicators (#URL integration)

### Problem Statement

How do we consolidate duplicate chat input code while preserving all features and maintaining the new Pill + RichTextInput experience as the default?

## Decision Drivers

1. **Single Source of Truth**: One component handles all chat input UI logic
2. **Feature Parity**: No regression in any chat input feature
3. **User Preference**: `submitOnEnter` must be passed from uiSlice, never hardcoded
4. **Feature Flag**: `FF_ENABLE_RICH_TEXT_CHAT_INPUT` allows rollback if issues arise
5. **Thinking Toggle**: Hide toggle (always enabled) - product approved
6. **Controls Placement**: Voice/file buttons remain outside RichTextInput in controls row

## Decision

Consolidate all chat input UI into `ChatInputForm.tsx` with `enableRichTextMode` prop.

### Implementation

1. **ChatInputForm.tsx** becomes the single source of truth:
   - When `enableRichTextMode=true`: Renders pill container + RichTextInput + controls row
   - When `enableRichTextMode=false`: Renders legacy textarea (fallback)

2. **ChatDocument.tsx** delegates to ChatInputForm:
   - Removed 230+ lines of duplicate RichTextInput/pill container code
   - Now passes `enableRichTextMode`, `submitOnEnter`, `mentionOptions`, `richTextMaxLength` to ChatInputForm
   - All other props unchanged

3. **ConnectedChatInputForm.tsx** uses feature flag:
   - `useFeatureFlag("rich_text_chat_input")` controls `enableRichTextMode`
   - `useAppSelector(selectSubmitOnEnter)` passes user preference

4. **Feature Flag** (`enable_rich_text_chat_input`):
   - Default: `true` (new RichText experience is the default)
   - Environment variable: `FF_ENABLE_RICH_TEXT_CHAT_INPUT=false` for rollback

### Code Structure After Consolidation

```
ChatInputForm.tsx (Single Source of Truth)
├── Props:
│   ├── enableRichTextMode: boolean (default: true)
│   ├── submitOnEnter: boolean (from uiSlice, never hardcoded!)
│   ├── mentionOptions?: MentionOption[]
│   ├── richTextMaxLength?: number
│   ├── modelSupportsThinking: boolean
│   ├── reasoningEffort: ReasoningEffortLevel
│   └── ...existing props (voice, file, slash commands, etc.)
│
├── Renders:
│   ├── SlashCommandMenu (when input starts with "/")
│   ├── Pill Container (when enableRichTextMode=true)
│   │   ├── RichTextInput (with formatting toolbar)
│   │   └── Controls Row (voice, file, model, reasoning, send)
│   └── Legacy Textarea (when enableRichTextMode=false)
│
ChatDocument.tsx (Delegates)
├── Uses ChatInputForm with enableRichTextMode prop
├── ~230 lines removed (duplicate code eliminated)
└── Passes submitOnEnter from uiSlice

ConnectedChatInputForm.tsx (Feature Flag Integration)
├── Uses useFeatureFlag("rich_text_chat_input")
├── Uses useAppSelector(selectSubmitOnEnter)
└── Passes to ChatInputForm
```

## Consequences

### Positive

- **Single Source of Truth**: All chat input UI logic in one component
- **No Duplication**: Removed 230+ lines of duplicate code from ChatDocument
- **Consistent UX**: Same input behavior across all chat contexts
- **Easy Rollback**: Feature flag allows instant revert to legacy textarea
- **Maintainable**: Bug fixes apply to all consumers automatically

### Negative

- **ChatInputForm Complexity**: Component now handles two modes (but clearly separated)
- **Test Updates**: ChatDocument tests needed `ui` slice in mock store

### Neutral

- **Thinking Toggle Hidden**: Product decision - always enabled for thinking models
- **Controls Outside Input**: Voice/file buttons remain in separate controls row

## Alternatives Considered

### Alternative 1: Keep Separate Implementations

- **Rejected**: Duplicate code leads to feature drift and maintenance burden

### Alternative 2: Create New Unified Component

- **Rejected**: ChatInputForm already had most features; enhancing it was simpler

### Alternative 3: Extract Pill Container to Shared Component

- **Rejected**: Pill container + controls row are tightly coupled to input state

## Files Modified

| File | Change |
|------|--------|
| `ChatInputForm.tsx` | Added `enableRichTextMode` prop with pill container/RichTextInput support |
| `ChatDocument.tsx` | Removed 230+ lines of duplicate code, delegates to ChatInputForm |
| `ChatDocument.test.tsx` | Added `ui` reducer to mock store for `submitOnEnter` |
| `ConnectedChatInputForm.tsx` | Uses feature flag + uiSlice for RichText mode |
| `feature_flags.py` | Added `enable_rich_text_chat_input` flag (default: true) |
| `types/api.ts` | Added `rich_text_chat_input` to FeatureFlags interface |

## Related ADRs

- ADR-0088: Frontend Hook Selection Guidance
- ADR-0089: Prompt Architecture Centralization

## References

- Plan: `~/.claude/plans/smooth-squishing-cosmos.md`
- Feature Flag: `FF_ENABLE_RICH_TEXT_CHAT_INPUT`
