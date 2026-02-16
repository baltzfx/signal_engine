'use client';

import { useSignals } from '@/contexts/SignalContext';
import { TrendingUp, TrendingDown, Target, Clock, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { signals } = useSignals();

  // Calculate statistics
  const totalSignals = signals.length;
  const openSignals = signals.filter(s => !s.outcome || s.outcome === 'open').length;
  const closedSignals = signals.filter(s => s.outcome && s.outcome !== 'open').length;
  const tpHitSignals = signals.filter(s => s.outcome === 'tp_hit').length;
  const slHitSignals = signals.filter(s => s.outcome === 'sl_hit').length;
  const winRate = closedSignals > 0 ? ((tpHitSignals / closedSignals) * 100).toFixed(1) : '0.0';
  
  const avgReturn = signals
    .filter(s => s.return_pct !== null && s.return_pct !== undefined)
    .reduce((acc, s) => acc + (s.return_pct || 0), 0) / (closedSignals || 1);

  const recentSignals = signals.slice(0, 5);

  const stats = [
    {
      title: 'Active Signals',
      value: openSignals,
      change: '+12%',
      trend: 'up',
      icon: TrendingUp,
      color: 'blue',
    },
    {
      title: 'Win Rate',
      value: `${winRate}%`,
      change: closedSignals > 0 ? `${closedSignals} closed` : 'No data',
      trend: parseFloat(winRate) >= 50 ? 'up' : 'down',
      icon: Target,
      color: 'green',
    },
    {
      title: 'Avg Return',
      value: `${avgReturn >= 0 ? '+' : ''}${avgReturn.toFixed(2)}%`,
      change: closedSignals > 0 ? 'Per signal' : 'No data',
      trend: avgReturn >= 0 ? 'up' : 'down',
      icon: TrendingDown,
      color: avgReturn >= 0 ? 'green' : 'red',
    },
    {
      title: 'Total Signals',
      value: totalSignals,
      change: 'Last 24 hours',
      trend: 'neutral',
      icon: Clock,
      color: 'purple',
    },
  ];

  return (
    <div className="p-4 lg:p-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-gray-600">Welcome back! Here's your signal performance overview.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.title} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className={`p-3 rounded-lg bg-${stat.color}-50`}>
                    <Icon className={`w-6 h-6 text-${stat.color}-600`} />
                  </div>
                  {stat.trend === 'up' && (
                    <span className="flex items-center text-green-600 text-sm font-medium">
                      <ArrowUpRight className="w-4 h-4" />
                      {stat.change}
                    </span>
                  )}
                  {stat.trend === 'down' && (
                    <span className="flex items-center text-red-600 text-sm font-medium">
                      <ArrowDownRight className="w-4 h-4" />
                      {stat.change}
                    </span>
                  )}
                  {stat.trend === 'neutral' && (
                    <span className="text-gray-500 text-sm">{stat.change}</span>
                  )}
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-1">{stat.title}</h3>
                <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
              </div>
            );
          })}
        </div>

        {/* Recent Signals */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Recent Signals</h2>
            <Link 
              href="/signals"
              className="text-indigo-600 hover:text-indigo-700 text-sm font-medium flex items-center gap-1"
            >
              View all
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>

          <div className="space-y-4">
            {recentSignals.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No signals yet. Waiting for new signals...</p>
            ) : (
              recentSignals.map((signal, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="flex flex-col">
                      <span className="font-bold text-gray-900">{signal.symbol}</span>
                      <span className={`text-sm font-semibold ${signal.direction === 'long' ? 'text-green-600' : 'text-red-600'}`}>
                        {signal.direction === 'long' ? '📈 LONG' : '📉 SHORT'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-xs text-gray-500">Entry</div>
                      <div className="font-semibold text-gray-900">
                        {signal.entry_price ? `$${signal.entry_price.toFixed(4)}` : '—'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500">TP</div>
                      <div className="font-semibold text-green-600">
                        {signal.tp_price ? `$${signal.tp_price.toFixed(4)}` : '—'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500">SL</div>
                      <div className="font-semibold text-red-600">
                        {signal.sl_price ? `$${signal.sl_price.toFixed(4)}` : '—'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-500">Score</div>
                      <div className="font-semibold text-indigo-600">{(signal.score * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      {!signal.outcome || signal.outcome === 'open' ? (
                        <span className="px-3 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                          🔵 OPEN
                        </span>
                      ) : signal.outcome === 'tp_hit' ? (
                        <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                          ✓ TP HIT
                        </span>
                      ) : signal.outcome === 'sl_hit' ? (
                        <span className="px-3 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                          ✗ SL HIT
                        </span>
                      ) : (
                        <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full">
                          ⏱ {signal.outcome?.toUpperCase()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          <Link href="/signals" className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl p-6 text-white hover:shadow-lg transition-shadow">
            <TrendingUp className="w-8 h-8 mb-3" />
            <h3 className="text-xl font-bold mb-2">View Live Signals</h3>
            <p className="text-indigo-100">Monitor real-time trading signals and market opportunities</p>
          </Link>
          
          <Link href="/analytics" className="bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl p-6 text-white hover:shadow-lg transition-shadow">
            <Target className="w-8 h-8 mb-3" />
            <h3 className="text-xl font-bold mb-2">Performance Analytics</h3>
            <p className="text-purple-100">Deep dive into your trading performance metrics</p>
          </Link>
        </div>
    </div>
  );
}
