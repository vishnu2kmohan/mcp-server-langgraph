# ADR-0043: Cost Monitoring Dashboard

## Status

**Accepted** - 2025-11-02

## Context

As the MCP server handles multiple LLM providers (Anthropic, OpenAI, Google Gemini, etc.) with varying pricing models, there's a critical need for:

1. **Real-time cost tracking**: Monitor token usage and costs across all LLM providers
2. **Budget monitoring**: Track spending against budgets and alert on overages
3. **Cost attribution**: Break down costs by user, session, model, and feature
4. **Trend analysis**: Identify cost patterns and optimization opportunities
5. **Financial accountability**: Provide stakeholders with transparent cost visibility

Without centralized cost monitoring, organizations risk:
- Unexpected LLM API bills
- Inability to attribute costs to specific users or projects
- Lack of visibility into cost optimization opportunities
- Difficulty forecasting future spending

## Decision

We will implement a **Cost Monitoring Dashboard** with the following architecture:

### **Backend: Cost Tracking API**

**Location**: `src/mcp_server_langgraph/monitoring/cost_tracker.py`

**Components**:
1. **CostMetricsCollector**: Captures token usage and calculates costs
2. **CostAggregator**: Aggregates costs by dimensions (user, model, session, feature)
3. **BudgetMonitor**: Tracks spending against budgets and triggers alerts
4. **CostAPI**: FastAPI endpoints for retrieving cost data

**Data Model**:
```python
class TokenUsage(BaseModel):
    """Token usage for a single LLM call."""
    timestamp: datetime
    user_id: str
    session_id: str
    model: str
    provider: str  # anthropic, openai, google
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal
    feature: Optional[str]  # e.g., "chat", "tool_execution"
    metadata: Dict[str, Any]

class CostSummary(BaseModel):
    """Aggregated cost summary."""
    period_start: datetime
    period_end: datetime
    total_cost_usd: Decimal
    total_tokens: int
    request_count: int
    by_model: Dict[str, Decimal]
    by_user: Dict[str, Decimal]
    by_feature: Dict[str, Decimal]
    top_cost_sessions: List[Tuple[str, Decimal]]
```

**API Endpoints**:
```
GET  /api/cost/summary?period={period}&group_by={dimension}
GET  /api/cost/usage?start={start}&end={end}&user_id={user_id}
GET  /api/cost/budget?budget_id={id}
POST /api/cost/budget
GET  /api/cost/trends?metric={metric}&period={period}
GET  /api/cost/export?format={csv|json}
```

### **Storage: Time-Series Database**

**Options Evaluated**:
1. **Prometheus + PostgreSQL** (Selected)
   - Prometheus for real-time metrics
   - PostgreSQL for detailed cost history
   - Leverages existing infrastructure

2. **ClickHouse** (Alternative)
   - Excellent for time-series analytics
   - Requires new infrastructure

3. **TimescaleDB** (Alternative)
   - PostgreSQL extension for time-series
   - Good middle ground

**Decision**: Use **Prometheus for metrics** + **PostgreSQL for detailed records**
- Prometheus: Counter metrics for tokens/costs (real-time)
- PostgreSQL: Full cost records (audit trail, detailed queries)

### **Frontend: Grafana Dashboard**

**Primary Option**: Grafana dashboard (leverages existing observability stack)

**Dashboard Panels**:
1. **Cost Overview**
   - Total spend (current month)
   - Daily burn rate
   - Budget utilization (%)
   - Cost trend (7/30/90 days)

2. **Usage Metrics**
   - Token usage by model
   - Requests per model
   - Average cost per request
   - Peak usage times

3. **Attribution**
   - Top users by cost
   - Cost by feature/endpoint
   - Session-level costs
   - Department/team breakdown

4. **Budget Monitoring**
   - Budget vs. actual
   - Remaining budget
   - Projected end-of-month cost
   - Alert thresholds

5. **Model Comparison**
   - Cost per model
   - Token efficiency
   - Response time vs. cost
   - Quality metrics vs. cost

**Grafana Configuration**: `deployments/helm/mcp-server-langgraph/dashboards/cost-monitoring.json`

### **Alternative: React Dashboard** (Optional enhancement)

For organizations wanting embedded dashboards:

**Location**: `src/mcp_server_langgraph/monitoring/dashboard/`

**Tech Stack**:
- React + TypeScript
- Recharts for visualizations
- Tailwind CSS for styling
- Axios for API calls

**Advantages**:
- Embedded in application
- Custom branding
- Interactive drill-downs
- Export capabilities

**Disadvantages**:
- Additional maintenance
- Duplicates Grafana functionality

### **Cost Calculation Logic**

**Pricing Strategy**:
```python
# src/mcp_server_langgraph/monitoring/pricing.py

PRICING_TABLE = {
    "anthropic": {
        "claude-3-5-sonnet-20241022": {
            "input": Decimal("0.003"),   # $ per 1K tokens
            "output": Decimal("0.015"),
        },
        "claude-3-5-haiku-20241022": {
            "input": Decimal("0.0008"),
            "output": Decimal("0.004"),
        },
    },
    "openai": {
        "gpt-4-turbo": {
            "input": Decimal("0.01"),
            "output": Decimal("0.03"),
        },
        "gpt-4o-mini": {
            "input": Decimal("0.00015"),
            "output": Decimal("0.0006"),
        },
    },
    "google": {
        "gemini-2.5-flash-preview-001": {
            "input": Decimal("0.000075"),  # FREE tier pricing
            "output": Decimal("0.0003"),
        },
    },
}

def calculate_cost(
    model: str,
    provider: str,
    prompt_tokens: int,
    completion_tokens: int
) -> Decimal:
    """Calculate cost for LLM call."""
    pricing = PRICING_TABLE[provider][model]
    input_cost = (Decimal(prompt_tokens) / 1000) * pricing["input"]
    output_cost = (Decimal(completion_tokens) / 1000) * pricing["output"]
    return input_cost + output_cost
```

