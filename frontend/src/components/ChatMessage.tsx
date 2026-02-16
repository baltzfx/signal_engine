'use client';

import { useState, useEffect } from 'react';
import type { Message } from '@/types';
import SignalCard from './SignalCard';
import { Bot, User, Info } from 'lucide-react';

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);
  if (message.type === 'signal' && message.signal) {
    return <SignalCard signal={message.signal} />;
  }

  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-slide-in`}>
      <div
        className={`flex gap-3 max-w-2xl ${
          isUser ? 'flex-row-reverse' : 'flex-row'
        }`}
      >
        {/* Avatar */}
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
            isUser
              ? 'bg-purple-600'
              : isSystem
              ? 'bg-gray-400'
              : 'bg-gradient-to-br from-purple-600 to-indigo-600'
          }`}
        >
          {isUser ? (
            <User className="w-6 h-6 text-white" />
          ) : isSystem ? (
            <Info className="w-6 h-6 text-white" />
          ) : (
            <Bot className="w-6 h-6 text-white" />
          )}
        </div>

        {/* Message Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-purple-600 text-white rounded-tr-none'
              : isSystem
              ? 'bg-gray-100 text-gray-700 rounded-tl-none'
              : 'bg-gradient-to-br from-gray-100 to-gray-200 text-gray-800 rounded-tl-none'
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {formatContent(message.content)}
          </div>
          {mounted && (
            <div
              className={`text-xs mt-2 ${
                isUser ? 'text-purple-200' : 'text-gray-500'
              }`}
            >
              {new Date(message.timestamp).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatContent(content: string) {
  // Simple markdown-like formatting
  const parts = content.split('**');
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="font-bold">
        {part}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}
