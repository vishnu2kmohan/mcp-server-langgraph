# 78. Multi-Agent Orchestrator Patterns

Date: 2025-12-21

## Status

Accepted

## Category

Architecture & Multi-Agent Systems

## Context

The MCP server requires complex AI-driven analysis capabilities that involve multiple LLM calls for different purposes:

1. **AI UX Service** (`api/v1/ai_ux_service.py`): Provides composite analysis including:
   - Persona analysis (user behavior patterns)
   - Disclosure analysis (transparency recommendations)
   - Error recovery suggestions
   - Onboarding recommendations
   - Nudge generation

2. **Alert Recommendations** (`api/v1/alert_recommendations.py`): Provides alert analysis including:
   - Alert correlation (grouping related alerts)
   - Root cause analysis
   - Remediation suggestions
   - Pattern detection across alert groups

**Problem**:
- Sequential execution of multiple LLM calls creates latency bottlenecks
- No standardized pattern for parallel task execution
- Code duplication between similar orchestration patterns
- Lack of observability metrics for parallel execution efficiency
- Inconsistent error handling across orchestration implementations

**Target Goals**:
- Parallel execution of independent analysis tasks (3-4x speedup)
- Unified orchestration pattern via abstract base class
- Comprehensive observability metrics for parallel execution
- Graceful degradation with partial results on failures
- Feature flag control for gradual rollout

## Decision

Implement a **multi-agent orchestrator pattern** with the following components:

### 1. Abstract Base Orchestrator

**Location**: `src/mcp_server_langgraph/agents/base_orchestrator.py`

**Design**:
```python
@dataclass
class BaseTask:
    """Base task dataclass for orchestration."""
    task_type: str
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class BaseResult:
    """Base result dataclass for orchestration."""
    task_type: str
    success: bool
    result: dict[str, Any] | None = None
    error: str | None = None

class BaseOrchestrator(ABC, Generic[TaskT, ResultT]):
    """Abstract base class for orchestrators with parallel execution."""

    @property
    @abstractmethod
    def feature_flag_name(self) -> str: ...

    @abstractmethod
    async def _execute_task(self, task: TaskT) -> ResultT: ...

    @abstractmethod
    def synthesize(self, results: list[ResultT]) -> dict[str, Any]: ...

    async def execute(self, tasks: list[TaskT]) -> list[ResultT]:
        """Execute tasks in parallel using asyncio.gather."""
        coroutines = [self._execute_task(task) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        # Convert exceptions to failed results
        return self._process_results(tasks, results)
```

**Benefits**:
- Generic type parameters enable type-safe task/result handling
- Parallel execution via `asyncio.gather` with `return_exceptions=True`
- Automatic exception-to-failed-result conversion
- Feature flag integration for gradual rollout
- Metrics instrumentation support

### 2. UX Orchestrator

**Location**: `src/mcp_server_langgraph/agents/ux_orchestrator.py`

**Analysis Types**:
```python
UX_ANALYSIS_TYPES = [
    "persona_analysis",
    "disclosure_analysis",
    "error_analysis",
    "onboarding_analysis",
    "nudge_analysis",
]
```

**Pattern**:
```
run_composite_analysis(session_context)
    ├── PersonaAnalysis [parallel]
    ├── DisclosureAnalysis [parallel]
    ├── ErrorAnalysis [parallel]
    ├── OnboardingAnalysis [parallel]
    └── NudgeAnalysis [parallel]
         ↓
    Synthesis (cross-insights aggregation)
```

**Feature Flag**: `enable_orchestrated_ai_ux`

### 3. Alert Orchestrator

**Location**: `src/mcp_server_langgraph/agents/alert_orchestrator.py`

**Analysis Types**:
```python
ALERT_ANALYSIS_TYPES = [
    "correlation",
    "root_cause",
    "remediation",
    "pattern_detection",
]
```

**Pattern**:
```
analyze_alerts(alerts)
    ├── CorrelationAnalysis [parallel]
    ├── RootCauseAnalysis [parallel]
    ├── RemediationAnalysis [parallel]
    └── PatternDetection [parallel]
         ↓
    Synthesis (correlation summary)
```

**Feature Flag**: `enable_orchestrated_alert_analysis`

### 4. Observability Metrics

**Location**: `src/mcp_server_langgraph/agents/metrics.py`

