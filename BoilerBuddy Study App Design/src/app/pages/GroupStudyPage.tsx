import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Send, Users, Clock, CheckCircle } from 'lucide-react';

const activeMembers = [
  { id: 1, name: 'Jamie S.', avatar: 'JS', status: 'active', answered: true },
  { id: 2, name: 'Alex M.', avatar: 'AM', status: 'active', answered: false },
  { id: 3, name: 'Taylor R.', avatar: 'TR', status: 'thinking', answered: true },
  { id: 4, name: 'Morgan P.', avatar: 'MP', status: 'active', answered: false },
];

const chatMessages = [
  { id: 1, user: 'Jamie S.', message: 'Hey everyone! Ready to tackle derivatives?', time: '2:05 PM' },
  { id: 2, user: 'Alex M.', message: "Let's do this!", time: '2:06 PM' },
  { id: 3, user: 'System', message: 'New question loaded: Find derivative of 3x² + 2x - 5', time: '2:07 PM', isSystem: true },
  { id: 4, user: 'Taylor R.', message: 'Is it 6x + 2?', time: '2:08 PM' },
];

export function GroupStudyPage() {
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [sessionCode] = useState('ABC-123');

  const handleSendMessage = () => {
    if (message.trim()) {
      console.log('Send message:', message);
      setMessage('');
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 hover:bg-muted rounded-xl transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-accent" />
            <div>
              <h3 className="text-sm">Group Study Session</h3>
              <p className="text-xs text-muted-foreground">Code: {sessionCode}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="w-4 h-4" />
            <span className="text-sm">24:15</span>
          </div>
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row max-w-7xl mx-auto w-full">
        {/* Left: Question feed */}
        <div className="flex-1 p-4 lg:p-6 overflow-y-auto">
          <div className="bg-card rounded-3xl shadow-lg p-6 border border-border mb-6">
            <div className="flex items-center justify-between mb-4">
              <span className="inline-block text-xs text-accent bg-accent/10 px-3 py-1 rounded-full">
                Current Question
              </span>
              <div className="flex items-center gap-2">
                <div className="flex -space-x-2">
                  {activeMembers.filter(m => m.answered).map((member) => (
                    <div
                      key={member.id}
                      className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center border-2 border-card text-white text-xs"
                    >
                      <CheckCircle className="w-4 h-4" />
                    </div>
                  ))}
                </div>
                <span className="text-sm text-muted-foreground">
                  {activeMembers.filter(m => m.answered).length}/{activeMembers.length} answered
                </span>
              </div>
            </div>

            <h2 className="mb-4">Find the derivative of f(x) = 3x² + 2x - 5</h2>

            <div className="space-y-3">
              {['6x + 2', '6x² + 2x', '3x + 2', '6x'].map((option, index) => (
                <button
                  key={index}
                  className="w-full text-left p-4 rounded-2xl border-2 border-border hover:border-accent/50 hover:bg-accent/5 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm">
                      {String.fromCharCode(65 + index)}
                    </span>
                    <span>{option}</span>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-6 h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-3/4 bg-amber-500 rounded-full transition-all"></div>
            </div>
            <p className="text-xs text-muted-foreground mt-2 text-center">
              Time remaining: 45 seconds
            </p>
          </div>

          {/* Answer history */}
          <div className="bg-card rounded-3xl shadow-lg p-6 border border-border">
            <h3 className="mb-4">Previous Questions</h3>
            <div className="space-y-3">
              {[
                { q: 'Evaluate ∫x² dx', a: 'x³/3 + C', correct: 3 },
                { q: 'Find lim(x→0) sin(x)/x', a: '1', correct: 4 },
              ].map((item, index) => (
                <div key={index} className="p-4 bg-muted/50 rounded-2xl">
                  <p className="text-sm mb-2">{item.q}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-green-600">Answer: {item.a}</span>
                    <span className="text-xs text-muted-foreground">
                      {item.correct}/{activeMembers.length} correct
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Chat and members */}
        <div className="lg:w-96 border-t lg:border-t-0 lg:border-l border-border flex flex-col">
          {/* Active members */}
          <div className="p-4 border-b border-border">
            <h4 className="mb-3 text-sm text-muted-foreground">Active Members</h4>
            <div className="space-y-2">
              {activeMembers.map((member) => (
                <div key={member.id} className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-accent-foreground relative">
                    {member.avatar}
                    <div className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-card ${
                      member.status === 'active' ? 'bg-green-500' : 'bg-amber-500'
                    }`}></div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm">{member.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {member.status === 'active' ? 'Active' : 'Thinking...'}
                    </p>
                  </div>
                  {member.answered && <CheckCircle className="w-5 h-5 text-green-600" />}
                </div>
              ))}
            </div>
          </div>

          {/* Chat */}
          <div className="flex-1 flex flex-col">
            <div className="flex-1 p-4 overflow-y-auto space-y-3">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={msg.isSystem ? 'text-center' : ''}
                >
                  {msg.isSystem ? (
                    <p className="text-xs text-muted-foreground bg-muted px-3 py-2 rounded-full inline-block">
                      {msg.message}
                    </p>
                  ) : (
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-xs">{msg.user}</p>
                        <span className="text-xs text-muted-foreground">{msg.time}</span>
                      </div>
                      <div className="bg-muted rounded-2xl rounded-tl-none px-4 py-2">
                        <p className="text-sm">{msg.message}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Message input */}
            <div className="p-4 border-t border-border">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                  placeholder="Type a message..."
                  className="flex-1 px-4 py-3 rounded-2xl border-2 border-border bg-input-background focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!message.trim()}
                  className="px-4 py-3 bg-accent text-accent-foreground rounded-2xl hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
