import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Flame, Target, Trophy, Users, BookOpen, Clock, TrendingUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const retentionData = [
  { day: 'Mon', retention: 45 },
  { day: 'Tue', retention: 62 },
  { day: 'Wed', retention: 71 },
  { day: 'Thu', retention: 78 },
  { day: 'Fri', retention: 85 },
  { day: 'Sat', retention: 88 },
  { day: 'Sun', retention: 92 },
];

const topicMap = [
  { name: 'Limits', learned: true, confidence: 95 },
  { name: 'Derivatives', learned: true, confidence: 88 },
  { name: 'Integrals', learned: false, confidence: 45 },
  { name: 'Series', learned: false, confidence: 30 },
  { name: 'Vector Calc', learned: false, confidence: 20 },
  { name: 'Diff Eq', learned: false, confidence: 15 },
];

export function DashboardPage() {
  const navigate = useNavigate();
  const [currentQuestion] = useState({
    title: 'Find the derivative of f(x) = 3x² + 2x - 5',
    topic: 'Derivatives',
    difficulty: 'Medium',
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-black rounded-2xl flex items-center justify-center">
              <BookOpen className="w-6 h-6 text-secondary" />
            </div>
            <h1 className="text-2xl">BoilerBuddy</h1>
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-muted rounded-xl transition-colors">
              <Users className="w-5 h-5" />
            </button>
            <div className="w-10 h-10 bg-accent rounded-full flex items-center justify-center">
              <span className="text-accent-foreground">JS</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Welcome section */}
        <div className="mb-8">
          <h2 className="mb-2">Welcome back, Jamie! 👋</h2>
          <p className="text-muted-foreground">You're crushing it! Keep up the momentum.</p>
        </div>

        {/* Quick stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-gradient-to-br from-orange-50 to-orange-100/50 rounded-2xl p-6 border border-orange-200">
            <div className="flex items-center gap-3 mb-2">
              <Flame className="w-6 h-6 text-orange-600" />
              <span className="text-sm text-orange-900">Study Streak</span>
            </div>
            <p className="text-3xl text-orange-900">7 days</p>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-purple-100/50 rounded-2xl p-6 border border-purple-200">
            <div className="flex items-center gap-3 mb-2">
              <Target className="w-6 h-6 text-purple-600" />
              <span className="text-sm text-purple-900">Accuracy</span>
            </div>
            <p className="text-3xl text-purple-900">87%</p>
          </div>

          <div className="bg-gradient-to-br from-amber-50 to-amber-100/50 rounded-2xl p-6 border border-amber-200">
            <div className="flex items-center gap-3 mb-2">
              <Trophy className="w-6 h-6 text-amber-600" />
              <span className="text-sm text-amber-900">Topics Mastered</span>
            </div>
            <p className="text-3xl text-amber-900">2/6</p>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-blue-100/50 rounded-2xl p-6 border border-blue-200">
            <div className="flex items-center gap-3 mb-2">
              <Clock className="w-6 h-6 text-blue-600" />
              <span className="text-sm text-blue-900">Until Exam</span>
            </div>
            <p className="text-3xl text-blue-900">12 days</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Next Review */}
          <div className="lg:col-span-2 space-y-6">
            {/* Next Review Card */}
            <div className="bg-card rounded-3xl shadow-lg p-6 border border-border">
              <div className="flex items-center justify-between mb-4">
                <h3>Next Review</h3>
                <span className="text-sm text-accent bg-accent/10 px-3 py-1 rounded-full">
                  {currentQuestion.difficulty}
                </span>
              </div>
              <div className="mb-4">
                <p className="text-sm text-muted-foreground mb-2">{currentQuestion.topic}</p>
                <p className="text-xl mb-4">{currentQuestion.title}</p>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className="h-full w-3/5 bg-accent rounded-full"></div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Performance: Good • Due for review
                </p>
              </div>
              <button
                onClick={() => navigate('/study')}
                className="w-full bg-accent text-accent-foreground py-3 rounded-2xl hover:opacity-90 transition-opacity"
              >
                Start Review Session
              </button>
            </div>

            {/* Retention Graph */}
            <div className="bg-card rounded-3xl shadow-lg p-6 border border-border">
              <div className="flex items-center gap-2 mb-6">
                <TrendingUp className="w-5 h-5 text-accent" />
                <h3>Your Retention Progress</h3>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={retentionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="day" stroke="#666" />
                  <YAxis stroke="#666" />
                  <Tooltip />
                  <Line type="monotone" dataKey="retention" stroke="#9B72CF" strokeWidth={3} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Right column - Brain Map & CTA */}
          <div className="space-y-6">
            {/* Brain Map */}
            <div className="bg-card rounded-3xl shadow-lg p-6 border border-border">
              <h3 className="mb-4">Brain Map</h3>
              <div className="space-y-3">
                {topicMap.map((topic) => (
                  <div key={topic.name}>
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-sm">{topic.name}</span>
                      <span className={`text-xs ${topic.learned ? 'text-green-600' : 'text-amber-600'}`}>
                        {topic.confidence}%
                      </span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          topic.learned ? 'bg-green-500' : 'bg-amber-400'
                        }`}
                        style={{ width: `${topic.confidence}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Group Study CTA */}
            <div className="bg-gradient-to-br from-accent/20 to-accent/10 rounded-3xl shadow-lg p-6 border border-accent/30">
              <Users className="w-10 h-10 text-accent mb-3" />
              <h3 className="mb-2">Study Together</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Join a group session and learn with your peers
              </p>
              <button
                onClick={() => navigate('/group-study')}
                className="w-full bg-accent text-accent-foreground py-3 rounded-2xl hover:opacity-90 transition-opacity"
              >
                Join Session
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile bottom nav */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-card border-t border-border">
        <div className="flex items-center justify-around py-3">
          <button className="flex flex-col items-center gap-1 text-accent">
            <BookOpen className="w-6 h-6" />
            <span className="text-xs">Home</span>
          </button>
          <button
            onClick={() => navigate('/study')}
            className="flex flex-col items-center gap-1 text-muted-foreground"
          >
            <Target className="w-6 h-6" />
            <span className="text-xs">Study</span>
          </button>
          <button
            onClick={() => navigate('/leaderboard')}
            className="flex flex-col items-center gap-1 text-muted-foreground"
          >
            <Trophy className="w-6 h-6" />
            <span className="text-xs">Rank</span>
          </button>
          <button
            onClick={() => navigate('/group-study')}
            className="flex flex-col items-center gap-1 text-muted-foreground"
          >
            <Users className="w-6 h-6" />
            <span className="text-xs">Groups</span>
          </button>
        </div>
      </nav>
    </div>
  );
}
