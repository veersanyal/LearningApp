import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Trophy, Medal, Award, TrendingUp } from 'lucide-react';

const leaderboardData = [
  { rank: 1, name: 'Sarah Chen', avatar: 'SC', xp: 2847, course: 'MA 162', streak: 14 },
  { rank: 2, name: 'Michael Torres', avatar: 'MT', xp: 2653, course: 'MA 161', streak: 12 },
  { rank: 3, name: 'Emily Watson', avatar: 'EW', xp: 2489, course: 'MA 162', streak: 10 },
  { rank: 4, name: 'Jamie Smith', avatar: 'JS', xp: 2341, course: 'MA 161', streak: 7, isYou: true },
  { rank: 5, name: 'Alex Johnson', avatar: 'AJ', xp: 2198, course: 'MA 165', streak: 9 },
  { rank: 6, name: 'Taylor Brown', avatar: 'TB', xp: 2045, course: 'MA 162', streak: 6 },
  { rank: 7, name: 'Morgan Lee', avatar: 'ML', xp: 1932, course: 'MA 161', streak: 5 },
  { rank: 8, name: 'Jordan Kim', avatar: 'JK', xp: 1876, course: 'MA 166', streak: 8 },
  { rank: 9, name: 'Casey Davis', avatar: 'CD', xp: 1754, course: 'MA 165', streak: 4 },
  { rank: 10, name: 'Riley Martinez', avatar: 'RM', xp: 1623, course: 'MA 162', streak: 7 },
];

export function LeaderboardPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<'all' | 'weekly' | 'alltime'>('weekly');
  const [courseFilter, setcourseFilter] = useState<string>('all');

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Trophy className="w-6 h-6 text-amber-500" />;
    if (rank === 2) return <Medal className="w-6 h-6 text-gray-400" />;
    if (rank === 3) return <Award className="w-6 h-6 text-amber-700" />;
    return null;
  };

  return (
    <div className="min-h-screen bg-background pb-20 lg:pb-0">
      {/* Header */}
      <header className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 hover:bg-muted rounded-xl transition-colors lg:hidden"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div className="flex-1">
            <h2>Leaderboard</h2>
            <p className="text-sm text-muted-foreground">Compete with Purdue students</p>
          </div>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-3">
          <div className="flex gap-2 bg-muted p-1 rounded-2xl">
            <button
              onClick={() => setFilter('weekly')}
              className={`px-4 py-2 rounded-xl text-sm transition-all ${
                filter === 'weekly'
                  ? 'bg-card shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              This Week
            </button>
            <button
              onClick={() => setFilter('alltime')}
              className={`px-4 py-2 rounded-xl text-sm transition-all ${
                filter === 'alltime'
                  ? 'bg-card shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              All Time
            </button>
          </div>

          <select
            value={courseFilter}
            onChange={(e) => setcourseFilter(e.target.value)}
            className="px-4 py-2 rounded-2xl border-2 border-border bg-card focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
          >
            <option value="all">All Courses</option>
            <option value="MA 161">MA 161</option>
            <option value="MA 162">MA 162</option>
            <option value="MA 165">MA 165</option>
            <option value="MA 166">MA 166</option>
          </select>
        </div>

        {/* Top 3 podium */}
        <div className="mb-8 grid grid-cols-3 gap-4 items-end">
          {/* 2nd place */}
          <div className="text-center">
            <div className="bg-gradient-to-br from-gray-100 to-gray-200 rounded-3xl p-6 shadow-lg border-2 border-gray-300 mb-3">
              <div className="w-20 h-20 mx-auto rounded-full bg-gray-400 flex items-center justify-center text-white text-xl mb-3">
                {leaderboardData[1].avatar}
              </div>
              <Medal className="w-8 h-8 text-gray-500 mx-auto mb-2" />
              <p className="text-sm mb-1">{leaderboardData[1].name}</p>
              <p className="text-2xl text-gray-700">{leaderboardData[1].xp}</p>
              <p className="text-xs text-muted-foreground">XP</p>
            </div>
          </div>

          {/* 1st place */}
          <div className="text-center">
            <div className="bg-gradient-to-br from-amber-100 to-amber-200 rounded-3xl p-6 shadow-xl border-2 border-amber-400 mb-3 transform scale-105">
              <div className="w-24 h-24 mx-auto rounded-full bg-amber-500 flex items-center justify-center text-white text-2xl mb-3">
                {leaderboardData[0].avatar}
              </div>
              <Trophy className="w-10 h-10 text-amber-600 mx-auto mb-2" />
              <p className="text-sm mb-1">{leaderboardData[0].name}</p>
              <p className="text-3xl text-amber-700">{leaderboardData[0].xp}</p>
              <p className="text-xs text-muted-foreground">XP</p>
            </div>
          </div>

          {/* 3rd place */}
          <div className="text-center">
            <div className="bg-gradient-to-br from-amber-50 to-amber-100 rounded-3xl p-6 shadow-lg border-2 border-amber-300 mb-3">
              <div className="w-20 h-20 mx-auto rounded-full bg-amber-700 flex items-center justify-center text-white text-xl mb-3">
                {leaderboardData[2].avatar}
              </div>
              <Award className="w-8 h-8 text-amber-800 mx-auto mb-2" />
              <p className="text-sm mb-1">{leaderboardData[2].name}</p>
              <p className="text-2xl text-amber-900">{leaderboardData[2].xp}</p>
              <p className="text-xs text-muted-foreground">XP</p>
            </div>
          </div>
        </div>

        {/* Full leaderboard */}
        <div className="bg-card rounded-3xl shadow-lg border border-border overflow-hidden">
          <div className="p-6">
            <h3 className="mb-4">Full Rankings</h3>
          </div>

          <div className="divide-y divide-border">
            {leaderboardData.map((user) => (
              <div
                key={user.rank}
                className={`px-6 py-4 flex items-center gap-4 transition-colors ${
                  user.isYou ? 'bg-accent/10 border-l-4 border-accent' : 'hover:bg-muted/50'
                }`}
              >
                <div className="w-12 flex items-center justify-center">
                  {getRankIcon(user.rank) || (
                    <span className="text-lg text-muted-foreground">#{user.rank}</span>
                  )}
                </div>

                <div className="w-12 h-12 rounded-full bg-accent flex items-center justify-center text-accent-foreground">
                  {user.avatar}
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p>{user.name}</p>
                    {user.isYou && (
                      <span className="text-xs bg-accent/20 text-accent px-2 py-0.5 rounded-full">
                        You
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">{user.course}</p>
                </div>

                <div className="text-right">
                  <div className="flex items-center gap-2 justify-end mb-1">
                    <TrendingUp className="w-4 h-4 text-green-600" />
                    <p className="text-lg">{user.xp}</p>
                  </div>
                  <p className="text-xs text-muted-foreground">{user.streak} day streak</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Your stats */}
        <div className="mt-6 bg-gradient-to-br from-accent/20 to-accent/10 rounded-3xl p-6 border border-accent/30">
          <h4 className="mb-3">Your Progress</h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-2xl text-accent">2,341</p>
              <p className="text-sm text-muted-foreground">Total XP</p>
            </div>
            <div>
              <p className="text-2xl text-accent">+124</p>
              <p className="text-sm text-muted-foreground">This week</p>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-sm mb-2">
              <span>Next rank in 107 XP</span>
              <span className="text-accent">82%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-4/5 bg-accent rounded-full"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
