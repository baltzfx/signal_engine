'use client';

import { useSignals } from '@/contexts/SignalContext';
import { BarChart3, TrendingUp, TrendingDown, Target, Award, Activity } from 'lucide-react';

export default function AnalyticsPage() {
  const { signals } = useSignals();

  // Performance calculations
  const totalSignals = signals.length;
  const openSignals = signals.filter(s => !s.outcome || s.outcome === 'open');
  const closedSignals = signals.filter(s => s.outcome && s.outcome !== 'open');
  const tpHitSignals = closedSignals.filter(s => s.outcome === 'tp_hit');
  const slHitSignals = closedSignals.filter(s => s.outcome === 'sl_hit');
  const expiredSignals = closedSignals.filter(s => s.outcome === 'expired');

  const winRate = closedSignals.length > 0 
    ? ((tpHitSignals.length / closedSignals.length) * 100).toFixed(1) 
    : '0.0';

  const avgReturn = closedSignals.length > 0
    ? (closedSignals.reduce((acc, s) => acc + (s.return_pct || 0), 0) / closedSignals.length).toFixed(2)
    : '0.00';

  const totalReturn = closedSignals.reduce((acc, s) => acc + (s.return_pct || 0), 0).toFixed(2);

  // Symbol performance
  const symbolStats = signals.reduce((acc: any, signal) => {
    if (!acc[signal.symbol]) {
      acc[signal.symbol] = { total: 0, wins: 0, losses: 0, returns: 0 };
    }
    acc[signal.symbol].total++;
    if (signal.outcome === 'tp_hit') {
      acc[signal.symbol].wins++;
      acc[signal.symbol].returns += signal.return_pct || 0;
    } else if (signal.outcome === 'sl_hit') {
      acc[signal.symbol].losses++;
      acc[signal.symbol].returns += signal.return_pct || 0;
    }
    return acc;
  }, {});

  const topPerformers = Object.entries(symbolStats)
    .map(([symbol, stats]: [string, any]) => ({
      symbol,
      winRate: stats.total > 0 ? ((stats.wins / stats.total) * 100).toFixed(1) : '0',
      totalSignals: stats.total,
      returns: stats.returns.toFixed(2),
    }))
    .sort((a, b) => parseFloat(b.returns) - parseFloat(a.returns))
    .slice(0, 10);

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Performance Analytics</h1>
          <p className="text-gray-600">Detailed insights into your signal performance and trading statistics</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl shadow-lg p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <BarChart3 className="w-8 h-8 opacity-80" />
              <span className="text-sm font-medium opacity-90">Overall</span>
            </div>
            <h3 className="text-sm font-medium opacity-90 mb-1">Total Signals</h3>
            <p className="text-4xl font-bold">{totalSignals}</p>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl shadow-lg p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Target className="w-8 h-8 opacity-80" />
              <span className="text-sm font-medium opacity-90">Success</span>
            </div>
            <h3 className="text-sm font-medium opacity-90 mb-1">Win Rate</h3>
            <p className="text-4xl font-bold">{winRate}%</p>
            <p className="text-xs opacity-75 mt-1">{tpHitSignals.length} wins / {closedSignals.length} closed</p>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl shadow-lg p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-8 h-8 opacity-80" />
              <span className="text-sm font-medium opacity-90">Average</span>
            </div>
            <h3 className="text-sm font-medium opacity-90 mb-1">Avg Return</h3>
            <p className="text-4xl font-bold">{avgReturn}%</p>
            <p className="text-xs opacity-75 mt-1">Per closed signal</p>
          </div>

          <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl shadow-lg p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Award className="w-8 h-8 opacity-80" />
              <span className="text-sm font-medium opacity-90">Total</span>
            </div>
            <h3 className="text-sm font-medium opacity-90 mb-1">Total Return</h3>
            <p className="text-4xl font-bold">{totalReturn}%</p>
            <p className="text-xs opacity-75 mt-1">Cumulative</p>
          </div>
        </div>

        {/* Signal Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Status Distribution */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-600" />
              Signal Status Distribution
            </h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                  <span className="text-gray-700">Open Signals</span>
                </div>
                <span className="font-bold text-gray-900">{openSignals.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span className="text-gray-700">TP Hit</span>
                </div>
                <span className="font-bold text-gray-900">{tpHitSignals.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span className="text-gray-700">SL Hit</span>
                </div>
                <span className="font-bold text-gray-900">{slHitSignals.length}</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full bg-gray-400"></div>
                  <span className="text-gray-700">Expired</span>
                </div>
                <span className="font-bold text-gray-900">{expiredSignals.length}</span>
              </div>
            </div>
          </div>

          {/* Win/Loss Ratio */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
              <Target className="w-5 h-5 text-indigo-600" />
              Win/Loss Analysis
            </h2>
            <div className="space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-600">Win Rate</span>
                  <span className="text-sm font-bold text-green-600">{winRate}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className="bg-gradient-to-r from-green-400 to-green-600 h-3 rounded-full transition-all"
                    style={{ width: `${winRate}%` }}
                  ></div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 pt-4">
                <div className="text-center p-4 bg-green-50 rounded-lg">
                  <TrendingUp className="w-6 h-6 text-green-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Wins</p>
                  <p className="text-2xl font-bold text-green-600">{tpHitSignals.length}</p>
                </div>
                <div className="text-center p-4 bg-red-50 rounded-lg">
                  <TrendingDown className="w-6 h-6 text-red-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Losses</p>
                  <p className="text-2xl font-bold text-red-600">{slHitSignals.length}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Top Performing Symbols */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Top Performing Symbols</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-600">Symbol</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">Signals</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">Win Rate</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-600">Return</th>
                </tr>
              </thead>
              <tbody>
                {topPerformers.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-gray-500">
                      No closed signals data available yet
                    </td>
                  </tr>
                ) : (
                  topPerformers.map((item, idx) => (
                    <tr key={item.symbol} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-4 px-4">
                        <span className="font-bold text-gray-900">{item.symbol}</span>
                      </td>
                      <td className="text-right py-4 px-4 text-gray-700">{item.totalSignals}</td>
                      <td className="text-right py-4 px-4">
                        <span className={`font-semibold ${parseFloat(item.winRate) >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                          {item.winRate}%
                        </span>
                      </td>
                      <td className="text-right py-4 px-4">
                        <span className={`font-bold ${parseFloat(item.returns) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {parseFloat(item.returns) >= 0 ? '+' : ''}{item.returns}%
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
  );
}
