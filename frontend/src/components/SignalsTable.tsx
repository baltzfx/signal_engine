'use client';

import { useEffect, useState } from 'react';
import { useSignals } from '@/contexts/SignalContext';
import SignalTabs, { SignalFilterTab } from './SignalTabs';
import { TrendingUp, ArrowUpCircle, ArrowDownCircle, Target, Shield, Clock, Percent } from 'lucide-react';
import type { Message } from '@/types';

export default function SignalsTable() {
  const { messages, getSignalCounts } = useSignals();
  const [activeTab, setActiveTab] = useState<SignalFilterTab>('all');

  // Extract signals from messages and sort newest to oldest
  const signals = messages
    .filter(m => m.type === 'signal' && m.signal)
    .map(m => m.signal!)
    .sort((a, b) => b.timestamp - a.timestamp);

  // Filter signals based on active tab
  const filteredSignals = signals.filter((signal) => {
    const outcome = signal.outcome;
    
    switch (activeTab) {
      case 'all':
        return true;
      case 'open':
        return !outcome || outcome === 'open';
      case 'closed':
        return outcome && outcome !== 'open';
      case 'tp_hit':
        return outcome === 'tp_hit';
      case 'sl_hit':
        return outcome === 'sl_hit';
      case 'expired':
        return outcome === 'expired';
      default:
        return true;
    }
  });

  const formatPrice = (price?: number) => {
    if (!price) return '—';
    return `$${price.toFixed(4)}`;
  };

  const formatPercent = (value?: number) => {
    if (!value) return '—';
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getOutcomeColor = (outcome?: string) => {
    switch (outcome) {
      case 'tp_hit':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'sl_hit':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'expired':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  const getOutcomeText = (outcome?: string) => {
    switch (outcome) {
      case 'tp_hit':
        return '✅ TP Hit';
      case 'sl_hit':
        return '❌ SL Hit';
      case 'expired':
        return '⏱️ Expired';
      default:
        return '🔵 Open';
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-4 lg:p-6 border-b border-gray-200 bg-white shadow-sm">
        <h1 className="text-xl lg:text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 lg:w-6 lg:h-6 text-indigo-600" />
          Live Trading Signals
        </h1>
        <p className="text-gray-600 text-xs lg:text-sm">
          Real-time signals sorted by newest first • Auto-synced with Telegram
        </p>
      </div>

      {/* Tabs */}
      <SignalTabs 
        activeTab={activeTab} 
        onTabChange={setActiveTab}
        counts={getSignalCounts()}
      />

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {filteredSignals.length === 0 ? (
          <div className="text-center py-12">
            <TrendingUp className="w-16 h-16 mx-auto mb-4 opacity-20 text-gray-400" />
            <p className="text-gray-500 text-lg">
              {activeTab === 'all' 
                ? 'No signals available yet. Waiting for new signals...' 
                : `No ${activeTab.replace('_', ' ')} signals available.`}
            </p>
            <p className="text-gray-400 text-sm mt-2">
              Signals with score ≥ 50% are automatically sent to Telegram
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Time
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Direction
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Entry
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Take Profit
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Stop Loss
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredSignals.map((signal, index) => {
                  const isLong = signal.direction === 'long';
                  const DirectionIcon = isLong ? ArrowUpCircle : ArrowDownCircle;
                  const directionColor = isLong ? 'text-green-600' : 'text-red-600';
                  const directionBg = isLong ? 'bg-green-50' : 'bg-red-50';

                  return (
                    <tr 
                      key={`${signal.symbol}-${signal.timestamp}-${index}`}
                      className="hover:bg-gray-50 transition-colors"
                    >
                      <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(signal.timestamp)}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="font-semibold text-gray-900">{signal.symbol}</div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className={`flex items-center gap-1 ${directionColor}`}>
                          <DirectionIcon className="w-4 h-4" />
                          <span className="font-medium uppercase">{signal.direction}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          <Percent className="w-3 h-3 text-gray-400" />
                          <span className={`font-semibold ${
                            signal.score >= 0.7 ? 'text-green-600' : 
                            signal.score >= 0.5 ? 'text-yellow-600' : 
                            'text-gray-600'
                          }`}>
                            {formatPercent(signal.score)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-mono">
                        {formatPrice(signal.entry_price)}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-green-600">
                        <div className="flex items-center gap-1">
                          <Target className="w-3 h-3" />
                          {formatPrice(signal.tp_price)}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-sm font-mono text-red-600">
                        <div className="flex items-center gap-1">
                          <Shield className="w-3 h-3" />
                          {formatPrice(signal.sl_price)}
                        </div>
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getOutcomeColor(signal.outcome)}`}>
                          {getOutcomeText(signal.outcome)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="border-t bg-white px-4 py-3">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <div>
            Showing <span className="font-semibold text-gray-900">{filteredSignals.length}</span> signals
          </div>
          <div className="text-xs">
            🤖 Signals automatically sent to Telegram when score ≥ 50%
          </div>
        </div>
      </div>
    </div>
  );
}
