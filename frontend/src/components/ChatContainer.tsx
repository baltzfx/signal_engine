'use client';

import { useEffect, useRef, useState } from 'react';
import { useSignals } from '@/contexts/SignalContext';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import SignalTabs, { SignalFilterTab } from './SignalTabs';
import { TrendingUp } from 'lucide-react';
import type { Message } from '@/types';

export default function ChatContainer() {
  const { messages, getSignalCounts } = useSignals();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<SignalFilterTab>('all');

  // Filter messages based on active tab
  const filteredMessages = messages.filter((message) => {
    if (activeTab === 'all') return true;
    if (message.type !== 'signal' || !message.signal) return true;
    
    const outcome = message.signal.outcome;
    
    switch (activeTab) {
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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  useEffect(() => {
    scrollToBottom();
  }, [activeTab]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="p-4 lg:p-6 border-b border-gray-200 bg-white shadow-sm">
        <h1 className="text-xl lg:text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 lg:w-6 lg:h-6 text-indigo-600" />
          Live Trading Signals
        </h1>
        <p className="text-gray-600 text-xs lg:text-sm">Real-time AI-powered trading alerts</p>
      </div>

      {/* Tabs */}
      <SignalTabs 
        activeTab={activeTab} 
        onTabChange={setActiveTab}
        counts={getSignalCounts()}
      />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 lg:p-6 scrollbar-hide">
        <div className="container mx-auto max-w-4xl space-y-4">
          {filteredMessages.length === 0 ? (
            <div className="text-center py-12">
              <TrendingUp className="w-16 h-16 mx-auto mb-4 opacity-20 text-gray-400" />
              <p className="text-gray-500 text-lg">
                {activeTab === 'all' 
                  ? 'No signals available yet. Waiting for new signals...' 
                  : `No ${activeTab.replace('_', ' ')} signals available.`}
              </p>
            </div>
          ) : (
            filteredMessages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t bg-gray-50 p-4">
        <div className="container mx-auto max-w-4xl">
          <ChatInput />
        </div>
      </div>
    </div>
  );
}
