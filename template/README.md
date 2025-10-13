# Cookiecutter Template Configuration

This directory contains configuration for using this project as a Cookiecutter template.

## Files

- `cookiecutter.json` - Cookiecutter template variables and default values

## Using This Template

Generate a new MCP server project based on this template:

```bash
# Using uvx (recommended)
uvx cookiecutter gh:vishnu2kmohan/mcp-server-langgraph

# Or using cookiecutter directly
cookiecutter https://github.com/vishnu2kmohan/mcp-server-langgraph
```

## Template Variables

The cookiecutter.json defines variables that will be prompted during project generation:
- `project_name` - Your new project name
- `author_name` - Project author
- `python_version` - Target Python version
- And more...

## Documentation

For detailed template usage instructions, see:
- [Template Usage Guide](../docs/template/usage.md)
- Main [README.md](../README.md) - "Use This Template" section

---

**Note**: This project can be used both as a standalone MCP server and as a Cookiecutter template for generating new projects.
