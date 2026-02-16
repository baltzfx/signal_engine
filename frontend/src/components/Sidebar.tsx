'use client';

import { useSignals } from '@/contexts/SignalContext';
import { Activity, TrendingUp, TrendingDown, Menu, X } from 'lucide-react';
import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import type { PerformanceStats } from '@/types';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({ isOpen, onToggle }: SidebarProps) {
  const { signals, systemMetrics, isConnected } = useSignals();
  const [perfStats, setPerfStats] = useState<PerformanceStats | null>(null);

  useEffect(() => {
    // Load performance stats
    apiClient.getPerformanceStats(7).then(setPerfStats).catch(console.error);
  }, []);

  const longSignals = signals.filter((s) => s.direction === 'long').length;
  const shortSignals = signals.filter((s) => s.direction === 'short').length;

  const overallStats = perfStats?.stats.reduce(
    (acc, stat) => ({
      totalSignals: acc.totalSignals + stat.total_signals,
      wins: acc.wins + stat.wins,
      losses: acc.losses + stat.losses,
    }),
    { totalSignals: 0, wins: 0, losses: 0 }
  );

  const winRate = overallStats
    ? ((overallStats.wins / overallStats.totalSignals) * 100).toFixed(1)
    : '0.0';

  return (
    <>
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="fixed top-4 left-4 z-50 p-2 bg-white rounded-lg shadow-lg hover:bg-gray-50"
      >
        {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen w-80 bg-white shadow-2xl transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } overflow-y-auto z-40`}
      >
        <div className="p-6 space-y-6">
          {/* Header */}
          <div className="pt-12">
            <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              SignalEngine v3
            </h2>
            <p className="text-sm text-gray-600 mt-1">AI-Powered Analysis</p>
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-2 text-sm">
            <div
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500 animate-pulse-slow' : 'bg-red-500'
              }`}
            />
            <span className={isConnected ? 'text-green-700' : 'text-red-700'}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Stats Cards */}
          <div className="space-y-3">
            <StatCard
              icon={<Activity className="w-5 h-5 text-purple-600" />}
              label="Total Signals"
              value={signals.length.toString()}
            />
            <StatCard
              icon={<TrendingUp className="w-5 h-5 text-green-600" />}
              label="Long Signals"
              value={longSignals.toString()}
              color="green"
            />
            <StatCard
              icon={<TrendingDown className="w-5 h-5 text-red-600" />}
              label="Short Signals"
              value={shortSignals.toString()}
              color="red"
            />
            <StatCard
              label="Win Rate (7d)"
              value={`${winRate}%`}
              color="blue"
            />
          </div>

          {/* System Metrics */}
          {systemMetrics && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">System</h3>
              <div className="space-y-2 text-sm">
                {systemMetrics.cpu_percent !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">CPU:</span>
                    <span className="font-medium">{systemMetrics.cpu_percent.toFixed(1)}%</span>
                  </div>
                )}
                {systemMetrics.memory_percent !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Memory:</span>
                    <span className="font-medium">{systemMetrics.memory_percent.toFixed(1)}%</span>
                  </div>
                )}
                {systemMetrics.uptime_seconds !== undefined && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Uptime:</span>
                    <span className="font-medium">
                      {Math.floor(systemMetrics.uptime_seconds / 60)}m
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-gray-700">Quick Questions</h3>
            <QuickButton text="What's the market trend?" />
            <QuickButton text="Show me top performing symbols" />
            <QuickButton text="Any strong signals right now?" />
          </div>
        </div>
      </aside>
    </>
  );
}

function StatCard({
  icon,
  label,
  value,
  color = 'gray',
}: {
  icon?: React.ReactNode;
  label: string;
  value: string;
  color?: string;
}) {
  const bgColors = {
    gray: 'bg-gray-50',
    green: 'bg-green-50',
    red: 'bg-red-50',
    blue: 'bg-blue-50',
  };

  return (
    <div className={`${bgColors[color as keyof typeof bgColors]} rounded-lg p-4`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm text-gray-600">{label}</span>
        </div>
        <span className="text-xl font-bold text-gray-800">{value}</span>
      </div>
    </div>
  );
}

function QuickButton({ text }: { text: string }) {
  const { addUserMessage, addAssistantMessage } = useSignals();

  const handleClick = async () => {
    addUserMessage(text);
    try {
      const response = await apiClient.query(text);
      addAssistantMessage(response.ai_response || 'No response from AI');
    } catch (error) {
      addAssistantMessage('Error processing request');
    }
  };

  return (
    <button
      onClick={handleClick}
      className="w-full text-left px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-colors"
    >
      {text}
    </button>
  );
}
