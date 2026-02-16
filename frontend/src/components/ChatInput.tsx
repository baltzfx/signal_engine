'use client';

import { useState } from 'react';
import { useSignals } from '@/contexts/SignalContext';
import { apiClient } from '@/lib/api';
import { Send, Loader2 } from 'lucide-react';

export default function ChatInput() {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { addUserMessage, addAssistantMessage } = useSignals();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput('');
    addUserMessage(message);
    setIsLoading(true);

    try {
      const response = await apiClient.query(message);
      addAssistantMessage(response.ai_response || 'No response from AI');
    } catch (error) {
      addAssistantMessage('Sorry, I encountered an error processing your request.');
      console.error('Query error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask me anything about the market..."
        disabled={isLoading}
        className="flex-1 px-4 py-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={isLoading || !input.trim()}
        className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-full hover:from-purple-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Thinking...
          </>
        ) : (
          <>
            <Send className="w-5 h-5" />
            Send
          </>
        )}
      </button>
    </form>
  );
}
