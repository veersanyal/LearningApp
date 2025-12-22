import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, HelpCircle, Check, AlertCircle, ChevronRight, Lightbulb } from 'lucide-react';

const steps = [
  { id: 1, title: 'Understand the problem', completed: true },
  { id: 2, title: 'Identify the rule', completed: true },
  { id: 3, title: 'Apply the formula', completed: false },
  { id: 4, title: 'Simplify the result', completed: false },
];

const options = [
  { id: 'a', text: '6x + 2', correct: true },
  { id: 'b', text: '6x² + 2x' },
  { id: 'c', text: '3x + 2' },
  { id: 'd', text: '6x' },
];

export function StudyPage() {
  const navigate = useNavigate();
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [showHint, setShowHint] = useState(false);
  const [showWalkthrough, setShowWalkthrough] = useState(false);
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = () => {
    if (selectedAnswer) {
      // Check answer and proceed
      console.log('Submitted:', selectedAnswer);
    }
  };

  return (
    <div className="min-h-screen bg-background pb-20 lg:pb-0">
      {/* Header */}
      <header className="bg-card border-b border-border sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 hover:bg-muted rounded-xl transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
          <div className="flex-1 mx-4">
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-1/2 bg-accent rounded-full transition-all"></div>
            </div>
          </div>
          <span className="text-sm text-muted-foreground">2/5</span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Breadcrumb stepper */}
        <div className="mb-8 bg-card rounded-2xl p-6 border border-border">
          <h4 className="mb-4 text-muted-foreground">Problem-solving steps</h4>
          <div className="space-y-3">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    step.completed
                      ? 'bg-green-500 text-white'
                      : index === 2
                      ? 'bg-accent text-accent-foreground'
                      : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {step.completed ? <Check className="w-5 h-5" /> : step.id}
                </div>
                <span
                  className={
                    step.completed
                      ? 'text-green-600'
                      : index === 2
                      ? 'text-foreground'
                      : 'text-muted-foreground'
                  }
                >
                  {step.title}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Question card */}
        <div className="bg-card rounded-3xl shadow-lg p-8 border border-border mb-6">
          <div className="flex items-start justify-between mb-6">
            <div className="flex-1">
              <span className="inline-block text-xs text-accent bg-accent/10 px-3 py-1 rounded-full mb-3">
                Derivatives
              </span>
              <h2 className="mb-4">Find the derivative of f(x) = 3x² + 2x - 5</h2>
              <p className="text-muted-foreground">
                Use the power rule to find the derivative of this polynomial function.
              </p>
            </div>
          </div>

          {/* AI Hint */}
          {showHint && (
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-2xl p-4">
              <div className="flex gap-3">
                <Lightbulb className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="text-blue-900 mb-1">Hint</h4>
                  <p className="text-sm text-blue-800">
                    Remember: The power rule states that d/dx(xⁿ) = n·xⁿ⁻¹. Apply this to each
                    term separately.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Multiple choice options */}
          <div className="space-y-3 mb-6">
            {options.map((option) => (
              <button
                key={option.id}
                onClick={() => setSelectedAnswer(option.id)}
                className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
                  selectedAnswer === option.id
                    ? 'border-accent bg-accent/10'
                    : 'border-border hover:border-accent/50 hover:bg-accent/5'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm">
                    {option.id.toUpperCase()}
                  </span>
                  <span>{option.text}</span>
                  {option.correct && selectedAnswer === option.id && (
                    <Check className="w-5 h-5 text-green-600 ml-auto" />
                  )}
                </div>
              </button>
            ))}
          </div>

          {/* LaTeX input area (alternative answer method) */}
          <div className="mb-6">
            <label className="block mb-2 text-sm text-muted-foreground">
              Or type your answer (LaTeX supported):
            </label>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="e.g., 6x + 2"
              className="w-full p-4 rounded-2xl border-2 border-border bg-input-background focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
            />
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => setShowHint(true)}
              className="flex items-center justify-center gap-2 px-6 py-3 rounded-2xl border-2 border-border hover:bg-muted transition-colors"
            >
              <HelpCircle className="w-5 h-5" />
              Show Hint
            </button>
            <button
              onClick={handleSubmit}
              disabled={!selectedAnswer && !inputValue}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-accent text-accent-foreground hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Check Answer
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Floating "I feel stuck" button */}
        <button
          onClick={() => setShowWalkthrough(!showWalkthrough)}
          className="fixed bottom-24 lg:bottom-8 right-8 bg-destructive text-destructive-foreground px-6 py-4 rounded-full shadow-lg hover:opacity-90 transition-opacity flex items-center gap-2"
        >
          <AlertCircle className="w-5 h-5" />
          I feel stuck
        </button>

        {/* Walkthrough modal */}
        {showWalkthrough && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-card rounded-3xl shadow-2xl p-8 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="mb-2">Step-by-step walkthrough</h2>
                  <p className="text-muted-foreground">Let's break this down together!</p>
                </div>
                <button
                  onClick={() => setShowWalkthrough(false)}
                  className="p-2 hover:bg-muted rounded-xl transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-6">
                <div className="bg-accent/10 rounded-2xl p-4 border border-accent/30">
                  <h4 className="mb-2">Step 1: Identify the terms</h4>
                  <p className="text-sm">
                    The function f(x) = 3x² + 2x - 5 has three terms: 3x², 2x, and -5
                  </p>
                </div>

                <div className="bg-accent/10 rounded-2xl p-4 border border-accent/30">
                  <h4 className="mb-2">Step 2: Apply the power rule to each term</h4>
                  <p className="text-sm">
                    • For 3x²: multiply the coefficient (3) by the exponent (2) and reduce the
                    exponent by 1 → 6x
                  </p>
                  <p className="text-sm mt-2">
                    • For 2x: the exponent is 1, so 2·1·x⁰ → 2
                  </p>
                  <p className="text-sm mt-2">• For -5: the derivative of a constant is 0</p>
                </div>

                <div className="bg-accent/10 rounded-2xl p-4 border border-accent/30">
                  <h4 className="mb-2">Step 3: Combine the results</h4>
                  <p className="text-sm">f'(x) = 6x + 2 + 0 = 6x + 2</p>
                </div>

                <button
                  onClick={() => setShowWalkthrough(false)}
                  className="w-full bg-accent text-accent-foreground py-3 rounded-2xl hover:opacity-90 transition-opacity"
                >
                  Got it, thanks!
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