**New Metrics**:
```python
# UX Orchestration
ux_orchestration_counter = Counter(
    name="agent.ux_orchestration.count",
    description="Total UX orchestration executions",
)
ux_synthesis_counter = Counter(
    name="agent.ux_synthesis.count",
    description="UX synthesis operations",
)

# Alert Orchestration
alert_orchestration_counter = Counter(
    name="agent.alert_orchestration.count",
    description="Total alert orchestration executions",
)
alert_synthesis_counter = Counter(
    name="agent.alert_synthesis.count",
    description="Alert synthesis operations",
)

# Parallel Execution Performance
parallel_speedup_histogram = Histogram(
    name="agent.orchestration.parallel_speedup",
    description="Speedup ratio from parallel execution",
)
orchestrator_parallel_tasks_histogram = Histogram(
    name="agent.orchestration.parallel_tasks",
    description="Number of parallel tasks per orchestration",
)

# Feature Flag Usage
orchestrator_feature_flag_counter = Counter(
    name="agent.orchestrator.feature_flag.check",
    description="Feature flag checks for orchestrators",
)
```

**Recording Functions**:
- `record_ux_orchestration(task_count, successful_count, duration_ms, success, analysis_types, error_type)`
- `record_alert_orchestration(alert_count, task_count, successful_count, duration_ms, success, analysis_types, correlation_groups)`
- `record_parallel_speedup(orchestrator_type, task_count, parallel_duration_ms, estimated_sequential_ms)`
- `record_ux_synthesis(input_count, cross_insights_count, duration_ms)`
- `record_alert_synthesis(input_count, correlation_groups, patterns_detected, duration_ms)`
- `record_orchestrator_feature_flag_check(orchestrator_type, flag_name, enabled)`

## Architecture

### Module Structure

```
src/mcp_server_langgraph/agents/
├── __init__.py                    # Public API exports
├── base_orchestrator.py           # BaseOrchestrator ABC
├── ux_orchestrator.py             # UXOrchestrator implementation
├── alert_orchestrator.py          # AlertOrchestrator implementation
├── artifacts.py                   # Artifact storage for inter-agent communication
├── coordinator.py                 # Subagent coordination
├── definition.py                  # AgentDefinition & AgentRegistry
├── metrics.py                     # Observability metrics
├── model_selector.py              # LLM model tier selection
├── orchestrator.py                # Generic task decomposition orchestrator
├── resilience.py                  # Orchestrator resilience patterns
└── subagent.py                    # Subagent implementation
```

### Parallel Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator.execute()                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Task 1    │  │   Task 2    │  │   Task 3    │  ...         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │            asyncio.gather(*coroutines,           │           │
│  │              return_exceptions=True)             │           │
│  └──────────────────────────────────────────────────┘           │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Result 1   │  │  Result 2   │  │  Result 3   │              │
│  │  (success)  │  │  (exception │  │  (success)  │              │
│  │             │  │  → failed)  │  │             │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │              Synthesize Results                  │           │
│  │         (aggregate cross-insights)               │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                       │
│                          ▼                                       │
│                 ┌─────────────────┐                             │
│                 │  Final Result   │                             │
│                 │  + Metrics      │                             │
│                 └─────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

### Exception Handling Strategy

```python
async def execute(self, tasks: list[TaskT]) -> list[ResultT]:
    """Execute with graceful exception handling."""
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Convert exception to failed result (partial success possible)
            failed_result = self._create_failed_result(
                task=tasks[i],
                error=str(result),
            )
            final_results.append(failed_result)
        else:
            final_results.append(result)

    return final_results
```

**Benefits**:
- Partial success: 2 out of 3 tasks succeed → return 2 results + 1 failed
- Full exception context preserved in failed result
- Enables synthesize() to work with available results

## Consequences

### Positive

1. **Performance Improvement**
   - 3-4x speedup for multi-task analysis (parallel vs sequential)
   - Measured parallel speedup tracked via histogram metric
   - Reduced end-user latency for composite analysis

2. **Code Reuse**
   - BaseOrchestrator provides common parallel execution logic
   - DRY principle applied across UX and Alert orchestrators
   - New orchestrators can inherit base functionality

3. **Observability**
   - Detailed metrics for orchestration performance
   - Speedup ratio tracking identifies optimization opportunities
   - Feature flag usage tracked for rollout monitoring

4. **Graceful Degradation**
   - Partial failures don't block entire analysis
   - Failed tasks return structured error results
   - Synthesis can work with available results

5. **Feature Flag Control**
   - Gradual rollout with `enable_orchestrated_ai_ux` and `enable_orchestrated_alert_analysis`
   - Easy rollback by disabling flags
   - A/B testing possible

6. **Type Safety**
   - Generic type parameters (`TaskT`, `ResultT`) enable type checking
   - Mypy validates task/result type consistency
   - IDE autocomplete works correctly

