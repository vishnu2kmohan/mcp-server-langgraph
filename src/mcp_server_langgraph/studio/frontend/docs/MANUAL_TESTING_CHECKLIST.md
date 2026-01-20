# Connections Page Redesign - Manual Testing Checklist

This checklist validates the Connections Page Redesign & Chat UX Enhancement features
before merging to main. Complete all items for full validation.

## Prerequisites

- [ ] Development server running (`npm run dev`)
- [ ] Backend API running (`uv run uvicorn ...`)
- [ ] At least one test user account available
- [ ] OAuth2 provider configured (GitHub, Slack, etc.) for OAuth tests

---

## Phase 1: Connections Page Directory

### Tab Navigation
- [ ] Navigate to Connections page
- [ ] Verify two tabs visible: "Discover" and "My Connectors"
- [ ] Click "Discover" tab → verify grid of connector templates loads
- [ ] Click "My Connectors" tab → verify existing connections shown
- [ ] Tab switching animation is smooth (no janky transitions)

### Discover Tab Features
- [ ] Connector cards display: icon, name, description, auth type badge, category badge
- [ ] Cards sorted by popularity by default (GitHub, Slack, Notion at top)
- [ ] Category filter chips visible (Development, Communication, Productivity, etc.)
- [ ] Click category chip → only matching connectors shown
- [ ] Click "All" → all connectors shown again
- [ ] Search box filters templates by name/description
- [ ] Click "Connect" on template → ConnectionDialog opens with template pre-filled

### My Connectors Tab Features
- [ ] Connection cards show: name, URL, status badge, auth type, scope badge
- [ ] Status badges show correct colors (connected=green, error=red, etc.)
- [ ] Scope badges show correctly (Personal, Shared, Session icons)
- [ ] Multi-select checkboxes work
- [ ] Bulk actions toolbar appears when items selected
- [ ] Bulk delete works (with confirmation)
- [ ] Individual actions work: Edit, Test, Delete, Audit Log

### Health Dashboard
- [ ] Collapsible health dashboard section visible
- [ ] Click to expand → shows connection health metrics
- [ ] Metrics update when connections change

---

## Phase 2: Chat Intent Suggestions

### Proactive Suggestions
- [ ] Open chat interface
- [ ] Type "check my GitHub PRs" (without GitHub connected)
- [ ] Suggestion bar appears: "This might need GitHub access"
- [ ] Click "Connect GitHub" → inline connection card opens
- [ ] Click "Dismiss" → suggestion bar hides
- [ ] Type "send a slack message" → Slack suggestion appears

### Already Configured
- [ ] Connect GitHub successfully
- [ ] Type "check my GitHub PRs" again
- [ ] No suggestion bar appears (already configured)

---

## Phase 3: Inline Connection Card

### Card Appearance
- [ ] Trigger auth_required (attempt action needing unconfigured connection)
- [ ] Inline connection card appears in chat message area
- [ ] Card shows: title, description, auth method options

### OAuth2 Flow
- [ ] Select "Connect with OAuth2" option
- [ ] Click "Sign in with [Provider]"
- [ ] OAuth popup window opens
- [ ] Complete OAuth in popup
- [ ] Popup closes automatically
- [ ] Card updates to show "Connected" status
- [ ] Success animation plays

### API Key Flow
- [ ] Select "Use API Key" option
- [ ] API key input field appears
- [ ] Enter valid API key
- [ ] Click "Connect"
- [ ] Connection test runs
- [ ] Success state shown

### Error States
- [ ] Enter invalid API key → error message shown
- [ ] Cancel OAuth flow → appropriate error shown
- [ ] Click "Retry" → flow restarts
- [ ] Click "Skip" → card dismisses

---

## Phase 4: OAuth Popup Flow

### Popup Behavior
- [ ] OAuth popup opens in new window (not tab)
- [ ] Popup has reasonable dimensions (600x700 approx)
- [ ] Popup is centered on screen

