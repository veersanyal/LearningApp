# StudyBoiler - Quick Start Guide

Welcome to StudyBoiler, Purdue's AI-powered adaptive learning platform!

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Google Gemini API key

### Installation

1. **Install Dependencies**
```bash
pip install -r Info/requirements.txt
```

2. **Set Up Environment Variables**
```bash
# Create .env file
echo "GEMINI_API_KEY=your_api_key_here" > .env
echo "SECRET_KEY=your_secret_key_here" >> .env
```

3. **Initialize Database**
```bash
python -c "from database import init_db; from app import app; app.app_context().push(); init_db()"
```

4. **Run the Application**
```bash
python app.py
```

5. **Open Browser**
```
http://localhost:5000
```

---

## 📱 First Time User Flow

### Step 1: Register Account
1. Open the app (you'll see the login modal)
2. Click "Register" tab
3. Fill in:
   - Username (required, min 3 characters)
   - Password (required, min 6 characters)
   - Major (optional, e.g., "Computer Science")
   - Graduation Year (optional, e.g., 2026)
4. Click "Register"
5. You'll be automatically logged in

### Step 2: Upload Study Material
1. Click "📚 Home" in the sidebar
2. Click "Upload Material" button
3. Choose one of:
   - **PDF File** (lecture notes, textbook chapter)
   - **Image** (screenshot of slides, handwritten notes)
   - **Text** (paste text directly)
4. Click "Upload & Process"
5. Wait for AI to extract topics

### Step 3: Start Learning
1. Click "Generate Question" button
2. Read the question carefully
3. Select your answer from the options
4. Click "Submit Answer"
5. Get instant feedback:
   - ✅ Correct → Earn XP, increase mastery
   - ❌ Wrong → See explanation, topic marked for review

### Step 4: Explore Features

**View Analytics:**
- Click "📊 Analytics" to see:
  - Forgetting curve graph
  - Study heatmap
  - Time-of-day performance
  - Mastery progress

**Check Leaderboards:**
- Click "🏆 Leaderboards" to see:
  - Global rankings
  - Your rank
  - Nearby competitors

**View Achievements:**
- Click "🎖️ Achievements" to see:
  - All 12 achievements
  - Your unlocked badges
  - XP rewards

---

## 🎮 Gamification Features

### XP System
**How to Earn XP:**
- Correct answer: 10 XP base
- Medium difficulty: +50% XP
- Hard difficulty: +100% XP
- 7+ day streak: +5 XP bonus
- First correct attempt: +10 XP bonus
- Speed bonus (<30s): +5 XP

**XP Penalties:**
- Using "Guide Me": -20% XP

### Leveling
- Start at Level 1
- Level up by earning XP:
  - Levels 1-10: 500 XP each
  - Levels 11-25: 1000 XP each
  - Levels 26-50: 2000 XP each
- View progress in user profile (bottom left)

### Achievements

**Quick Achievements (Try First):**
1. **First Step** (10 XP) - Answer 1 question
2. **Getting Started** (20 XP) - Answer 10 questions
3. **Early Bird** (40 XP) - Study before 8 AM
4. **Night Owl** (40 XP) - Study after 10 PM

**Challenge Achievements:**
5. **Perfect Ten** (100 XP) - 10 correct in a row
6. **Week Warrior** (75 XP) - 7-day study streak
7. **Topic Master** (120 XP) - 100% mastery in a topic

**Long-term Achievements:**
8. **Centurion** (50 XP) - Answer 100 questions
9. **Unstoppable** (150 XP) - 30-day streak
10. **Scholar** (200 XP) - Master 5 topics

---

## 🏆 Leaderboard Types

### Global Leaderboard
- All users ranked by total XP
- See top performers
- Find your rank

### By Major
- Filter by your major
- See how you stack up against classmates
- Example: "Computer Science"

### Time Periods
- **All Time** - Total XP since account creation
- **This Month** - XP earned in last 30 days
- **This Week** - XP earned in last 7 days

---

## 🎯 Challenge System

### Create a Challenge

1. **Answer a Question First**
   - Generate and answer a question
   
2. **Create Challenge** (feature in development)
   - Click "Challenge a Friend"
   - Choose friend or create link
   - Share 6-character code

3. **Accept Challenges**
   - Receive challenge notification
   - Click to accept
   - Answer the question
   - See who won!

---

## 💡 Pro Tips

### Maximize XP
1. **Study consistently** - Build your streak
2. **Try hard questions** - Double XP
3. **Answer quickly** - Speed bonus
4. **First try matters** - Bonus for first correct answer
5. **Avoid Guide Me** - Use only when stuck

### Effective Learning
1. **Review weak topics** - Check right panel
2. **Follow forgetting curve** - Review before you forget
3. **Use Exam Prep** - Plan your study sessions
4. **Check analytics** - Find your peak study times
5. **Master topics completely** - Aim for 100%

### Social Features
1. **Check activity feed** - See what others are achieving
2. **Climb leaderboards** - Compete with friends
3. **Create challenges** - Test your knowledge
4. **Submit questions** - Help the community
5. **Track streaks** - Don't break the chain!

---

## 📊 Understanding Your Stats

### Right Panel Stats

**Study Streak:** 
- Days you've studied consecutively
- 🔥 Icon shows streak length
- Break if you miss a day

**Total Questions:**
- All questions you've answered
- Includes correct and incorrect

**Accuracy:**
- Percentage of correct answers
- (Correct / Total) × 100%

**Topics Studied:**
- Number of unique topics practiced
- Extracted from your materials

**Weekly Questions:**
- Questions answered in last 7 days
- Resets weekly

**Mastered Topics:**
- Topics with ≥95% mastery
- Shows true understanding

**Daily Progress:**
- Progress toward daily goal
- Encourages consistency

---

## 🔧 Troubleshooting

### "No topics available"
- Upload study material first
- Wait for processing to complete
- Check that file contains actual content

### "Login failed"
- Check username and password
- Ensure account is registered
- Try registering if new user

### "Question generation failed"
- Check your Gemini API key
- Ensure API quota not exceeded
- Try uploading different content

### Charts not loading
- Check browser console for errors
- Ensure you have answered questions
- Try refreshing the page

### Slow performance
- Clear browser cache
- Check internet connection
- Restart the server

---

## 🎓 Best Practices

### For Maximum Learning
1. Study 20-30 minutes daily
2. Take breaks between questions
3. Review explanations for wrong answers
4. Focus on weak topics first
5. Use spaced repetition

### For High Scores
1. Maintain study streaks
2. Answer harder questions
3. Be quick but accurate
4. Complete all topics
5. Use analytics to improve

### For Community
1. Submit quality questions
2. Accept challenges
3. Check activity feed
4. Compete on leaderboards
5. Share with friends

---

## 📈 Progress Tracking

### Daily Routine
- [ ] Log in (maintain streak)
- [ ] Answer 10 questions (Getting Started)
- [ ] Review weak topics
- [ ] Check leaderboard position
- [ ] View new achievements

### Weekly Goals
- [ ] 70+ questions (10/day)
- [ ] Master 1 new topic
- [ ] Improve accuracy by 5%
- [ ] Move up leaderboard
- [ ] Complete 1 challenge

### Monthly Milestones
- [ ] 300+ questions
- [ ] 5+ mastered topics
- [ ] Top 10 in major leaderboard
- [ ] All quick achievements
- [ ] 30-day streak

---

## 🆘 Need Help?

### Common Questions

**Q: How is mastery calculated?**
A: Mastery uses a combination of accuracy, recency, and spaced repetition intervals. Answer correctly multiple times over time to increase mastery.

**Q: When do I level up?**
A: Check your XP progress in the user profile. You'll get a notification when you level up.

**Q: How do streaks work?**
A: Answer at least 1 question per day. Streaks break if you skip a day.

**Q: Can I change my major?**
A: Settings feature coming soon! For now, it's set at registration.

**Q: How do I delete my account?**
A: Contact admin or use Settings → Clear All Progress (destructive).

---

## 🎉 Ready to Go!

You're all set! Here's your first challenge:

1. ✅ Register account
2. ✅ Upload study material
3. ✅ Answer 10 questions
4. ✅ Unlock "Getting Started" achievement
5. ✅ Check your rank on leaderboard
6. ✅ Start your study streak!

**Good luck and happy studying! 🎓**

---

## 📞 Support

For issues or questions:
- Check troubleshooting section above
- Review implementation docs in `Info/`
- Check console for error messages

---

**Version:** 2.0.0  
**Last Updated:** December 8, 2025  
**Status:** Production Ready