### Negative

1. **Complexity**
   - New abstraction layer adds cognitive overhead
   - Generic types require understanding of Python typing
   - Debugging parallel execution requires asyncio knowledge

2. **Testing Overhead**
   - Need to test parallel execution scenarios
   - Mocking concurrent coroutines requires care
   - Integration tests needed for cross-orchestrator behavior

3. **Error Debugging**
   - Parallel errors may have interleaved logs
   - Stack traces from asyncio.gather less clear
   - Need to add trace context for observability

### Mitigations

1. **Documentation**: Comprehensive docstrings and ADR explain patterns
2. **Test Coverage**: 50+ unit tests, 13 integration tests for orchestrators
3. **Observability**: OpenTelemetry integration for distributed tracing
4. **Feature Flags**: Safe rollout with instant rollback capability

## Test Coverage

### Unit Tests (64 tests)

**BaseOrchestrator** (`tests/unit/agents/test_base_orchestrator.py`):
- Module structure and imports (6 tests)
- ABC pattern verification (5 tests)
- BaseTask dataclass (4 tests)
- BaseResult dataclass (4 tests)
- Execute method with empty tasks (3 tests)
- Parallel execution (3 tests)
- Exception handling (3 tests)
- Feature flag integration (2 tests)

**UXOrchestrator** (`tests/unit/agents/test_ux_orchestrator.py`):
- Class structure (5 tests)
- Analysis task creation (5 tests)
- Composite analysis execution (5 tests)
- Synthesis with cross-insights (3 tests)
- Feature flag gating (2 tests)

**AlertOrchestrator** (`tests/unit/agents/test_alert_orchestrator.py`):
- Class structure (5 tests)
- Alert analysis task creation (5 tests)
- Multi-alert analysis (5 tests)
- Correlation grouping (3 tests)
- Pattern detection (2 tests)

**Observability Metrics** (`tests/unit/agents/test_orchestrator_metrics.py`):
- Metric existence (4 tests)
- Recording functions (6 tests)
- UX orchestration recording (3 tests)
- Alert orchestration recording (3 tests)
- Parallel speedup recording (2 tests)
- Feature flag recording (2 tests)

### Integration Tests (13 tests)

**Orchestrator Integration** (`tests/integration/test_orchestrators_integration.py`):
- UX composite analysis end-to-end (2 tests)
- Alert analysis end-to-end (2 tests)
- Partial failure handling (2 tests)
- Parallel performance verification (2 tests)
- Cross-orchestrator concurrent execution (2 tests)
- Large task/alert handling (2 tests)
- Pattern detection integration (1 test)

## Feature Flags

```python
# In core/feature_flags.py

# Phase 11: UX Orchestrator
enable_orchestrated_ai_ux: bool = Field(
    default=False,
    description="Enable parallel AI UX orchestration for composite analysis",
)

# Phase 12: Alert Orchestrator
enable_orchestrated_alert_analysis: bool = Field(
    default=False,
    description="Enable parallel alert orchestration for multi-alert analysis",
)
```

## Performance Expectations

| Scenario | Sequential | Parallel | Speedup |
|----------|------------|----------|---------|
| 3 UX analysis tasks | ~300ms | ~100ms | 3x |
| 4 alert analysis tasks | ~400ms | ~100ms | 4x |
| 5 mixed tasks | ~500ms | ~120ms | 4.2x |

**Note**: Speedup depends on task independence and LLM response times.

## Migration Path

### Backward Compatibility
- Existing AI UX service continues to work (feature flag defaults to false)
- New orchestration is opt-in via feature flags
- API contracts remain unchanged

### Rollout Strategy
1. **Development**: Enable flags, run full test suite
2. **Staging**: A/B test with 10% traffic
3. **Production**: Gradual rollout (10% → 50% → 100%)
4. **Monitoring**: Watch parallel speedup metrics, error rates

### Rollback Plan
- Disable feature flags immediately
- Fall back to sequential execution
- No code changes required

## Related ADRs

- **ADR-0024**: Agentic Loop Implementation
- **ADR-0030**: Resilience Patterns for Production Systems
- **ADR-0074**: AI Suggestions Streaming Cost Tracking
- **ADR-0077**: Claude Agent SDK Integration

## References

- [LangGraph Multi-Agent Patterns](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
- [asyncio.gather Documentation](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather)
- [OpenTelemetry Python Metrics](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [Python ABC and Generics](https://docs.python.org/3/library/abc.html)

---

**Last Updated**: 2025-12-21
**Next Review**: 2026-01-21 (after 1 month in production)
