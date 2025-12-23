# Frontend XSS Prevention Guide

**Created**: 2025-12-22
**Status**: Active
**Purpose**: Document XSS prevention patterns for the Studio Frontend

---

## Overview

This guide documents the XSS (Cross-Site Scripting) prevention patterns implemented in the Studio Frontend. All components that render user-provided or AI-generated content MUST follow these patterns.

## Critical Rule: dangerouslySetInnerHTML

**Never use `dangerouslySetInnerHTML` without sanitization.**

Any component using `dangerouslySetInnerHTML` MUST:
1. Use DOMPurify to sanitize the HTML
2. Configure allowed tags/attributes explicitly
3. Have corresponding XSS security tests

### Current Usages (All Sanitized)

| File | Purpose | Sanitization |
|------|---------|--------------|
| `CanvasArtifact.tsx:199` | Markdown preview | DOMPurify with allowlist |
| `ChatMessage.tsx:117,148` | Basic markdown rendering | DOMPurify + HTML escaping |
| `InteractiveMermaidDiagram.tsx:428` | Mermaid SVG output | Mermaid strict mode |
| `ArtifactRenderer.tsx:107` | HTML artifact preview | DOMPurify with allowlist |
| `RunOutputViewer.tsx:107` | Run output rendering | DOMPurify with allowlist |

---

## DOMPurify Configuration Patterns

### Pattern 1: Full Markdown Support

Use this configuration for rich markdown content (headings, lists, tables, etc.):

```typescript
import DOMPurify from "dompurify";

const sanitizedHtml = DOMPurify.sanitize(content, {
  // Allow common markdown-rendered elements
  ALLOWED_TAGS: [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "b", "em", "i", "u", "s", "del", "ins",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a", "img",
    "table", "thead", "tbody", "tr", "th", "td",
    "div", "span",
  ],
  // Allow safe attributes only
  ALLOWED_ATTR: [
    "href", "src", "alt", "title", "class", "id",
    "width", "height", "target", "rel",
  ],
  // Block data: URLs which can contain scripts
  ALLOW_DATA_ATTR: false,
  // Explicitly forbid dangerous elements
  FORBID_TAGS: [
    "script", "style", "iframe", "form",
    "input", "textarea", "button",
  ],
  // Forbid event handlers
  FORBID_ATTR: [
    "onerror", "onclick", "onload", "onmouseover",
    "onfocus", "onblur", "onsubmit", "onchange",
  ],
});
```

**Example usage**: `CanvasArtifact.tsx` for markdown preview.

### Pattern 2: Minimal Markdown (Bold/Italic Only)

Use this for simple text with basic formatting:

```typescript
import DOMPurify from "dompurify";

function safeRenderMarkdown(content: string): string {
  // First escape any existing HTML to prevent XSS
  const escaped = content
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

  // Apply markdown transformations on escaped content
  const rendered = escaped
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>");

  // Final sanitization pass with strict allowlist
  return DOMPurify.sanitize(rendered, {
    ALLOWED_TAGS: ["strong", "b", "em", "i"],
    ALLOWED_ATTR: [],
  });
}
```

**Example usage**: `ChatMessage.tsx` for inline markdown in messages.

### Pattern 3: SVG/Diagram Content

For Mermaid diagrams and other SVG content, use library security settings:

```typescript
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  // CRITICAL: Use "strict" mode to prevent XSS via HTML labels
  // "loose" mode allows HTML labels which can contain malicious scripts
  securityLevel: "strict",
  suppressErrorRendering: true,
});
```

**Why "strict"?** Mermaid's "loose" mode allows HTML labels in diagrams, which can be exploited:
```mermaid
graph TD
  A[<script>alert('XSS')</script>] --> B
```

In "loose" mode, this would execute the script. In "strict" mode, it's escaped.

---

## Testing Patterns

### XSS Security Tests (Required)

Every component using `dangerouslySetInnerHTML` MUST have these tests:

