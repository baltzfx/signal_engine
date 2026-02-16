'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  TrendingUp, 
  BarChart3, 
  MessageSquare,
  Menu,
  X,
  Zap,
  Settings,
  Bell,
  User
} from 'lucide-react';

export default function Navigation() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const navItems = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/signals', icon: TrendingUp, label: 'Live Signals' },
    { href: '/analytics', icon: BarChart3, label: 'Analytics' },
    { href: '/chat', icon: MessageSquare, label: 'AI Chat' },
  ];

  const isActive = (path: string) => pathname === path;

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex lg:flex-col lg:w-64 bg-gradient-to-b from-indigo-900 via-purple-900 to-purple-800 text-white fixed h-screen">
        {/* Logo */}
        <div className="p-6 border-b border-indigo-700">
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="p-2 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-lg group-hover:scale-110 transition-transform">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">SignalEngine</h1>
              <p className="text-xs text-indigo-300">Beta Phase</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                  ${active 
                    ? 'bg-white text-indigo-900 shadow-lg' 
                    : 'text-indigo-100 hover:bg-indigo-800/50'
                  }
                `}
              >
                <Icon className={`w-5 h-5 ${active ? 'text-indigo-600' : ''}`} />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* User Profile */}
        {/* <div className="p-4 border-t border-indigo-700">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-indigo-800/50 hover:bg-indigo-800 cursor-pointer transition-colors">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-pink-400 flex items-center justify-center">
              <User className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold">Pro User</p>
              <p className="text-xs text-indigo-300">Active subscription</p>
            </div>
            <Settings className="w-4 h-4 text-indigo-300" />
          </div>
        </div> */}
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 bg-gradient-to-r from-indigo-900 to-purple-900 text-white z-50 shadow-lg">
        <div className="flex items-center justify-between p-4">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="p-1.5 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-lg">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold">SignalEngine</span>
          </Link>
          
          <div className="flex items-center gap-3">
            <button className="p-2 hover:bg-indigo-800 rounded-lg transition-colors">
              <Bell className="w-5 h-5" />
            </button>
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 hover:bg-indigo-800 rounded-lg transition-colors"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/50 z-40 backdrop-blur-sm" onClick={() => setIsMobileMenuOpen(false)}>
          <div 
            className="fixed right-0 top-16 bottom-0 w-64 bg-gradient-to-b from-indigo-900 via-purple-900 to-purple-800 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <nav className="p-4 space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                      ${active 
                        ? 'bg-white text-indigo-900 shadow-lg' 
                        : 'text-indigo-100 hover:bg-indigo-800/50'
                      }
                    `}
                  >
                    <Icon className={`w-5 h-5 ${active ? 'text-indigo-600' : ''}`} />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
