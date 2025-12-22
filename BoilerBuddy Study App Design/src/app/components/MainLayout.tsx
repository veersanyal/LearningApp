import { Outlet, Link, useLocation } from 'react-router-dom';
import { Home, BookOpen, Users, Trophy, Map, Upload, LogOut, User } from 'lucide-react';
import { useState } from 'react';

interface MainLayoutProps {
  onLogout: () => void;
}

export function MainLayout({ onLogout }: MainLayoutProps) {
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const navItems = [
    { path: '/dashboard', icon: Home, label: 'Dashboard' },
    { path: '/study', icon: BookOpen, label: 'Study' },
    { path: '/group-study', icon: Users, label: 'Group' },
    { path: '/leaderboard', icon: Trophy, label: 'Leaderboard' },
    { path: '/heatmap', icon: Map, label: 'Heatmap' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-white">
      {/* Desktop Top Navbar */}
      <nav className="hidden md:block fixed top-0 left-0 right-0 bg-black text-white z-50 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <h1 className="text-xl" style={{ color: '#CFB991' }}>
              <span className="font-bold">Boiler</span>Buddy
            </h1>
            <div className="flex gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-4 py-2 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? 'bg-white/10 text-white'
                      : 'text-gray-300 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {item.label}
                </Link>
              ))}
              <Link
                to="/upload"
                className={`px-4 py-2 rounded-lg transition-colors ${
                  isActive('/upload')
                    ? 'bg-white/10 text-white'
                    : 'text-gray-300 hover:text-white hover:bg-white/5'
                }`}
              >
                Upload
              </Link>
            </div>
          </div>
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-blue-400 flex items-center justify-center hover:opacity-80 transition-opacity"
            >
              <User className="w-5 h-5 text-white" />
            </button>
            {showUserMenu && (
              <div className="absolute right-0 top-12 bg-white text-black rounded-lg shadow-xl p-2 min-w-[160px]">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    onLogout();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile Bottom Navbar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-black text-white z-50 shadow-lg">
        <div className="flex justify-around items-center h-16">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center justify-center gap-1 px-3 py-2 ${
                  isActive(item.path) ? 'text-yellow-400' : 'text-gray-300'
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main Content */}
      <div className="md:pt-16 pb-16 md:pb-0">
        <Outlet />
      </div>
    </div>
  );
}
