// Simple Agent Workflow Benchmark
// Tests: Single-node agent with basic tool execution

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 10 },  // Ramp up to 10 VUs over 1 minute
    { duration: '3m', target: 10 },  // Stay at 10 VUs for 3 minutes
    { duration: '1m', target: 0 },   // Ramp down to 0 VUs
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000', 'p(99)<5000'], // 95% under 2s, 99% under 5s
    http_req_failed: ['rate<0.01'],  // Error rate under 1%
    errors: ['rate<0.01'],
  },
};

// Test endpoint configuration
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-key';

export default function () {
  // Simple agent request payload
  const payload = JSON.stringify({
    query: 'What is the capital of France?',
    agent_type: 'simple',
    config: {
      model: 'gemini/gemini-2.5-flash',
      temperature: 0.7,
      max_tokens: 500,
    },
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    timeout: '30s',
  };

  // Make request
  const response = http.post(`${BASE_URL}/api/v1/agents/invoke`, payload, params);

  // Validate response
  const success = check(response, {
    'status is 200': (r) => r.status === 200,
    'response has result': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.result !== undefined;
      } catch (e) {
        return false;
      }
    },
    'response time < 3s': (r) => r.timings.duration < 3000,
  });

  // Track errors
  errorRate.add(!success);

  // Simulate realistic request pacing (users don't send continuous requests)
  sleep(Math.random() * 2 + 1); // Sleep 1-3 seconds between requests
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, opts) {
  const { indent = '', enableColors = false } = opts || {};
  const metrics = data.metrics;

  let summary = '\n\n=== Simple Agent Workflow Benchmark Results ===\n\n';

  if (metrics.http_req_duration) {
    summary += `${indent}Response Time:\n`;
    summary += `${indent}  avg: ${metrics.http_req_duration.values.avg.toFixed(2)}ms\n`;
    summary += `${indent}  p50: ${metrics.http_req_duration.values.p50.toFixed(2)}ms\n`;
    summary += `${indent}  p95: ${metrics.http_req_duration.values.p95.toFixed(2)}ms\n`;
    summary += `${indent}  p99: ${metrics.http_req_duration.values.p99.toFixed(2)}ms\n\n`;
  }

  if (metrics.http_reqs) {
    summary += `${indent}Throughput:\n`;
    summary += `${indent}  total requests: ${metrics.http_reqs.values.count}\n`;
    summary += `${indent}  requests/sec: ${metrics.http_reqs.values.rate.toFixed(2)}\n\n`;
  }

  if (metrics.http_req_failed) {
    const failRate = (metrics.http_req_failed.values.rate * 100).toFixed(2);
    summary += `${indent}Reliability:\n`;
    summary += `${indent}  error rate: ${failRate}%\n\n`;
  }

  return summary;
}
