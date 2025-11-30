# MCP Server with LangGraph - Benchmarking Suite

This directory contains performance benchmarking tools and results for MCP Server with LangGraph.

## Overview

The benchmarking suite measures:
- **Throughput**: Requests per second under sustained load
- **Latency**: Response time percentiles (p50, p95, p99)
- **Concurrency**: Maximum concurrent requests supported
- **Scalability**: Performance degradation under increasing load
- **Resource Usage**: CPU, memory, network utilization

## Benchmark Scenarios

### 1. Simple Agent Workflow
- **Description**: Single-node agent with basic tool execution
- **Metrics**: Baseline performance for minimal overhead
- **Use Case**: Lightweight agents, chatbots, simple Q&A

### 2. Multi-Agent Coordination
- **Description**: 3-agent workflow with sequential execution
- **Metrics**: Overhead of multi-agent orchestration
- **Use Case**: Research workflows, content generation pipelines

### 3. Complex State Management
- **Description**: 5-node graph with conditional branching
- **Metrics**: State persistence and checkpointing performance
- **Use Case**: Long-running workflows, human-in-the-loop patterns

### 4. High Concurrency Load
- **Description**: 100+ concurrent requests
- **Metrics**: Horizontal scaling capabilities
- **Use Case**: Production deployments, high-traffic applications

## Running Benchmarks

### Prerequisites

```bash
# Install k6 (load testing tool)
brew install k6  # macOS
# OR
sudo apt-get install k6  # Ubuntu/Debian

# Install Python dependencies
pip install -r requirements-bench.txt
```

### Quick Start

```bash
# Run all benchmarks
make benchmark

# Run specific scenario
k6 run scenarios/simple-agent.js

# Run with custom parameters
k6 run --vus 50 --duration 5m scenarios/multi-agent.js
```

### Configuration

Edit `config.json` to customize:
- `target_url`: MCP Server endpoint
- `duration`: Test duration (default: 5 minutes)
- `vus`: Virtual users (concurrent requests)
- `ramp_up_time`: Gradual load increase period

## Interpreting Results

### Key Metrics

**Throughput (req/s)**
- **Good**: >100 req/s for simple workflows
- **Excellent**: >500 req/s for complex workflows

**Latency (ms)**
- **p50 (median)**: <500ms typical
- **p95**: <2000ms acceptable
- **p99**: <5000ms for complex workflows

**Error Rate**
- **Target**: <0.1% under normal load
- **Acceptable**: <1% under stress conditions

### Sample Results

```
Scenario: Simple Agent Workflow
VUs: 10, Duration: 5m

✓ http_req_duration.............avg=245ms  p95=890ms  p99=1.2s
✓ http_reqs......................125/s (37,500 total)
✓ http_req_failed................0.02%
✓ data_received..................2.1 MB/s
```

## Benchmark Results Archive

Benchmark results are stored in this directory after running benchmarks.

## Comparison Methodology

When comparing frameworks:
1. **Identical Hardware**: Same VM/container specifications
2. **Same LLM Provider**: Use same model (e.g., Gemini Flash) for all tests
3. **Equivalent Workflows**: Map workflows to be functionally equivalent
4. **Multiple Runs**: Average of 3+ test runs for reliability
5. **Documented Conditions**: Document all configuration parameters

## Contributing

To add new benchmark scenarios:
1. Create scenario file in `scenarios/`
2. Add documentation to this README
3. Submit PR with results from reference hardware
4. Include comparison with previous versions

## Reference Hardware

Official benchmarks run on:
- **CPU**: 4 vCPUs (Intel Xeon @ 2.3GHz)
- **Memory**: 16 GB RAM
- **Network**: 10 Gbps
- **Storage**: SSD (provisioned IOPS)
- **Platform**: Google Cloud (n2-standard-4)

## Troubleshooting

**High Error Rates**
- Reduce VUs or increase ramp-up time
- Check server logs for bottlenecks
- Verify resource limits (CPU, memory)

**Inconsistent Results**
- Ensure no other processes consuming resources
- Run multiple iterations and average
- Check for network latency variance

**Low Throughput**
- Profile application code for bottlenecks
- Check database query performance
- Verify LLM API rate limits not hit

## Tools Used

- **k6**: HTTP load testing ([k6.io](https://k6.io))
- **Grafana**: Metrics visualization
- **Prometheus**: Metrics collection
- **LangSmith**: LLM-specific tracing and cost tracking

## License

Same as parent project (MIT-style).
