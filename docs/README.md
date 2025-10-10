# MCP Server with LangGraph Documentation

This directory contains the Mintlify-powered documentation for MCP Server with LangGraph.

## 🚀 Quick Start

### Local Development

1. **Install Mintlify CLI**:
   ```bash
   npm install -g mintlify
   ```

2. **Start the development server**:
   ```bash
   cd docs
   mintlify dev
   ```

3. **Open your browser**:
   ```
   http://localhost:3000
   ```

Changes to `.mdx` files will hot-reload automatically!

## 📁 Structure

```
docs/
├── getting-started/       # Getting started guides
│   ├── introduction.mdx
│   ├── quickstart.mdx
│   └── installation.mdx
├── guides/               # How-to guides
│   ├── multi-llm-setup.mdx
│   ├── openfga-setup.mdx
│   └── infisical-setup.mdx
├── api-reference/        # API documentation
│   ├── introduction.mdx
│   └── mcp-endpoints.mdx
├── deployment/           # Deployment guides
│   ├── overview.mdx
│   ├── docker.mdx
│   └── kubernetes.mdx
├── security/             # Security documentation
│   ├── overview.mdx
│   └── best-practices.mdx
└── advanced/             # Advanced topics
    ├── contributing.mdx
    └── troubleshooting.mdx
```

## 🎨 Writing Documentation

### MDX Format

Mintlify uses MDX (Markdown + JSX). You can use:

- **Standard Markdown**: Headings, lists, links, code blocks
- **React Components**: Special Mintlify components

### Special Components

```mdx
<Card title="Example" icon="rocket" href="/path">
  Card content
</Card>

<CardGroup cols={2}>
  <Card ...>...</Card>
  <Card ...>...</Card>
</CardGroup>

<Tabs>
  <Tab title="Tab 1">Content</Tab>
  <Tab title="Tab 2">Content</Tab>
</Tabs>

<Accordion title="Click to expand">
  Hidden content
</Accordion>

<Note>Important information</Note>
<Tip>Helpful tip</Tip>
<Warning>Warning message</Warning>
<Check>Success message</Check>

<Steps>
  <Step title="Step 1">...</Step>
  <Step title="Step 2">...</Step>
</Steps>
```

### Code Blocks

````mdx
```python
def hello():
    print("Hello, world!")
```

```bash
npm install package
```

<CodeGroup>
```python Python
print("Hello")
```

```javascript JavaScript
console.log("Hello")
```
</CodeGroup>
````

## 🔧 Configuration

The documentation is configured in `mint.json`:

```json
{
  "name": "MCP Server with LangGraph",
  "logo": { ... },
  "colors": { ... },
  "navigation": [ ... ],
  "tabs": [ ... ]
}
```

### Key Configuration

- **Navigation**: Edit `navigation` array in `mint.json`
- **Tabs**: Add new tabs in `tabs` array
- **Colors**: Customize brand colors
- **Logos**: Add SVG logos to `/logo` directory
- **Favicon**: Add `/favicon.svg`

## 📝 Adding New Pages

1. **Create MDX file**:
   ```bash
   touch docs/guides/new-guide.mdx
   ```

2. **Add frontmatter**:
   ```mdx
   ---
   title: New Guide
   description: 'Description of the guide'
   ---
   ```

3. **Add to navigation** in `mint.json`:
   ```json
   {
     "group": "Guides",
     "pages": [
       "guides/existing-guide",
       "guides/new-guide"
     ]
   }
   ```

## 🚀 Deployment

### Option 1: Mintlify Hosting (Recommended)

1. **Sign up** at [mintlify.com](https://mintlify.com)

2. **Connect GitHub repository**:
   - Go to Mintlify dashboard
   - Click "New Documentation"
   - Connect GitHub repository
   - Select `docs/` directory

3. **Auto-deployment**:
   - Pushes to `main` branch auto-deploy
   - Preview deployments for PRs

4. **Custom domain** (optional):
   - Add CNAME record: `docs.yourdomain.com`
   - Configure in Mintlify dashboard

### Option 2: Self-Hosted

Build static site:

```bash
mintlify build
```

Deploy to:
- **Vercel**: `vercel deploy`
- **Netlify**: `netlify deploy`
- **GitHub Pages**: Deploy `_site/` directory
- **S3 + CloudFront**: Upload `_site/` to S3

## 🎯 Best Practices

### Writing Style

- ✅ Use active voice
- ✅ Keep sentences short and clear
- ✅ Include code examples
- ✅ Add visual aids (diagrams, screenshots)
- ✅ Use callout components (Note, Tip, Warning)
- ❌ Don't assume prior knowledge
- ❌ Don't use jargon without explanation

### Organization

- **Getting Started**: Tutorials and quick starts
- **Guides**: Task-oriented how-to guides
- **API Reference**: Technical reference documentation
- **Deployment**: Infrastructure and deployment guides
- **Advanced**: Complex topics and deep dives

### Code Examples

Always provide:
1. **Multiple languages** (Python, cURL, JavaScript)
2. **Complete, runnable examples**
3. **Expected output**
4. **Error handling**

## 🔍 Search

Mintlify provides built-in search powered by Algolia. It automatically indexes:
- Page titles
- Headings
- Content
- Code blocks

No configuration needed!

## 📊 Analytics

Enable analytics in `mint.json`:

```json
{
  "analytics": {
    "ga4": {
      "measurementId": "G-XXXXXXXXXX"
    },
    "posthog": {
      "apiKey": "phc_xxxx"
    }
  }
}
```

## 🐛 Troubleshooting

### Build fails

```bash
# Clear cache
rm -rf .mintlify

# Reinstall
npm install -g mintlify@latest
```

### Hot reload not working

```bash
# Restart dev server
mintlify dev --force
```

### Navigation not updating

1. Check `mint.json` syntax (must be valid JSON)
2. Ensure file paths match exactly
3. Restart dev server

## 📚 Resources

- **Mintlify Docs**: https://mintlify.com/docs
- **MDX Guide**: https://mdxjs.com/
- **Component Library**: https://mintlify.com/docs/components
- **Examples**: https://github.com/mintlify/starter

## 🤝 Contributing

To contribute to documentation:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `mintlify dev`
5. Submit a pull request

See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for details.

## 📧 Support

- **Mintlify Support**: support@mintlify.com
- **GitHub Issues**: https://github.com/vishnu2kmohan/mcp_server_langgraph/issues
- **Discussions**: https://github.com/vishnu2kmohan/mcp_server_langgraph/discussions

---

**Happy documenting!** 📖✨
