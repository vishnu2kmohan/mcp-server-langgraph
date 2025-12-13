/**
 * CostPage
 *
 * Cost tracking dashboard page showing LLM usage costs
 * with summary metrics and breakdown by model.
 */

import { useEffect, useState } from 'react';
import { DollarSign, Loader2, TrendingUp, RefreshCw } from 'lucide-react';

type Period = 'day' | 'week' | 'month';

interface CostSummary {
  total_cost: number;
  total_tokens: number;
  period: string;
}

interface ModelCost {
  model: string;
  cost: number;
  tokens: number;
}

interface CostByModel {
  models: ModelCost[];
}

export function CostPage() {
  const [period, setPeriod] = useState<Period>('week');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [modelCosts, setModelCosts] = useState<ModelCost[]>([]);

  const fetchCostData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Fetch cost summary
      const summaryResponse = await fetch(
        `/api/v1/cost/summary?period=${period}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!summaryResponse.ok) {
        throw new Error('Failed to load cost summary');
      }

      const summaryData: CostSummary = await summaryResponse.json();
      setSummary(summaryData);

      // Fetch cost by model
      const modelResponse = await fetch(
        `/api/v1/cost/by-model?period=${period}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!modelResponse.ok) {
        throw new Error('Failed to load cost by model');
      }

      const modelData: CostByModel = await modelResponse.json();
      setModelCosts(modelData.models || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cost data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCostData();
  }, [period]);

  const formatCurrency = (amount: number): string => {
    return `$${amount.toFixed(2)}`;
  };

  const formatNumber = (num: number): string => {
    return num.toLocaleString();
  };

  const handlePeriodChange = (newPeriod: Period) => {
    setPeriod(newPeriod);
  };

  const handleRetry = () => {
    fetchCostData();
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Cost Dashboard
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Track and analyze LLM usage costs
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Period Selector */}
            <select
              value={period}
              onChange={(e) => handlePeriodChange(e.target.value as Period)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="day">Day</option>
              <option value="week">Week</option>
              <option value="month">Month</option>
            </select>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
            <p className="text-lg mb-4">{error}</p>
            <button
              onClick={handleRetry}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw size={16} />
              Retry
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Cost Summary Cards */}
            {summary && (
              <div className="grid gap-4 md:grid-cols-3">
                {/* Total Cost */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-blue-500" />
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Total Cost
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                      {formatCurrency(summary.total_cost)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Past {summary.period}
                  </div>
                </div>

                {/* Total Tokens */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <TrendingUp size={20} className="text-green-500" />
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Total Tokens
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                      {formatNumber(summary.total_tokens)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Past {summary.period}
                  </div>
                </div>

                {/* Average Cost per Token */}
                <div className="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 mb-2">
                    <DollarSign size={20} className="text-purple-500" />
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Avg Cost/Token
                    </h3>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-gray-900 dark:text-gray-100">
                      {formatCurrency(summary.total_cost / summary.total_tokens * 1000)}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">/1K</span>
                  </div>
                  <div className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    Past {summary.period}
                  </div>
                </div>
              </div>
            )}

            {/* Cost by Model */}
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Cost by Model
                </h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Model
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Cost
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Tokens
                      </th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Avg Cost/1K
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {modelCosts.map((modelCost) => (
                      <tr key={modelCost.model} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-gray-100">
                          {modelCost.model}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900 dark:text-gray-100">
                          {formatCurrency(modelCost.cost)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-400">
                          {formatNumber(modelCost.tokens)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-400">
                          {formatCurrency(modelCost.cost / modelCost.tokens * 1000)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default CostPage;
