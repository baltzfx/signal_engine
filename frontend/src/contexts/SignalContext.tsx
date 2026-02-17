'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { Signal, Message, SystemMetrics } from '@/types';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ApiClient } from '@/lib/api';

interface SignalContextType {
  messages: Message[];
  signals: Signal[];
  systemMetrics: SystemMetrics | null;
  isConnected: boolean;
  addUserMessage: (content: string) => void;
  addAssistantMessage: (content: string) => void;
  getSignalCounts: () => {
    all: number;
    open: number;
    closed: number;
    tp_hit: number;
    sl_hit: number;
    expired: number;
  };
}

const SignalContext = createContext<SignalContextType | undefined>(undefined);

export function SignalProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'system',
      content: '🚀 Connected to SignalEngine v3. Waiting for signals...',
      timestamp: 0, // Fixed timestamp to avoid hydration mismatch
    },
  ]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);

  // Load initial signals from API
  useEffect(() => {
    let isFirstLoad = true; // Use local variable instead of state
    
    const loadSignals = async () => {
      try {
        const api = new ApiClient();
        console.log('Fetching signals from API...');
        const response = await api.getSignals(50);
        console.log('API response:', response);
        
        if (response.signals && response.signals.length > 0) {
          console.log(`Loaded ${response.signals.length} signals`);
          setSignals(response.signals);
          
          // Add initial signals as messages (only on first load)
          if (isFirstLoad) {
            const signalMessages: Message[] = response.signals.map((signal: Signal) => ({
              id: `signal-${signal.symbol}-${signal.timestamp}`,
              type: 'signal' as const,
              content: formatSignalMessage(signal),
              signal,
              timestamp: signal.timestamp * 1000,
            }));
            
            setMessages(prev => [...prev, ...signalMessages]);
            isFirstLoad = false; // Update local flag
            console.log('Initial signals added to messages');
          } else {
            // On refresh, update existing signal messages with new price data
            setMessages(prev => prev.map(msg => {
              if (msg.type === 'signal' && msg.signal) {
                const updatedSignal = response.signals.find(
                  (s: Signal) => s.symbol === msg.signal!.symbol && s.timestamp === msg.signal!.timestamp
                );
                if (updatedSignal) {
                  return {
                    ...msg,
                    signal: updatedSignal,
                    content: formatSignalMessage(updatedSignal),
                  };
                }
              }
              return msg;
            }));
            console.log('Signals refreshed with new price data');
          }
        } else {
          console.log('No signals returned from API');
        }
      } catch (error) {
        console.error('Failed to load signals:', error);
        if (isFirstLoad) {
          const errorMsg: Message = {
            id: `error-${Date.now()}`,
            type: 'system',
            content: '⚠️ Failed to load signals from API. Check if backend is running on http://localhost:8000',
            timestamp: Date.now(),
          };
          setMessages(prev => [...prev, errorMsg]);
        }
      }
    };

    loadSignals();
    
    // Refresh signals every 10 seconds to update current prices and P&L
    const refreshInterval = setInterval(() => {
      loadSignals();
    }, 10000); // 10 seconds
    
    return () => clearInterval(refreshInterval);
  }, []); // Empty dependency array - only run once on mount

  const handleWebSocketMessage = useCallback((wsMessage: any) => {
    switch (wsMessage.type) {
      case 'signal':
        const signal: Signal = wsMessage.data;
        setSignals((prev) => [signal, ...prev].slice(0, 100));
        
        // Add signal as a message
        const signalMessage: Message = {
          id: `signal-${Date.now()}`,
          type: 'signal',
          content: formatSignalMessage(signal),
          signal,
          timestamp: signal.timestamp * 1000,
        };
        setMessages((prev) => [...prev, signalMessage]);
        break;

      case 'status':
        if (wsMessage.data?.metrics) {
          setSystemMetrics(wsMessage.data.metrics);
        }
        break;

      case 'connected':
        const welcomeMsg: Message = {
          id: `connected-${Date.now()}`,
          type: 'system',
          content: `✅ ${wsMessage.data.message}`,
          timestamp: Date.now(),
        };
        setMessages((prev) => [...prev, welcomeMsg]);
        break;
    }
  }, []);

  const { isConnected } = useWebSocket(handleWebSocketMessage);

  const addUserMessage = useCallback((content: string) => {
    const message: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, message]);
  }, []);

  const addAssistantMessage = useCallback((content: string) => {
    const message: Message = {
      id: `assistant-${Date.now()}`,
      type: 'assistant',
      content,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, message]);
  }, []);

  const getSignalCounts = useCallback(() => {
    const all = signals.length;
    const open = signals.filter(s => !s.outcome || s.outcome === 'open').length;
    const tp_hit = signals.filter(s => s.outcome === 'tp_hit').length;
    const sl_hit = signals.filter(s => s.outcome === 'sl_hit').length;
    const expired = signals.filter(s => s.outcome === 'expired').length;
    const closed = signals.filter(s => s.outcome && s.outcome !== 'open').length;
    
    return { all, open, closed, tp_hit, sl_hit, expired };
  }, [signals]);

  return (
    <SignalContext.Provider
      value={{
        messages,
        signals,
        systemMetrics,
        isConnected,
        addUserMessage,
        addAssistantMessage,
        getSignalCounts,
      }}
    >
      {children}
    </SignalContext.Provider>
  );
}

export function useSignals() {
  const context = useContext(SignalContext);
  if (context === undefined) {
    throw new Error('useSignals must be used within a SignalProvider');
  }
  return context;
}

function formatSignalMessage(signal: Signal): string {
  const direction = signal.direction.toUpperCase();
  const emoji = signal.direction === 'long' ? '🟢' : '🔴';
  const scorePercent = (signal.score * 100).toFixed(1);
  const mtfBadge = signal.mtf_aligned ? ' | MTF ✓' : '';
  
  return `${emoji} **${direction} ${signal.symbol}**\nScore: ${scorePercent}%${mtfBadge}\nEntry: $${signal.entry_price?.toFixed(2) || 'N/A'}${
    signal.tp_price ? `\nTP: $${signal.tp_price.toFixed(2)}` : ''
  }${signal.sl_price ? ` | SL: $${signal.sl_price.toFixed(2)}` : ''}`;
}
