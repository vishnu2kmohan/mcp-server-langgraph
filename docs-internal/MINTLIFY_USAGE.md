# Mintlify Documentation

This project uses [Mintlify](https://mintlify.com) for documentation.

## File Structure

```
/
├── mint.json              # Mintlify configuration (root)
├── .mintlifyignore        # Files to exclude from Mintlify (root)
└── docs/
    ├── getting-started/   # Getting started guides (MDX)
    ├── api-reference/     # API documentation (MDX)
    ├── guides/            # How-to guides (MDX)
    ├── deployment/        # Deployment guides (MDX)
    ├── architecture/      # ADR documentation (MDX)
    ├── advanced/          # Advanced topics (MDX)
    ├── development/       # Development guides (MDX)
    └── security/          # Security documentation (MDX)
```

## Local Development

Run the Mintlify dev server from the **project root**:

```bash
# From project root
mintlify dev
```

The server will:
- ✅ Scan only the `docs/` directory
- ✅ Ignore `.venv/`, `src/`, `tests/`, etc.
- ✅ Hot-reload on file changes
- 🌐 Open at http://localhost:3000

## What's Included

Mintlify documentation files (`.mdx`) in these directories:
- `docs/getting-started/`
- `docs/api-reference/`
- `docs/guides/`
- `docs/deployment/`
- `docs/architecture/`
- `docs/advanced/`
- `docs/development/`
- `docs/security/`

## What's Excluded (via .mintlifyignore)

- **Python environment:** `.venv/`, `venv/`, `env/`
- **Source code:** `src/`, `tests/`
- **Build artifacts:** `dist/`, `build/`, `*.pyc`
- **Internal docs:** `docs/archive/`, `docs/reports/`, `docs/adr/`
- **Configuration:** `config/`, `deployments/`, `docker/`
- **Root markdown files:** `/*.md` (README, CHANGELOG, etc.)

## Deployment

Deploy to Mintlify cloud:

```bash
mintlify deploy
```

Or use GitHub Actions (see `.github/workflows/mintlify.yml`)

## Configuration

All configuration is in `mint.json` at the project root:
- Navigation structure
- Theming and branding
- API reference endpoints
- External links

## Adding New Pages

1. Create a new `.mdx` file in the appropriate `docs/` subdirectory
2. Add the page reference to `mint.json` navigation
3. Restart `mintlify dev` to see changes

Example:
```json
// mint.json
{
  "navigation": [
    {
      "group": "Getting Started",
      "pages": [
        "getting-started/introduction",
        "getting-started/new-page"  // ← Add here
      ]
    }
  ]
}
```

## Troubleshooting

### Mintlify is scanning .venv/
- Ensure `.mintlifyignore` is at project root
- Restart the `mintlify dev` server
- Check that `.venv/` is listed in `.mintlifyignore`

### Page not showing up
- Check that the file path in `mint.json` matches the actual `.mdx` file
- File paths are relative to project root
- Example: `"getting-started/introduction"` → `docs/getting-started/introduction.mdx`

### Changes not appearing
- Mintlify has hot-reload, but sometimes needs a restart
- Press `Ctrl+C` and run `mintlify dev` again

## Learn More

- [Mintlify Documentation](https://mintlify.com/docs)
- [Mintlify CLI Reference](https://mintlify.com/docs/development)
- [MDX Syntax](https://mdxjs.com/)
