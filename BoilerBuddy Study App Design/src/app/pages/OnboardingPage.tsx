import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, ChevronRight, BookOpen, Calendar, Brain } from 'lucide-react';

const courses = [
  'MA 161 – Calculus I',
  'MA 162 – Calculus II',
  'MA 165 – Analytic Geometry & Calculus I',
  'MA 166 – Analytic Geometry & Calculus II',
  'MA 261 – Multivariate Calculus',
  'MA 265 – Linear Algebra',
];

const topics = [
  { id: 'limits', name: 'Limits' },
  { id: 'derivatives', name: 'Derivatives' },
  { id: 'integrals', name: 'Integrals' },
  { id: 'series', name: 'Series' },
  { id: 'vectorcalc', name: 'Vector Calculus' },
  { id: 'diffeq', name: 'Differential Equations' },
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [selectedCourse, setSelectedCourse] = useState('');
  const [examDate, setExamDate] = useState('');
  const [topicStrengths, setTopicStrengths] = useState<Record<string, number>>({
    limits: 3,
    derivatives: 3,
    integrals: 3,
    series: 3,
    vectorcalc: 3,
    diffeq: 3,
  });

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      // Complete onboarding
      navigate('/dashboard');
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const canProceed = () => {
    if (step === 1) return selectedCourse !== '';
    if (step === 2) return examDate !== '';
    return true;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-purple-50/20 to-amber-50/30 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Progress indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-2 rounded-full transition-all ${
                s === step ? 'w-12 bg-accent' : s < step ? 'w-8 bg-secondary' : 'w-8 bg-border'
              }`}
            />
          ))}
        </div>

        {/* Main card */}
        <div className="bg-card rounded-3xl shadow-xl p-8 md:p-12 border border-border">
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-4">
              {step === 1 && <BookOpen className="w-8 h-8 text-accent" />}
              {step === 2 && <Calendar className="w-8 h-8 text-accent" />}
              {step === 3 && <Brain className="w-8 h-8 text-accent" />}
              <h2>
                {step === 1 && 'Pick your course'}
                {step === 2 && 'Set your exam date'}
                {step === 3 && 'Rate your topic strengths'}
              </h2>
            </div>
            <p className="text-muted-foreground">
              {step === 1 && 'Which math course are you studying for?'}
              {step === 2 && "When's your next exam? We'll build a study plan for you."}
              {step === 3 && 'Help us understand where you are so we can personalize your learning.'}
            </p>
          </div>

          {/* Step 1: Course selection */}
          {step === 1 && (
            <div className="space-y-3">
              {courses.map((course) => (
                <button
                  key={course}
                  onClick={() => setSelectedCourse(course)}
                  className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
                    selectedCourse === course
                      ? 'border-accent bg-accent/10'
                      : 'border-border hover:border-accent/50 hover:bg-accent/5'
                  }`}
                >
                  {course}
                </button>
              ))}
            </div>
          )}

          {/* Step 2: Exam date */}
          {step === 2 && (
            <div>
              <input
                type="date"
                value={examDate}
                onChange={(e) => setExamDate(e.target.value)}
                className="w-full p-4 rounded-2xl border-2 border-border bg-input-background focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
              />
              <p className="text-sm text-muted-foreground mt-4">
                💡 Tip: We recommend starting at least 2 weeks before your exam for optimal results!
              </p>
            </div>
          )}

          {/* Step 3: Topic strengths */}
          {step === 3 && (
            <div className="space-y-6">
              {topics.map((topic) => (
                <div key={topic.id}>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm">{topic.name}</label>
                    <span className="text-sm text-muted-foreground">
                      {topicStrengths[topic.id]}/5
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="5"
                    value={topicStrengths[topic.id]}
                    onChange={(e) =>
                      setTopicStrengths({
                        ...topicStrengths,
                        [topic.id]: parseInt(e.target.value),
                      })
                    }
                    className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-accent"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>Beginner</span>
                    <span>Expert</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Navigation buttons */}
          <div className="flex gap-3 mt-8">
            {step > 1 && (
              <button
                onClick={handleBack}
                className="flex items-center gap-2 px-6 py-3 rounded-2xl border-2 border-border hover:bg-muted transition-colors"
              >
                <ChevronLeft className="w-5 h-5" />
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={!canProceed()}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-2xl bg-accent text-accent-foreground hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {step === 3 ? "Let's go!" : 'Next'}
              {step < 3 && <ChevronRight className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
