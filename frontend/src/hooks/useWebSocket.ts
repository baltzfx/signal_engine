import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketMessage } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/feed';

export function useWebSocket(onMessage: (message: WebSocketMessage) => void) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    try {
      // Only log WebSocket connection attempts in development
      if (process.env.NODE_ENV === 'development') {
        console.log('Attempting WebSocket connection to:', WS_URL);
      }
      
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('WebSocket connected');
        }
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          onMessage(message);
        } catch (error) {
          // Silent fail for parse errors in production
          if (process.env.NODE_ENV === 'development') {
            console.error('Failed to parse WebSocket message:', error);
          }
        }
      };

      ws.onerror = (error) => {
        // Only log errors in development to avoid console spam
        if (process.env.NODE_ENV === 'development') {
          console.warn('WebSocket connection error - backend may not be running');
        }
        setIsConnected(false);
      };

      ws.onclose = () => {
        if (process.env.NODE_ENV === 'development') {
          console.log('WebSocket closed - will retry in 5 seconds');
        }
        setIsConnected(false);
        
        // Reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (process.env.NODE_ENV === 'development') {
            console.log('Reconnecting WebSocket...');
          }
          connect();
        }, 5000);
      };

      wsRef.current = ws;
    } catch (error) {
      // Silent fail in production
      if (process.env.NODE_ENV === 'development') {
        console.warn('Failed to create WebSocket - backend may not be running');
      }
      setIsConnected(false);
    }
  }, [onMessage]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected, sendMessage };
}