**Update Frequency**: Pricing table updated monthly via configuration

### **Integration Points**

**1. LLM Factory Instrumentation**

Modify `src/mcp_server_langgraph/llm/llm_factory.py`:
```python
from ..monitoring.cost_tracker import CostMetricsCollector

class LLMFactory:
    def __init__(self):
        self.cost_tracker = CostMetricsCollector()

    async def invoke(self, prompt, **kwargs):
        response = await super().invoke(prompt, **kwargs)

        # Track cost
        await self.cost_tracker.record_usage(
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_id"),
            model=self.model,
            provider=self.provider,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

        return response
```

**2. Prometheus Metrics**

```python
from prometheus_client import Counter, Histogram

llm_token_usage = Counter(
    "llm_token_usage_total",
    "Total tokens used by LLM calls",
    ["provider", "model", "token_type"]  # token_type: input/output
)

llm_cost = Counter(
    "llm_cost_usd_total",
    "Total estimated cost in USD",
    ["provider", "model"]
)

llm_request_cost = Histogram(
    "llm_request_cost_usd",
    "Cost per request in USD",
    ["provider", "model"]
)
```

**3. Budget Alerts**

```python
# src/mcp_server_langgraph/monitoring/budget_alerts.py

class BudgetMonitor:
    async def check_budget(self, budget_id: str):
        """Check if budget exceeded and send alerts."""
        budget = await self.get_budget(budget_id)
        current_spend = await self.get_period_spend(budget_id)

        utilization = current_spend / budget.limit

        if utilization >= 0.9:
            await self.send_alert(
                level="critical",
                message=f"Budget {budget.name} at {utilization*100:.1f}%"
            )
        elif utilization >= 0.75:
            await self.send_alert(
                level="warning",
                message=f"Budget {budget.name} at {utilization*100:.1f}%"
            )
```

## Consequences

### **Positive**

1. **Financial Visibility**: Real-time insight into LLM spending
2. **Cost Control**: Budget alerts prevent bill shock
3. **Optimization Opportunities**: Identify expensive operations
4. **Accountability**: Attribute costs to users/teams
5. **Compliance**: Audit trail for cost tracking (SOC 2)
6. **Forecasting**: Data for capacity planning

### **Negative**

1. **Storage Overhead**: Cost data adds to database size
2. **Performance Impact**: Minimal (async cost tracking)
3. **Maintenance**: Pricing table requires monthly updates
4. **Complexity**: Additional monitoring infrastructure

### **Mitigations**

1. **Async Tracking**: Cost recording happens asynchronously
2. **Batch Writes**: Aggregate cost data before writing to DB
3. **Data Retention**: Archive cost data older than 13 months
4. **Pricing Automation**: Consider API-based pricing updates

## Implementation Plan

### **Phase 1: Backend (TDD)**
1. Write tests for CostMetricsCollector
2. Implement CostMetricsCollector
3. Write tests for CostAPI endpoints
4. Implement CostAPI
5. Write tests for BudgetMonitor
6. Implement BudgetMonitor

### **Phase 2: Storage**
1. Create PostgreSQL schema for cost_records
2. Set up Prometheus metrics
3. Configure data retention policies

### **Phase 3: Grafana Dashboard**
1. Create cost-monitoring.json dashboard
2. Configure panels for all metrics
3. Set up alert rules

### **Phase 4: Integration**
1. Instrument LLMFactory
2. Add cost tracking to all LLM calls
3. Deploy to staging
4. Validate accuracy

### **Phase 5: Alerts & Automation**
1. Configure budget alerts
2. Set up cost anomaly detection
3. Create automated reports

## Alternatives Considered

### **Alternative 1: Third-Party Cost Tracking (e.g., LangSmith, Helicone)**

**Pros**:
- No custom development
- Advanced analytics out-of-the-box
- Regular pricing updates

**Cons**:
- Additional vendor dependency
- Data privacy concerns
- Monthly SaaS costs ($$$)
- Limited customization

**Decision**: Build in-house for control and privacy

### **Alternative 2: Simple Logging (No Dashboard)**

**Pros**:
- Minimal implementation
- Low overhead

**Cons**:
- No visualization
- Manual analysis required
- No real-time alerts

**Decision**: Rejected - insufficient visibility

## References

- LiteLLM pricing: https://docs.litellm.ai/docs/pricing
- Anthropic pricing: https://www.anthropic.com/pricing
- OpenAI pricing: https://openai.com/pricing
- Google Gemini pricing: https://ai.google.dev/pricing
- Grafana dashboards: https://grafana.com/docs/grafana/latest/dashboards/
- Prometheus best practices: https://prometheus.io/docs/practices/

## Related ADRs

- ADR-0003: Dual Observability (Prometheus + OpenTelemetry)
- ADR-0001: Multi-Provider LLM Support
- ADR-0027: Rate Limiting Strategy (complements cost control)