```typescript
describe("XSS Security (Markdown Sanitization)", () => {
  it("should sanitize script tags", () => {
    const { container } = render(
      <Component content='<script>alert("XSS")</script><p>Safe</p>' />
    );
    expect(container.innerHTML).not.toContain("<script>");
    expect(container.innerHTML).not.toContain("alert");
    expect(container.textContent).toContain("Safe");
  });

  it("should sanitize onclick event handlers", () => {
    const { container } = render(
      <Component content='<div onclick="alert(\'XSS\')">Click</div>' />
    );
    expect(container.innerHTML).not.toContain("onclick");
    expect(container.textContent).toContain("Click");
  });

  it("should sanitize onerror event handlers", () => {
    const { container } = render(
      <Component content='<img src="x" onerror="alert(\'XSS\')">' />
    );
    expect(container.innerHTML).not.toContain("onerror");
  });

  it("should sanitize javascript: URLs", () => {
    const { container } = render(
      <Component content='<a href="javascript:alert(\'XSS\')">Click</a>' />
    );
    expect(container.innerHTML).not.toContain("javascript:");
  });

  it("should sanitize data: URLs with scripts", () => {
    const { container } = render(
      <Component content='<a href="data:text/html,<script>alert(1)</script>">Click</a>' />
    );
    expect(container.innerHTML).not.toContain("data:text/html");
  });

  it("should allow safe HTML elements", () => {
    const { container } = render(
      <Component content="<h1>Title</h1><p><strong>Bold</strong> and <em>italic</em></p>" />
    );
    expect(container.innerHTML).toContain("<h1>");
    expect(container.innerHTML).toContain("<strong>");
    expect(container.innerHTML).toContain("<em>");
  });
});
```

### Mermaid Security Tests

```typescript
describe("Security Configuration", () => {
  it("should initialize mermaid with strict security level", async () => {
    // Import mermaid to check configuration
    const mermaid = await import("mermaid");

    // Render a diagram to trigger initialization
    render(<InteractiveMermaidDiagram code="graph TD; A-->B" />);

    // Verify strict mode is used
    // Note: This is enforced in the component's initialization
    expect(mermaid.default.mermaidAPI.getConfig?.().securityLevel).toBe("strict");
  });
});
```

---

## Code Review Checklist

When reviewing code that uses `dangerouslySetInnerHTML`:

- [ ] **DOMPurify imported and used?**
  - Must sanitize content before rendering
  - Never pass raw user/AI content directly

- [ ] **Explicit allowlists configured?**
  - `ALLOWED_TAGS` must be defined
  - `ALLOWED_ATTR` must be defined
  - Prefer allowlists over blocklists

- [ ] **Event handlers blocked?**
  - `FORBID_ATTR` includes: onclick, onerror, onload, etc.
  - Or use HTML escaping before markdown processing

- [ ] **Dangerous protocols blocked?**
  - `javascript:` URLs removed
  - `data:` URLs restricted or removed
  - `ALLOW_DATA_ATTR: false` recommended

- [ ] **Security tests added?**
  - Script tag test
  - Event handler test (onclick, onerror)
  - Protocol test (javascript:, data:)
  - Safe content preservation test

- [ ] **Third-party libraries configured securely?**
  - Mermaid: `securityLevel: "strict"`
  - Other diagram libraries: check security docs

---

## Common Vulnerabilities to Avoid

### 1. Raw Content Rendering

```typescript
// BAD: Never do this
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// GOOD: Always sanitize
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userContent) }} />
```

### 2. Regex-Only Markdown Without Escaping

```typescript
// BAD: Regex on raw content allows XSS
const rendered = content
  .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

// GOOD: Escape HTML first, then apply regex
const escaped = escapeHtml(content);
const rendered = escaped
  .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
```

### 3. Loose Security Settings

```typescript
// BAD: Loose mode allows XSS via HTML labels
mermaid.initialize({ securityLevel: "loose" });

// GOOD: Strict mode escapes all HTML
mermaid.initialize({ securityLevel: "strict" });
```

### 4. Missing Protocol Filtering

```typescript
// BAD: Only checking tags
DOMPurify.sanitize(content, { ALLOWED_TAGS: ["a"] });
// Still allows: <a href="javascript:alert(1)">

// GOOD: DOMPurify removes javascript: by default
// But explicitly forbid data: URLs
DOMPurify.sanitize(content, {
  ALLOWED_TAGS: ["a"],
  ALLOWED_ATTR: ["href"],
  ALLOW_DATA_ATTR: false,
});
```

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `dompurify` | ^3.2.4 | HTML sanitization |
| `@types/dompurify` | ^3.2.0 | TypeScript definitions |

