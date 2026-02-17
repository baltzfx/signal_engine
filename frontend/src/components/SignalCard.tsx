'use client';

import { useState, useEffect } from 'react';
import type { Signal } from '@/types';
import { TrendingUp, TrendingDown, Target, Shield, Clock } from 'lucide-react';

interface SignalCardProps {
  signal: Signal;
}

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

export default function SignalCard({ signal }: SignalCardProps) {
  const [mounted, setMounted] = useState(false);
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    setMounted(true);
    
    // Update time every 10 seconds for open signals
    if (!signal.outcome || signal.outcome === 'open') {
      const interval = setInterval(() => {
        setCurrentTime(Date.now());
      }, 10000);
      
      return () => clearInterval(interval);
    }
  }, [signal.outcome]);
  const isLong = signal.direction === 'long';
  const scorePercent = (signal.score * 100).toFixed(1);
  const mtfScorePercent = signal.mtf_score ? (signal.mtf_score * 100).toFixed(1) : null;
  
  // Calculate time open and expiry warning
  const timeOpenSecs = currentTime / 1000 - signal.timestamp;
  const maxTTL = 21600; // 6 hours
  const isNearExpiry = timeOpenSecs > (maxTTL * 0.75); // 75% of TTL (4.5 hours)

  return (
    <div className="flex justify-start animate-slide-in">
      <div className="max-w-2xl w-full bg-white rounded-2xl shadow-lg border-l-4 overflow-hidden"
           style={{ borderLeftColor: isLong ? '#2ecc71' : '#e74c3c' }}>
        {/* Header */}
        <div className={`p-4 ${isLong ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {isLong ? (
                <TrendingUp className="w-6 h-6 text-green-600" />
              ) : (
                <TrendingDown className="w-6 h-6 text-red-600" />
              )}
              <div>
                <h3 className="text-xl font-bold text-gray-800">{signal.symbol}</h3>
                <p className={`text-sm font-semibold ${isLong ? 'text-green-700' : 'text-red-700'}`}>
                  {signal.direction.toUpperCase()} SIGNAL
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-800">{scorePercent}%</div>
              <div className="text-xs text-gray-600">Confidence</div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-4 space-y-3">
          {/* Status & MTF Badges */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Signal Status */}
            {signal.outcome && signal.outcome !== 'open' && (
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                signal.outcome === 'tp_hit'
                  ? 'bg-green-600 text-white'
                  : signal.outcome === 'sl_hit'
                  ? 'bg-red-600 text-white'
                  : signal.outcome === 'expired'
                  ? 'bg-gray-500 text-white'
                  : 'bg-blue-500 text-white'
              }`}>
                {signal.outcome === 'tp_hit' && '✓ TP HIT'}
                {signal.outcome === 'sl_hit' && '✗ SL HIT'}
                {signal.outcome === 'expired' && '⏱ EXPIRED'}
                {signal.outcome === 'manual' && '⊗ MANUAL CLOSE'}
                {signal.outcome === 'reversed' && '↔ REVERSED'}
              </span>
            )}
            {(!signal.outcome || signal.outcome === 'open') && (
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">
                🔵 OPEN
              </span>
            )}
            {/* Return % */}
            {signal.return_pct !== undefined && signal.return_pct !== null && (
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                signal.return_pct > 0
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {signal.return_pct > 0 ? '+' : ''}{signal.return_pct.toFixed(2)}%
              </span>
            )}
            {/* MTF Badge */}
            {signal.mtf_aligned !== undefined && (
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                signal.mtf_aligned
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}>
                {signal.mtf_aligned ? '✓ MTF Aligned' : '⚠ MTF Mixed'}
              </span>
            )}
            {mtfScorePercent && (
              <span className="text-sm text-gray-600">
                MTF: {mtfScorePercent}%
              </span>
            )}
          </div>

          {/* Price Levels */}
          <div className="grid grid-cols-3 gap-3">
            {signal.entry_price && (
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-xs text-gray-600 mb-1">Entry</div>
                <div className="font-bold text-gray-800">${signal.entry_price.toFixed(2)}</div>
              </div>
            )}
            {signal.tp_price && (
              <div className="bg-green-50 rounded-lg p-3">
                <div className="text-xs text-green-700 mb-1 flex items-center gap-1">
                  <Target className="w-3 h-3" />
                  Take Profit
                </div>
                <div className="font-bold text-green-700">${signal.tp_price.toFixed(2)}</div>
              </div>
            )}
            {signal.sl_price && (
              <div className="bg-red-50 rounded-lg p-3">
                <div className="text-xs text-red-700 mb-1 flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  Stop Loss
                </div>
                <div className="font-bold text-red-700">${signal.sl_price.toFixed(2)}</div>
              </div>
            )}
          </div>

          {/* Real-time Price & P&L (for open signals) */}
          {(!signal.outcome || signal.outcome === 'open') && signal.current_price && (
            <div className="grid grid-cols-2 gap-3 mt-3">
              <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                <div className="text-xs text-blue-700 mb-1 font-semibold">Current Price</div>
                <div className="font-bold text-blue-800">${signal.current_price.toFixed(2)}</div>
              </div>
              {signal.current_pnl_pct !== undefined && (
                <div className={`rounded-lg p-3 border ${
                  signal.current_pnl_pct >= 0 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-red-50 border-red-200'
                }`}>
                  <div className={`text-xs mb-1 font-semibold ${
                    signal.current_pnl_pct >= 0 ? 'text-green-700' : 'text-red-700'
                  }`}>
                    Real-time P&L
                  </div>
                  <div className={`font-bold text-lg ${
                    signal.current_pnl_pct >= 0 ? 'text-green-800' : 'text-red-800'
                  }`}>
                    {signal.current_pnl_pct >= 0 ? '▲' : '▼'} {Math.abs(signal.current_pnl_pct).toFixed(2)}%
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Trigger Events */}
          {signal.trigger_events && signal.trigger_events.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="text-xs text-blue-700 font-semibold mb-2">📌 Trigger Events</div>
              <div className="flex flex-wrap gap-2">
                {signal.trigger_events.map((event, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                  >
                    {event.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Timestamp & Duration */}
          {mounted && (
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(signal.timestamp * 1000).toLocaleString()}
              </div>
              {(!signal.outcome || signal.outcome === 'open') && (
                <div className={`flex items-center gap-1 font-semibold ${
                  isNearExpiry ? 'text-orange-600 animate-pulse' : 'text-blue-600'
                }`}>
                  <span>⏱</span>
                  <span>{formatDuration(timeOpenSecs)} open</span>
                  {isNearExpiry ? (
                    <span className="text-orange-500 text-[10px]">(expiring soon!)</span>
                  ) : (
                    <span className="text-gray-400 text-[10px]">(expires in 6h)</span>
                  )}
                </div>
              )}
              {signal.duration_sec && (
                <div className="flex items-center gap-1">
                  <span>Duration: {formatDuration(signal.duration_sec)}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
