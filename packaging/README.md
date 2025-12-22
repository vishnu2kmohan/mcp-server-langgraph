# Desktop Extension Distribution Guide

This guide covers packaging and distributing the MCP Server LangGraph as a Claude Desktop Extension (`.mcpb` format).

## Quick Start

```bash
# Build for current platform
uv run python packaging/build.py

# Build for specific platform
uv run python packaging/build.py --platform macos

# Generate manifest only (no bundling)
uv run python packaging/build.py --manifest-only

# Write platform-specific configs
uv run python packaging/build.py --write-platform-configs
```

## Package Structure

The `.mcpb` package contains:

```
mcp-server-langgraph-1.0.0.mcpb
├── manifest.json        # Extension manifest
├── server/
│   ├── main.py         # Entry point
│   ├── venv/           # Bundled Python virtual environment
│   └── src/            # Application source
├── assets/
│   └── icon.png        # Extension icon
└── platform/
    ├── windows.json    # Windows-specific config
    ├── macos.json      # macOS-specific config
    └── linux.json      # Linux-specific config
```

## Manifest Configuration

The `manifest.json` defines extension metadata and configuration:

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Package identifier (e.g., `mcp-server-langgraph`) |
| `version` | string | SemVer version (e.g., `1.0.0`) |
| `description` | string | Human-readable description |
| `author` | string | Author or organization |
| `license` | string | SPDX license identifier |

### Server Configuration

```json
{
  "server": {
    "type": "python",
    "entry": "server/main.py",
    "runtime_version": ">=3.12"
  }
}
```

### MCP Configuration

Defines how Claude Desktop launches the server:

```json
{
  "mcp_config": {
    "command": "${__dirname}/server/venv/bin/python",
    "args": ["${__dirname}/server/main.py"],
    "env": {
      "MCP_SERVER_HOST": "localhost",
      "MCP_SERVER_PORT": "8765"
    }
  }
}
```

### Platform Overrides

Platform-specific command paths:

```json
{
  "platform_overrides": {
    "windows": {
      "command": "${__dirname}\\server\\venv\\Scripts\\python.exe"
    },
    "linux": {
      "command": "${__dirname}/server/venv/bin/python"
    },
    "darwin": {
      "command": "${__dirname}/server/venv/bin/python"
    }
  }
}
```

### User Configuration

Define user-configurable settings that Claude Desktop UI will display:

```json
{
  "user_config": [
    {
      "name": "api_key",
      "label": "API Key",
      "type": "string",
      "secret": true,
      "required": true,
      "description": "LLM provider API key"
    },
    {
      "name": "llm_provider",
      "label": "LLM Provider",
      "type": "enum",
      "values": ["anthropic", "openai", "google", "azure"],
      "default": "anthropic"
    },
    {
      "name": "max_tokens",
      "label": "Max Tokens",
      "type": "integer",
      "default": 4096,
      "min": 256,
      "max": 32000
    },
    {
      "name": "enable_logging",
      "label": "Enable Debug Logging",
      "type": "boolean",
      "default": false
    }
  ]
}
```

## Platform-Specific Considerations

### Windows

- Use backslash paths in `platform_overrides`
- Keychain integration via DPAPI (Windows Credential Manager)
- Python executable: `Scripts\python.exe`

### macOS

- Native Keychain integration for secrets
- Gatekeeper code signing recommended for distribution
- Python executable: `bin/python`

### Linux

- Secret Service API for credential storage
- AppImage or Flatpak packaging options available
- Python executable: `bin/python`

## Security Best Practices

### Secret Handling

1. **Always mark secrets**: Use `"secret": true` for API keys and credentials
2. **Never bundle secrets**: Secrets are stored in platform keychains at runtime
3. **Environment injection**: Secrets are injected as environment variables

### Code Signing

For production distribution:

```bash
# macOS
codesign --deep --force --verify --sign "Developer ID" mcp-server-langgraph.mcpb

# Windows (requires certificate)
signtool sign /f certificate.pfx /p password /fd SHA256 mcp-server-langgraph.mcpb
```

## Dependency Management

The extension bundles its own Python virtual environment:

```bash
# Create isolated environment
uv venv server/venv --python 3.12

# Install dependencies
uv pip install -r requirements.txt --python server/venv/bin/python
```

### Dependency Validation

The build script validates all dependencies:

1. Checks for compatible versions
2. Excludes development dependencies
3. Verifies no conflicting packages

## Distribution Channels

### Claude Desktop Marketplace

1. Build the `.mcpb` package
2. Submit to Claude Desktop marketplace (coming soon)
3. Users install directly from Claude Desktop UI

### Direct Distribution

1. Host `.mcpb` file on your servers
2. Users download and import via Claude Desktop

### Enterprise Distribution

For internal enterprise use:

1. Configure private skill marketplace in Claude Desktop
2. Host `.mcpb` files on internal artifact server
3. Users authenticate and install from enterprise catalog

## Build Options

### CLI Arguments

| Argument | Description |
|----------|-------------|
| `--manifest-only` | Generate manifest.json without building package |
| `--platform` | Target platform: `windows`, `macos`, `linux` |
| `--write-platform-configs` | Generate platform config files |
| `--output-dir` | Output directory for built package |
| `--no-venv` | Skip bundling virtual environment |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `MCPB_VERSION` | Override version in manifest |
| `MCPB_SIGN` | Enable code signing |
| `MCPB_SIGN_IDENTITY` | Code signing identity |

## Troubleshooting

### Common Issues

**"Python not found" error**
- Ensure Python 3.12+ is in the bundled venv
- Check platform-specific paths in manifest

**"Permission denied" on macOS**
- Add executable permissions: `chmod +x server/venv/bin/python`
- May require code signing for Gatekeeper

**Secrets not loading**
- Verify `user_config` fields have correct `name` values
- Check platform keychain permissions

### Debug Mode

Enable verbose logging:

```bash
MCP_DEBUG=1 uv run python packaging/build.py
```

## Testing the Extension

Before distribution:

1. **Unit tests**: `uv run pytest tests/unit/packaging/`
2. **Integration test**: Install in Claude Desktop dev mode
3. **Cross-platform**: Test on all target platforms

## Version Updates

When releasing new versions:

1. Update `version` in `manifest.json`
2. Update `CHANGELOG.md`
3. Run build: `uv run python packaging/build.py`
4. Test installation
5. Publish to distribution channel

## Related Documentation

- [Claude Desktop Extensions](https://docs.anthropic.com/claude-desktop/extensions)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Skills System](../docs-internal/ADR-0072-ANTHROPIC-BEST-PRACTICES.md)
