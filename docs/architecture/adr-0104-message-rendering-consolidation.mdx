# ADR-0104: Message Rendering Consolidation

| Status   | Proposed                                     |
|----------|----------------------------------------------|
| Date     | 2026-01-21                                   |
| Category | Frontend Architecture                        |
| Authors  | Claude Code                                  |

## Context

The Studio frontend currently has two competing message rendering architectures:

### Architecture 1: Modern "Phase 2" MessageList

**Location**: `src/conversation/MessageList.tsx`

A simpler, emerging architecture focused on virtualization and performance.

**Features**:
- Message display
- Rich markdown (conditional)
- Source citations
- Partial streaming support

**Missing**:
- Thinking traces
- Message rating
- Agent traces
- Message actions (edit/delete)
- Plan rendering

### Architecture 2: Classic ChatMessages

**Location**: `src/components/Chat/ChatMessages.tsx`

The feature-complete production architecture.

**Features**:
- Full message display
- Complete rich markdown
- Source citations
- Thinking traces
- Message rating (thumbs up/down)
- Agent traces
- Message actions
- Full streaming support

**Missing**:
- Plan rendering (both architectures)

### Feature Parity Gap

| Feature | MessageList | ChatMessages |
|---------|-------------|--------------|
| Message display | Yes | Yes |
| Rich markdown | Partial | Yes |
| Source citations | Yes | Yes |
| Thinking traces | No | Yes |
| Message rating | No | Yes |
| Agent traces | No | Yes |
| Message actions | No | Yes |
| Streaming support | Partial | Yes |
| Plan rendering | No | No |

### Problem Statement

1. **Feature drift**: New features added to one architecture aren't replicated in the other
2. **Maintenance burden**: Bug fixes must be applied to two codebases
3. **Inconsistent UX**: Different rendering behaviors depending on usage context
4. **Plan rendering gap**: Neither architecture supports inline plan approval (Issue 7)

## Decision

Create a new unified `UnifiedMessageList` component that:

1. **Preserves all existing capabilities** from ChatMessages
2. **Adds plan rendering** for HITL approval flows
3. **Uses virtualization** for performance at scale
4. **Gates migration** with feature flag `unified_message_list`

### Required Capabilities (Must Preserve)

#### A. HITL Actions (4 Types)

| Type | UI Component | Actions |
|------|--------------|---------|
| Agent Approval | InlineApprovalCard | Approve, Reject, Modify |
| Clarification | InlineClarificationCard | Text input, Choice selection, Confirmation |
| Plan Approval | InlinePlanCard | Approve, Reject, Edit config |
| Remediation | RemediationCard | Approve with notes, Reject with reason |

#### B. Artifact Types (16 Types)

| Artifact | Renderer | Key Features |
|----------|----------|--------------|
| code | CodeArtifact | Syntax highlighting (50+ langs), copy, download, line numbers |
| chart | ChartArtifact | Bar/Line/Pie, type switching, export PNG/PDF/SVG |
| table | TableArtifact | Sort, filter, export CSV/Excel/JSON |
| json | JSONArtifact | Tree view, collapse/expand, copy |
| mermaid | MermaidArtifact | Diagram rendering, mermaid.live link |
| html | HTMLArtifact | Sandboxed iframe, Bokeh support |
| image | ArtifactRenderer | URLs, base64, lazy loading |
| svg | InteractiveSVGArtifact | Zoom, pan, sanitize, download |
| executable | SandpackExecutor | JSX/TSX execution in iframe sandbox |
| vega-lite | VegaLiteArtifact | Vega-Lite specs, theme support |
| latex | LaTeXArtifact | KaTeX math, zoom controls |
| audio | AudioArtifact | HTML5 player |
| video | VideoArtifact | HTML5 player with poster |
| widget | ArtifactRenderer | Custom generative widgets |
| mdx | MDXArtifact | Mintlify-compatible MDX |
| text | ArtifactRenderer | Plain text fallback |

#### C. Meta Components

- LLMThinkingTrace (thinking display with collapse)
- SelectedToolsDisplay (ADR-0099 tool visualization)
- TokenUsageDisplay (cost tracking)
- SourceCitations (citation links with deduplication)
- AIFollowUpSuggestions (suggestion chips)
- ResponseRating (thumbs up/down feedback)
- AgentExecutionTracePanel (lazy-loaded agent traces)

#### D. Interactive Features

- Zoom/pan for SVG, LaTeX, charts
- Copy to clipboard with feedback
- Download in multiple formats
- Fullscreen toggle
- Keyboard shortcuts (+/-/0 for zoom, Escape for close)
- Touch gestures (pinch-zoom, drag-pan)

#### E. Streaming Support

- StreamingArtifactPlaceholder with skeleton loading
- Lazy-loaded components with Suspense
- RAF-based auto-scroll
- Typing indicators

#### F. Security

- SVG sanitization (no scripts/event handlers)
- HTML iframe sandboxing
- Sandpack CSP compliance
- Vega-Lite trust:false default

## Implementation Plan

### Phase 1: Create Foundation (This Sprint)

1. Create `UnifiedMessageList.tsx` skeleton
2. Add feature flag `unified_message_list`
3. Wire up plan rendering integration (Issue 7)

### Phase 2: Feature Parity

1. Port all 16 artifact renderers
2. Port all 4 HITL action components
3. Port meta components (thinking, rating, etc.)

### Phase 3: Virtualization

1. Add react-window or similar for virtualization
2. Implement dynamic row heights
3. Performance testing with 1000+ messages

### Phase 4: Migration

1. A/B testing comparison
2. Gradual rollout via feature flag
3. Deprecation warnings on old components

## Consequences

### Positive

- Single source of truth for message rendering
- Consistent UX across all contexts
- Reduced maintenance burden
- Clear path for new features

### Negative

- Migration effort required
- Temporary code duplication during transition
- Risk of regression during migration

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Regression in existing features | Comprehensive regression test suite |
| Performance degradation | Virtualization + benchmarking |
| User disruption | Feature flag + gradual rollout |

## References

- ADR-0093: ChatInput Consolidation (prior art for consolidation pattern)
- Issue 7: Execution Plans Not Rendering Inline
- Issue 8: Duplicate Message Rendering Architectures

## Status

Proposed - Awaiting implementation.