Install with:
```bash
npm install dompurify @types/dompurify
```

---

## Content Security Policy (CSP)

### Current Implementation

CSP is implemented via a meta tag in `index.html`:

```html
<meta http-equiv="Content-Security-Policy" content="
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob: https:;
  font-src 'self' data:;
  connect-src 'self' ws: wss: http://localhost:* ws://localhost:*;
  frame-src 'self' blob:;
  worker-src 'self' blob:;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'self';
  upgrade-insecure-requests;
" />
```

### Directive Explanations

| Directive | Value | Purpose |
|-----------|-------|---------|
| `default-src` | `'self'` | Default fallback: only same-origin resources |
| `script-src` | `'self' 'unsafe-inline' 'unsafe-eval' blob:` | Scripts: self + inline (React), eval (Monaco), blob (workers) |
| `style-src` | `'self' 'unsafe-inline'` | Styles: self + inline (Tailwind, styled-components) |
| `img-src` | `'self' data: blob: https:` | Images: self, data URLs (SVGs), blobs, HTTPS |
| `font-src` | `'self' data:` | Fonts: self + base64 embedded fonts |
| `connect-src` | `'self' ws: wss: localhost:*` | Fetch/XHR/WebSocket: API + localhost dev |
| `frame-src` | `'self' blob:` | Iframes: self + blob (Sandpack code preview) |
| `worker-src` | `'self' blob:` | Web workers: self + blob (Monaco, PWA) |
| `object-src` | `'none'` | Plugins: completely blocked (Flash, Java) |
| `base-uri` | `'self'` | Base tag: same-origin only (prevents base hijacking) |
| `form-action` | `'self'` | Form submissions: same-origin only |
| `frame-ancestors` | `'self'` | Who can embed us: same-origin only (clickjacking protection) |

### Why 'unsafe-inline' and 'unsafe-eval'?

These are required for the current technology stack:

**`'unsafe-inline'` for scripts:**
- React's JSX transformation may inject inline handlers
- Some UI libraries use inline event handlers

**`'unsafe-eval'` for scripts:**
- Monaco Editor requires `eval` for WebAssembly and dynamic code execution
- Sandpack code sandbox uses `eval` for preview

**`'unsafe-inline'` for styles:**
- Tailwind CSS uses inline styles via `style` attribute
- React component libraries often use CSS-in-JS

### Production Recommendations

For production, implement CSP via HTTP headers (not meta tags) for additional security:

#### Nginx Configuration

```nginx
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob: https:;
  font-src 'self' data:;
  connect-src 'self' wss://*.your-domain.com https://*.your-domain.com;
  frame-src 'self' blob:;
  worker-src 'self' blob:;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'self';
  upgrade-insecure-requests;
  report-uri /api/v1/csp-report;
" always;
```

#### Traefik Middleware (Kubernetes)

```yaml
apiVersion: traefik.containo.us/v1alpha1
kind: Middleware
metadata:
  name: security-headers
spec:
  headers:
    contentSecurityPolicy: |
      default-src 'self';
      script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:;
      style-src 'self' 'unsafe-inline';
      img-src 'self' data: blob: https:;
      font-src 'self' data:;
      connect-src 'self' wss: https:;
      frame-src 'self' blob:;
      worker-src 'self' blob:;
      object-src 'none';
      base-uri 'self';
      form-action 'self';
      frame-ancestors 'self';
      upgrade-insecure-requests;
```

### Future Improvements

To eliminate `'unsafe-inline'` and `'unsafe-eval'`:

1. **Nonce-based CSP**: Generate per-request nonces for inline scripts
   ```html
   <script nonce="random123">...</script>
   ```
   CSP: `script-src 'self' 'nonce-random123'`

2. **Hash-based CSP**: Use SHA hashes for known inline scripts
   ```
   script-src 'self' 'sha256-abc123...'
   ```

3. **Externalize inline styles**: Move to CSS files or use `style-src-attr 'unsafe-inline'` (more specific)

4. **Monaco Editor alternative**: Consider CodeMirror which doesn't require `eval`

---

## References

- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [DOMPurify Documentation](https://github.com/cure53/DOMPurify)
- [Mermaid Security Documentation](https://mermaid.js.org/config/setup/modules/mermaidAPI.html#securitylevel)
- Project Security Policy: `/SECURITY.md`
