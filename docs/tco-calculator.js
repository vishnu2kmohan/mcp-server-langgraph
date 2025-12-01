/**
 * TCO Calculator - Dynamic Cost Calculation for AI Agent Frameworks
 *
 * This script provides interactive cost calculations for the TCO Calculator
 * in the MCP Server documentation.
 *
 * Updated: 2025-12-01
 */

(function() {
  'use strict';

  // ==============================================================================
  // LLM PRICING TABLE (per 1M tokens - input/output)
  // ==============================================================================
  const LLM_PRICING = {
    // Google Gemini (Recommended - Primary)
    'gemini-2.5-flash': { input: 0.30, output: 2.50, name: 'Gemini 2.5 Flash' },
    'gemini-2.5-flash-lite': { input: 0.10, output: 0.40, name: 'Gemini 2.5 Flash Lite' },
    'gemini-2.5-pro': { input: 1.25, output: 10.00, name: 'Gemini 2.5 Pro' },
    'gemini-3-pro-preview': { input: 2.00, output: 12.00, name: 'Gemini 3 Pro Preview' },
    // Anthropic Claude 4.5 (Fallback)
    'claude-4.5-haiku': { input: 1.00, output: 5.00, name: 'Claude 4.5 Haiku' },
    'claude-4.5-sonnet': { input: 3.00, output: 15.00, name: 'Claude 4.5 Sonnet' },
    'claude-4.5-opus': { input: 5.00, output: 25.00, name: 'Claude 4.5 Opus' },
    // OpenAI GPT-5.x (Last Resort)
    'gpt-5.1': { input: 1.25, output: 10.00, name: 'GPT-5.1' },
    'gpt-5.1-thinking': { input: 2.50, output: 15.00, name: 'GPT-5.1 Thinking' },
    'gpt-5-mini': { input: 0.25, output: 2.00, name: 'GPT-5 Mini' },
    'gpt-5-nano': { input: 0.05, output: 0.40, name: 'GPT-5 Nano' }
  };

  // ==============================================================================
  // FRAMEWORK BASELINE COSTS (at 1M requests/month, 1000 tokens/request, 3 devs)
  // ==============================================================================
  const BASELINE = {
    requestVolume: 1000000,
    tokensPerRequest: 1000,
    teamSize: 3
  };

  const FRAMEWORKS = {
    mcpK8s: {
      name: 'MCP Server (Kubernetes)',
      color: { bg: '#ecfdf5', border: '#10b981', accent: '#d1fae5' },
      baseline: {
        infrastructure: 350,
        llmApi: 420,          // Gemini 2.5 Flash @ $0.30/$2.50 per 1M tokens
        observability: 50,
        storage: 20,
        networking: 15,
        devOpsTime: 500
      },
      notes: {
        infrastructure: 'GKE cluster (4 pods, n2-standard-4)',
        llmApi: 'Based on selected LLM model',
        observability: 'LangSmith + Prometheus + Grafana',
        storage: 'PostgreSQL + Redis (state/checkpoints)',
        networking: 'Load balancer + egress',
        devOpsTime: '~10 hours/month @ $50/hr (maintenance)'
      },
      savings: true
    },
    mcpCloudRun: {
      name: 'MCP Server (Cloud Run)',
      color: { bg: '#eff6ff', border: '#3b82f6', accent: '#dbeafe' },
      baseline: {
        infrastructure: 600,
        llmApi: 420,          // Gemini 2.5 Flash @ $0.30/$2.50 per 1M tokens
        observability: 50,
        storage: 30,
        networking: 25,
        devOpsTime: 200
      },
      notes: {
        infrastructure: 'Serverless container hosting',
        llmApi: 'Based on selected LLM model',
        observability: 'LangSmith + Cloud Monitoring',
        storage: 'Cloud SQL + Memorystore',
        networking: 'Cloud Load Balancer',
        devOpsTime: '~4 hours/month (less maintenance)'
      },
      savings: true
    },
    langgraphCloud: {
      name: 'LangGraph Cloud',
      color: { bg: '#fef3c7', border: '#f59e0b', accent: '#fde68a' },
      baseline: {
        infrastructure: 5000,  // Platform fees bundled
        llmApi: 0,            // Included in platform
        observability: 0,     // LangSmith included
        storage: 0,           // Included
        networking: 100,      // Uptime fees
        devOpsTime: 0         // Fully managed
      },
      notes: {
        infrastructure: '$0.001/node × 5M node executions',
        llmApi: 'Included in platform fees',
        observability: 'LangSmith included',
        storage: 'Included in platform',
        networking: 'Always-on deployment',
        devOpsTime: 'Fully managed'
      },
      managed: true
    },
    openaiAgentKit: {
      name: 'OpenAI AgentKit',
      color: { bg: '#fce7f3', border: '#ec4899', accent: '#fbcfe8' },
      baseline: {
        infrastructure: 0,
        llmApi: 1688,         // GPT-5.1 @ $1.25/$10 per 1M tokens
        observability: 0,
        storage: 20,
        networking: 500,
        devOpsTime: 0
      },
      notes: {
        infrastructure: 'No separate AgentKit fee',
        llmApi: '1B tokens @ $1.25/$10 per 1M tokens (GPT-5.1)',
        observability: 'Basic Evals included',
        storage: '200 GB-days @ $0.10/GB-day',
        networking: '50K searches @ $10/1K calls',
        devOpsTime: 'Fully managed'
      },
      managed: true,
      vendorLocked: true
    },
    crewai: {
      name: 'CrewAI',
      color: { bg: '#f3f4f6', border: '#6b7280', accent: '#e5e7eb' },
      baseline: {
        infrastructure: 200,
        llmApi: 420,          // Gemini 2.5 Flash @ $0.30/$2.50 per 1M tokens
        observability: 0,
        storage: 10,
        networking: 5,
        devOpsTime: 800
      },
      notes: {
        infrastructure: 'Single VM (n2-standard-2)',
        llmApi: 'Based on selected LLM model',
        observability: 'Basic logging only',
        storage: 'Local SQLite (not production-ready)',
        networking: 'Minimal',
        devOpsTime: '~16 hours/month (manual setup)'
      }
    },
    googleAdk: {
      name: 'Google ADK',
      color: { bg: '#fef2f2', border: '#ef4444', accent: '#fee2e2' },
      baseline: {
        infrastructure: 1500,
        llmApi: 1688,         // Gemini 2.5 Pro @ $1.25/$10 per 1M tokens
        observability: 100,
        storage: 30,
        networking: 20,
        devOpsTime: 300
      },
      notes: {
        infrastructure: 'Vertex AI Agent Engine platform fees',
        llmApi: '1B tokens @ $1.25/$10 per 1M tokens (Gemini 2.5 Pro)',
        observability: 'Cloud Monitoring + Trace',
        storage: 'Agent state/artifacts',
        networking: 'VPC, load balancer',
        devOpsTime: '~6 hours/month'
      }
    }
  };

  // ==============================================================================
  // SCALING MULTIPLIERS
  // ==============================================================================

  function getComplexityMultiplier(complexity) {
    switch(complexity) {
      case 'simple': return 0.7;
      case 'moderate': return 1.0;
      case 'complex': return 1.5;
      default: return 1.0;
    }
  }

  function getRegionMultiplier(region) {
    switch(region) {
      case 'us': return 1.0;
      case 'eu': return 1.15;  // GDPR compliance overhead
      case 'asia': return 1.10;
      default: return 1.0;
    }
  }

  // ==============================================================================
  // COST CALCULATION FUNCTIONS
  // ==============================================================================

  function calculateLlmCost(requestVolume, tokensPerRequest, llmModel) {
    const pricing = LLM_PRICING[llmModel];
    if (!pricing) return 0;

    const totalTokens = requestVolume * tokensPerRequest;
    // Assume 30% input, 70% output token ratio for agent workloads
    const inputTokens = totalTokens * 0.3;
    const outputTokens = totalTokens * 0.7;

    return (inputTokens * pricing.input + outputTokens * pricing.output) / 1000000;
  }

  function calculateFrameworkCosts(frameworkKey, inputs) {
    const framework = FRAMEWORKS[frameworkKey];
    const base = framework.baseline;

    const volumeMultiplier = inputs.requestVolume / BASELINE.requestVolume;
    const tokenMultiplier = inputs.tokensPerRequest / BASELINE.tokensPerRequest;
    const teamMultiplier = inputs.teamSize / BASELINE.teamSize;
    const complexityMultiplier = getComplexityMultiplier(inputs.workflowComplexity);
    const regionMultiplier = getRegionMultiplier(inputs.deploymentRegion);

    // Calculate each cost component
    let costs = {};

    // Infrastructure: logarithmic scaling with volume
    costs.infrastructure = Math.round(base.infrastructure * Math.pow(volumeMultiplier, 0.3) * regionMultiplier);

    // LLM API: calculated from selected model (unless managed platform with included LLM)
    if (framework.managed && base.llmApi === 0) {
      // Managed platforms have bundled LLM costs
      costs.llmApi = 0;
    } else if (framework.vendorLocked) {
      // Vendor-locked platforms use their own pricing
      costs.llmApi = Math.round(base.llmApi * volumeMultiplier * tokenMultiplier);
    } else {
      // Self-hosted: use selected LLM model
      costs.llmApi = Math.round(calculateLlmCost(inputs.requestVolume, inputs.tokensPerRequest, inputs.llmModel));
    }

    // Observability: mostly fixed, slight scaling
    costs.observability = Math.round(base.observability * Math.pow(volumeMultiplier, 0.1));

    // Storage: sub-linear scaling
    costs.storage = Math.round(base.storage * Math.pow(volumeMultiplier, 0.4) * regionMultiplier);

    // Networking: linear with volume
    costs.networking = Math.round(base.networking * volumeMultiplier * regionMultiplier);

    // DevOps: scales with team and complexity
    costs.devOpsTime = Math.round(base.devOpsTime * teamMultiplier * complexityMultiplier);

    // Total
    costs.total = costs.infrastructure + costs.llmApi + costs.observability +
                  costs.storage + costs.networking + costs.devOpsTime;

    // Cost per 1000 requests
    costs.perThousand = (costs.total / (inputs.requestVolume / 1000)).toFixed(2);

    return costs;
  }

  function calculateAllCosts(inputs) {
    const allCosts = {};
    for (const key of Object.keys(FRAMEWORKS)) {
      allCosts[key] = calculateFrameworkCosts(key, inputs);
    }
    return allCosts;
  }

  // ==============================================================================
  // DISPLAY UPDATE FUNCTIONS
  // ==============================================================================

  function formatCurrency(value) {
    return '$' + Math.round(value).toLocaleString();
  }

  function formatVolume(value) {
    if (value >= 1000000) {
      return (value / 1000000).toFixed(1) + 'M';
    }
    return (value / 1000).toFixed(0) + 'K';
  }

  function updateDisplayValues(inputs) {
    // Update slider display labels
    const volumeDisplay = document.getElementById('requestVolumeDisplay');
    if (volumeDisplay) {
      volumeDisplay.textContent = formatVolume(inputs.requestVolume) + ' requests/month';
    }

    const tokensDisplay = document.getElementById('tokensDisplay');
    if (tokensDisplay) {
      tokensDisplay.textContent = inputs.tokensPerRequest.toLocaleString() + ' tokens/request';
    }

    const teamDisplay = document.getElementById('teamSizeDisplay');
    if (teamDisplay) {
      teamDisplay.textContent = inputs.teamSize + ' developer' + (inputs.teamSize > 1 ? 's' : '');
    }
  }

  function updateCostTables(allCosts, referenceTotal) {
    // Reference is LangGraph Cloud for savings comparison
    if (!referenceTotal) {
      referenceTotal = allCosts.langgraphCloud?.total || 5100;
    }

    for (const [key, costs] of Object.entries(allCosts)) {
      const framework = FRAMEWORKS[key];

      // Update cost cells
      updateCell(key, 'infrastructure', costs.infrastructure, framework.notes.infrastructure);
      updateCell(key, 'llmApi', costs.llmApi, framework.notes.llmApi);
      updateCell(key, 'observability', costs.observability, framework.notes.observability);
      updateCell(key, 'storage', costs.storage, framework.notes.storage);
      updateCell(key, 'networking', costs.networking, framework.notes.networking);
      updateCell(key, 'devOpsTime', costs.devOpsTime, framework.notes.devOpsTime);

      // Update total
      const totalCell = document.getElementById(key + '-total');
      if (totalCell) {
        totalCell.textContent = formatCurrency(costs.total) + '/month';
      }

      // Update per-1000 cost
      const perThousandCell = document.getElementById(key + '-perThousand');
      if (perThousandCell) {
        perThousandCell.textContent = '$' + costs.perThousand + ' per 1,000 requests';
      }

      // Update savings (if applicable)
      if (framework.savings && costs.total < referenceTotal) {
        const savingsCell = document.getElementById(key + '-savings');
        if (savingsCell) {
          const savings = referenceTotal - costs.total;
          const percentage = Math.round((savings / referenceTotal) * 100);
          savingsCell.textContent = formatCurrency(savings) + '/month vs LangGraph Cloud (' + percentage + '% cheaper)';
        }
      }
    }
  }

  function updateCell(frameworkKey, costType, value, note) {
    const cell = document.getElementById(frameworkKey + '-' + costType);
    if (cell) {
      cell.textContent = formatCurrency(value);
      if (note) {
        cell.title = note;
      }
    }
  }

  function updateComparisonChart(allCosts) {
    const chartContainer = document.getElementById('costComparisonChart');
    if (!chartContainer) return;

    const maxCost = Math.max(...Object.values(allCosts).map(c => c.total));

    let chartHtml = '<div style="font-family: var(--font-mono, monospace); font-size: 14px; color: var(--text-color, inherit);">';
    chartHtml += '<div style="margin-bottom: 15px; font-weight: bold; font-size: 16px;">Framework TCO Comparison</div>';

    // Sort by total cost
    const sorted = Object.entries(allCosts).sort((a, b) => a[1].total - b[1].total);

    for (const [key, costs] of sorted) {
      const framework = FRAMEWORKS[key];
      const width = Math.max(5, Math.round((costs.total / maxCost) * 100));

      chartHtml += '<div style="display: flex; align-items: center; margin-bottom: 10px;">';
      chartHtml += '<span style="width: 180px; flex-shrink: 0; font-size: 13px;">' + framework.name + '</span>';
      chartHtml += '<div style="flex: 1; height: 24px; background: var(--border-color, rgba(0,0,0,0.1)); border-radius: 4px; margin-right: 10px; overflow: hidden;">';
      chartHtml += '<div style="height: 100%; width: ' + width + '%; background: ' + framework.color.border + '; border-radius: 4px; transition: width 0.3s ease;"></div>';
      chartHtml += '</div>';
      chartHtml += '<span style="width: 100px; text-align: right; font-weight: bold; font-size: 14px;">' + formatCurrency(costs.total) + '</span>';
      chartHtml += '</div>';
    }

    chartHtml += '</div>';
    chartContainer.innerHTML = chartHtml;

    // Update best value display
    updateBestValueDisplay(sorted, allCosts);
  }

  function updateBestValueDisplay(sorted, allCosts) {
    const bestValueDisplay = document.getElementById('bestValueDisplay');
    if (!bestValueDisplay || sorted.length === 0) return;

    const [bestKey, bestCosts] = sorted[0];
    const bestFramework = FRAMEWORKS[bestKey];
    const langgraphCost = allCosts.langgraphCloud?.total || 5100;
    const savingsPercent = Math.round(((langgraphCost - bestCosts.total) / langgraphCost) * 100);

    bestValueDisplay.innerHTML = '<strong>Best Value</strong>: ' + bestFramework.name +
      ' - <strong>' + formatCurrency(bestCosts.total) + '/month</strong>' +
      (savingsPercent > 0 ? ' (' + savingsPercent + '% cheaper than managed platforms)' : '');
  }

  // ==============================================================================
  // INITIALIZATION
  // ==============================================================================

  function getInputValues() {
    return {
      requestVolume: parseInt(document.getElementById('requestVolume')?.value) || 1000000,
      tokensPerRequest: parseInt(document.getElementById('tokensPerRequest')?.value) || 1000,
      teamSize: parseInt(document.getElementById('teamSize')?.value) || 3,
      workflowComplexity: document.getElementById('workflowComplexity')?.value || 'moderate',
      deploymentRegion: document.getElementById('deploymentRegion')?.value || 'us',
      llmModel: document.getElementById('llmModel')?.value || 'gemini-2.5-flash'
    };
  }

  function updateCalculator() {
    const inputs = getInputValues();
    updateDisplayValues(inputs);

    const allCosts = calculateAllCosts(inputs);
    updateCostTables(allCosts, allCosts.langgraphCloud?.total);
    updateComparisonChart(allCosts);
  }

  function initialize() {
    // Attach event listeners to all inputs
    const inputIds = [
      'requestVolume', 'tokensPerRequest', 'teamSize',
      'workflowComplexity', 'deploymentRegion', 'llmModel'
    ];

    for (const id of inputIds) {
      const element = document.getElementById(id);
      if (element) {
        element.addEventListener('input', updateCalculator);
        element.addEventListener('change', updateCalculator);
      }
    }

    // Initial calculation
    updateCalculator();

    console.log('TCO Calculator initialized successfully');
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
  } else {
    // DOM already loaded (script loaded async)
    initialize();
  }

  // Also try to reinitialize after a delay (Mintlify may load content dynamically)
  setTimeout(initialize, 1000);
  setTimeout(initialize, 3000);
})();
