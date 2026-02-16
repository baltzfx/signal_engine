import type { Metadata } from "next";
import "./globals.css";
import Navigation from "@/components/Navigation";
import { SignalProvider } from "@/contexts/SignalContext";

export const metadata: Metadata = {
  title: "SignalEngine - AI Trading Signals",
  description: "Professional AI-powered trading signal platform",
  icons: {
    icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><text y=".9em" font-size="90">🚀</text></svg>',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        <SignalProvider>
          <div className="min-h-screen bg-gray-50">
            <Navigation />
            <main className="lg:ml-64 pt-16 lg:pt-0 min-h-screen">
              {children}
            </main>
          </div>
        </SignalProvider>
      </body>
    </html>
  );
}
