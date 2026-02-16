'use client';

import { useState } from 'react';

export type SignalFilterTab = 'all' | 'open' | 'closed' | 'tp_hit' | 'sl_hit' | 'expired';

interface SignalTabsProps {
  activeTab: SignalFilterTab;
  onTabChange: (tab: SignalFilterTab) => void;
  counts?: {
    all: number;
    open: number;
    closed: number;
    tp_hit: number;
    sl_hit: number;
    expired: number;
  };
}

export default function SignalTabs({ activeTab, onTabChange, counts }: SignalTabsProps) {
  const tabs: { id: SignalFilterTab; label: string; emoji: string }[] = [
    { id: 'all', label: 'All Signals', emoji: '📊' },
    { id: 'open', label: 'Open', emoji: '🔵' },
    { id: 'tp_hit', label: 'TP Hit', emoji: '✅' },
    { id: 'sl_hit', label: 'SL Hit', emoji: '❌' },
    { id: 'expired', label: 'Expired', emoji: '⏱️' },
    { id: 'closed', label: 'All Closed', emoji: '🔒' },
  ];

  return (
    <div className="bg-white border-b border-gray-200 shadow-sm">
      <div className="container mx-auto max-w-4xl px-4">
        <div className="flex gap-1 overflow-x-auto scrollbar-hide py-2">
          {tabs.map((tab) => {
            const count = counts?.[tab.id] ?? 0;
            const isActive = activeTab === tab.id;
            
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm
                  whitespace-nowrap transition-all duration-200
                  ${isActive
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }
                `}
              >
                <span>{tab.emoji}</span>
                <span>{tab.label}</span>
                {counts && (
                  <span className={`
                    ml-1 px-2 py-0.5 rounded-full text-xs font-bold
                    ${isActive ? 'bg-indigo-700' : 'bg-gray-300 text-gray-700'}
                  `}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
