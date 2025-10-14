# Mintlify Documentation Deployment Guide

This guide walks you through deploying your Mintlify documentation and integrating it with your deployed MCP Server application.

## 🚀 Quick Deployment

### Step 1: Deploy to Mintlify

1. **Sign up at Mintlify**
   - Go to https://mintlify.com
   - Sign in with GitHub

2. **Create New Documentation**
   - Click "New Documentation"
   - Select repository: `vishnu2kmohan/mcp-server-langgraph`
   - Set root directory: `./` (leave as default)
   - Mintlify auto-detects `mint.json`

3. **Configure Settings**
   - **Documentation URL**: `mcp-server-langgraph` (or custom subdomain)
   - **Branch**: `main` (auto-deploy on push)
   - **Build directory**: Leave default

4. **Deploy**
   - Click "Deploy"
   - Your docs will be live at: `https://mcp-server-langgraph.mintlify.app`

### Step 2: Custom Domain (Optional)

If you want docs at `docs.yourdomain.com`:

1. **Add DNS Record**
   ```
   Type: CNAME
   Name: docs
   Value: cname.mintlify.com
   ```

2. **Configure in Mintlify**
   - Go to Settings → Custom Domain
   - Enter: `docs.yourdomain.com`
   - SSL certificate auto-provisioned

3. **Update Application**
   Update `mcp_server_http.py` line 572:
   ```python
   "full_documentation": "https://docs.yourdomain.com"
   ```

## 🔗 Integration with Deployed Application

### Application Endpoints

Your deployed MCP Server now includes these documentation endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Root endpoint with all links |
| `GET /documentation` | Redirects to Mintlify docs |
| `GET /docs` | FastAPI Swagger UI |
| `GET /redoc` | ReDoc API documentation |

### Example Response from `/`

```json
{
  "service": "MCP Server with LangGraph",
  "version": "1.0.0",
  "description": "AI Agent with fine-grained authorization and observability",
  "endpoints": {
    "api_docs": "/docs",
    "redoc": "/redoc",
    "documentation": "/documentation",
    "health": "/health",
    "tools": "/tools",
    "resources": "/resources",
    "sse": "/sse",
    "messages": "/messages"
  },
  "external_links": {
    "full_documentation": "https://mcp-server-langgraph.mintlify.app",
    "github": "https://github.com/vishnu2kmohan/mcp-server-langgraph",
    "issues": "https://github.com/vishnu2kmohan/mcp-server-langgraph/issues"
  }
}
```

## 📱 Access Documentation

### From Deployed Application

Users can access documentation in several ways:

1. **Direct Redirect**
   ```bash
   curl https://your-app.com/documentation
   # Redirects to: https://mcp-server-langgraph.mintlify.app
   ```

2. **Root Endpoint**
   ```bash
   curl https://your-app.com/
   # Returns JSON with all documentation links
   ```

3. **Direct Access**
   ```bash
   # Mintlify hosted
   https://mcp-server-langgraph.mintlify.app

   # Custom domain (if configured)
   https://docs.yourdomain.com
   ```

## 🔧 Environment Variables

Add these to your deployment configuration:

### LangGraph Cloud

Update `langgraph.json`:
```json
{
  "env": {
    "DOCS_URL": "https://mcp-server-langgraph.mintlify.app",
    "GITHUB_REPO": "https://github.com/vishnu2kmohan/mcp-server-langgraph"
  }
}
```

### Docker Compose

Update `docker-compose.yml`:
```yaml
environment:
  - DOCS_URL=https://mcp-server-langgraph.mintlify.app
  - GITHUB_REPO=https://github.com/vishnu2kmohan/mcp-server-langgraph
```

### Kubernetes

Update your ConfigMap:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-server-config
data:
  DOCS_URL: "https://mcp-server-langgraph.mintlify.app"
  GITHUB_REPO: "https://github.com/vishnu2kmohan/mcp-server-langgraph"
```

## 📊 Embedding Documentation (Advanced)

### Option 1: Iframe Embed

Create a web UI that embeds Mintlify:

```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server Documentation</title>
</head>
<body>
    <iframe
        src="https://mcp-server-langgraph.mintlify.app"
        width="100%"
        height="100%"
        frameborder="0"
        style="height: 100vh;">
    </iframe>
