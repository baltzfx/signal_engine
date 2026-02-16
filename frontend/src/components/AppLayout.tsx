'use client';

import Navigation from '@/components/Navigation';
import { SignalProvider } from '@/contexts/SignalContext';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SignalProvider>
      <div className="min-h-screen bg-gray-50">
        <Navigation />
        
        {/* Main Content */}
        <main className="lg:ml-64 pt-16 lg:pt-0 min-h-screen">
          {children}
        </main>
      </div>
    </SignalProvider>
  );
}