### Popup Blocker Handling
- [ ] Enable popup blocker in browser
- [ ] Attempt OAuth flow
- [ ] Fallback to full-page redirect works
- [ ] After redirect, returns to correct page

### Cross-Window Communication
- [ ] Complete OAuth in popup
- [ ] Parent window receives success callback
- [ ] Connection status updates in parent window
- [ ] Popup closes automatically

### Error Handling
- [ ] Close popup without completing OAuth
- [ ] Timeout error shown in parent window
- [ ] Cancel button in OAuth provider
- [ ] Error state properly shown

---

## Phase 6: Scope Model

### Scope Selector (ConnectionDialog)
- [ ] Open "Add Connection" dialog
- [ ] Scope selector shows three options: Personal, Shared, Session
- [ ] Personal option shows user icon
- [ ] Shared option shows users icon (only when in project context)
- [ ] Session option shows clock icon (only when not in project)
- [ ] Default selection appropriate for context

### Scope Badges
- [ ] User-scoped connections show "Personal" badge
- [ ] Project-scoped connections show "Shared" badge with users icon
- [ ] Session-scoped connections show "Session" badge with clock icon

### Scope-Based Access
- [ ] Create user-scoped connection → only visible to owner
- [ ] Create project-scoped connection → visible to project members
- [ ] Non-owner cannot use user-scoped connection

---

## Phase 7: Header Model Selector (ADR-0102)

### Pill Display
- [ ] Navigate to chat session with header visible
- [ ] HeaderModelSelector pill visible in session header
- [ ] Pill shows model name and thinking level: "Claude Opus 4.5 (Medium)"
- [ ] For non-thinking models (GPT-4o), only model name shown (no level)

### Model Selection
- [ ] Click pill → dropdown opens
- [ ] All available models listed with provider info
- [ ] Current model shows checkmark
- [ ] Click different model → selection changes
- [ ] Dropdown closes after selection
- [ ] Pill updates to show new model

### Thinking Level Selection
- [ ] Open dropdown for thinking-capable model
- [ ] "Thinking Level" section visible at top
- [ ] Low/Medium/High options displayed
- [ ] Current level highlighted
- [ ] Click different level → selection changes
- [ ] Dropdown stays open for further adjustments
- [ ] Pill updates to reflect new level

### Model Status Badges
- [ ] Preview models show "Preview" badge
- [ ] Legacy models show "Legacy" badge
- [ ] Deprecated models show "Deprecated" badge with sunset date
- [ ] Thinking-capable models show brain icon

### Compact Mode
- [ ] In narrow layouts, abbreviated model name shown
- [ ] "Claude Opus 4.5" becomes "Opus 4.5"

### Keyboard Navigation
- [ ] Tab to focus pill
- [ ] Enter/Space to open dropdown
- [ ] Arrow keys navigate model list
- [ ] Enter selects focused model
- [ ] Escape closes dropdown
- [ ] Focus returns to pill after close

### Deprecation Warning
- [ ] Select deprecated model
- [ ] Warning banner appears in chat area
- [ ] Banner shows model name and sunset date
- [ ] Dismiss button hides banner
- [ ] Switching models resets banner visibility

---

## Accessibility

- [ ] All interactive elements keyboard accessible
- [ ] Tab order is logical
- [ ] Focus indicators visible
- [ ] Screen reader announces card content properly
- [ ] Reduced motion preference respected (animations simplified/disabled)
- [ ] Color contrast meets WCAG 2.1 AA

---

## Performance

- [ ] Page loads in under 2 seconds
- [ ] Tab switching is instant
- [ ] No visible layout shifts
- [ ] Smooth scrolling in connector grid
- [ ] No memory leaks after prolonged use

---

## Sign-Off

| Tester | Date | Status | Notes |
|--------|------|--------|-------|
|        |      |        |       |

**Approval**: [ ] Ready for merge