</body>
</html>
```

### Option 2: OpenAPI Integration

Link Mintlify docs in your OpenAPI/Swagger UI:

Update `mcp_server_http.py`:
```python
app = FastAPI(
    title="MCP Server with LangGraph",
    description=(
        "AI Agent with fine-grained authorization and observability\n\n"
        "**Full Documentation:** https://mcp-server-langgraph.mintlify.app"
    ),
    version=settings.service_version,
    docs_url="/docs",
    redoc_url="/redoc"
)
```

### Option 3: Custom Landing Page

Create `static/index.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>MCP Server - Home</title>
</head>
<body>
    <h1>MCP Server with LangGraph</h1>
    <nav>
        <a href="/docs">API Documentation (Swagger)</a> |
        <a href="/redoc">API Documentation (ReDoc)</a> |
        <a href="https://mcp-server-langgraph.mintlify.app">Full Documentation</a>
    </nav>
</body>
</html>
```

Mount static files in `mcp_server_http.py`:
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

## 🔄 Auto-Deploy Workflow

### GitHub Actions

Your docs auto-deploy when you push to `main`:

1. **Push documentation changes**
   ```bash
   git add docs/
   git commit -m "docs: update guides"
   git push origin main
   ```

2. **Mintlify auto-deploys**
   - Triggered on push to `main`
   - Build completes in ~2 minutes
   - Live at your Mintlify URL

3. **Preview PRs**
   - PRs get preview deployments
   - Preview URL in PR comments
   - Test before merging

### Webhook Notifications (Optional)

Configure webhooks in Mintlify dashboard to notify on:
- Successful deployments
- Build failures
- Deploy previews

## 📈 Analytics & Monitoring

### Enable Analytics

Update `mint.json`:
```json
{
  "analytics": {
    "ga4": {
      "measurementId": "G-XXXXXXXXXX"
    },
    "gtm": {
      "tagId": "GTM-XXXXXXX"
    }
  }
}
```

### Track Documentation Usage

Add to your monitoring:
```python
from mcp_server_langgraph.observability.telemetry import metrics

@app.get("/documentation")
async def documentation_redirect():
    # Track documentation access
    metrics.documentation_views.add(1, {"source": "app_redirect"})
    # ... redirect logic
```

## ✅ Deployment Checklist

- [ ] Deploy to Mintlify
- [ ] Configure custom domain (optional)
- [ ] Update application endpoints
- [ ] Test `/documentation` redirect
- [ ] Verify `/` root endpoint returns links
- [ ] Update environment variables
- [ ] Enable analytics
- [ ] Test auto-deploy workflow
- [ ] Add documentation links to README
- [ ] Update GitHub repository description

## 🎯 Post-Deployment

1. **Add to README.md**
   ```markdown
   ## Documentation

   - [Full Documentation](https://mcp-server-langgraph.mintlify.app)
   - [API Reference](https://your-app.com/docs)
   - [Health Checks](https://your-app.com/health)
   ```

2. **Update GitHub Repository**
   - Set website URL to Mintlify docs
   - Add documentation topic
   - Update description with docs link

3. **Share Documentation**
   - Tweet the launch
   - Post to relevant communities
   - Add to awesome lists

## 🆘 Troubleshooting

### Documentation not deploying

1. Check `mint.json` syntax
2. Verify all referenced pages exist
3. Check Mintlify dashboard for build errors
4. Review deployment logs

### Redirect not working

1. Verify `docs/index.html` exists
2. Check FastAPI route registration
3. Test with curl: `curl -L https://your-app.com/documentation`

### Custom domain issues

1. Verify DNS CNAME record
2. Wait for DNS propagation (up to 48 hours)
3. Check SSL certificate status in Mintlify dashboard

## 📚 Resources

- [Mintlify Docs](https://mintlify.com/docs)
- [Custom Domains](https://mintlify.com/docs/settings/custom-domain)
- [Analytics Setup](https://mintlify.com/docs/settings/analytics)
- [API Reference](https://mintlify.com/docs/api-playground/overview)
