# OpenFGA Modular Authorization Model

This directory contains the OpenFGA authorization model split into logical modules
for better maintainability and understanding.

## Module Structure

| Module | Types | Purpose |
|--------|-------|---------|
| `01-core.fga` | user, organization, service_principal | Base identity types |
| `02-resources.fga` | tool, workflow, session, project, artifact, conversation, vector_store | Main business resources |
| `03-observability.fga` | dashboard, logs, traces, metrics, observability | Monitoring and telemetry |
| `04-access-control.fga` | authz, system, api_key | Authentication & authorization |
| `05-ai-agents.fga` | ai, agent | AI and agent configuration |
| `06-skills.fga` | skill, marketplace | Skills and marketplace |
| `07-semantic-index.fga` | tool_index, skill_index, memory_index | Semantic search indices |
| `08-infrastructure.fga` | gateway, identity, mcp, mcp_connection, connection | Infrastructure access |
| `09-financial.fga` | cost, budget, execution, compliance, config, chat | Financial and compliance |

## Composition

The modules are composed into `model.json` using the `compose_model.py` script:

```bash
python config/openfga/compose_model.py
```

This generates:
- `config/openfga/model.json` - The combined JSON model for OpenFGA

## Module Format

Each module uses OpenFGA DSL format (`.fga` extension):

```fga
type user

type organization
  relations
    define member: [user]
    define admin: [user]
```

## Validation

After composition, validate the model:

```bash
fga model validate config/openfga/model.json
uv run pytest tests/unit/auth/test_openfga_model_inheritance.py -v
```

## ADR References

- ADR-0002: OpenFGA Authorization (main)
- ADR-0068: Gateway-Level Auth + OpenFGA Updates
- ADR-0099: Semantic Tool Selection
