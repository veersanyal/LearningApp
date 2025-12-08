"""
Gamification Module for Learning App
XP system, levels, and achievements

Author: Veer Sanyal
Date: December 2025

Academic Integrity Statement:
This is original work for gamification features.
"""

from database import get_db
from datetime import datetime, timedelta
import math


# XP Calculation Constants
BASE_XP = 10
DIFFICULTY_MULTIPLIERS = {
    "easy": 1.0,
    "medium": 1.5,
    "hard": 2.0
}
STREAK_BONUS_THRESHOLD = 7  # 7+ day streak gets bonus
STREAK_BONUS_XP = 5
FIRST_ATTEMPT_BONUS = 10
SPEED_BONUS_THRESHOLD = 30  # seconds
SPEED_BONUS_XP = 5
GUIDE_ME_PENALTY = 0.8  # 20% reduction


def calculate_xp(difficulty, is_correct, is_first_attempt=False, time_taken=None, 
                 used_guide_me=False, user_streak=0):
    """
    Calculate XP earned for answering a question.
    
    Args:
        difficulty: Question difficulty ("easy", "medium", "hard")
        is_correct: Whether the answer was correct
        is_first_attempt: Whether this is the first attempt on this question
        time_taken: Time in seconds to answer
        used_guide_me: Whether the user used the Guide Me feature
        user_streak: User's current study streak
    
    Returns:
        XP earned (integer)
    """
    if not is_correct:
        return 0  # No XP for incorrect answers
    
    # Base XP with difficulty multiplier
    xp = BASE_XP * DIFFICULTY_MULTIPLIERS.get(difficulty, 1.0)
    
    # Streak bonus (7+ day streak)
    if user_streak >= STREAK_BONUS_THRESHOLD:
        xp += STREAK_BONUS_XP
    
    # First attempt bonus
    if is_first_attempt:
        xp += FIRST_ATTEMPT_BONUS
    
    # Speed bonus (answered in < 30 seconds)
    if time_taken and time_taken < SPEED_BONUS_THRESHOLD:
        xp += SPEED_BONUS_XP
    
    # Guide Me penalty (20% reduction)
    if used_guide_me:
        xp *= GUIDE_ME_PENALTY
    
    return int(xp)


def get_level_from_xp(total_xp):
    """
    Calculate user level based on total XP.
    
    Level thresholds:
    - Level 1-10: 0-500 XP per level
    - Level 11-25: 500-1000 XP per level
    - Level 26-50: 1000-2000 XP per level
    - Level 51+: 2000+ XP per level
    
    Args:
        total_xp: Total XP accumulated
    
    Returns:
        Current level (integer)
    """
    if total_xp < 5000:  # Levels 1-10
        return min(10, (total_xp // 500) + 1)
    elif total_xp < 20000:  # Levels 11-25
        return 10 + ((total_xp - 5000) // 1000) + 1
    elif total_xp < 70000:  # Levels 26-50
        return 25 + ((total_xp - 20000) // 2000) + 1
    else:  # Level 51+
        return 50 + ((total_xp - 70000) // 2000) + 1


def get_xp_for_next_level(current_level):
    """
    Calculate XP needed for next level.
    
    Args:
        current_level: Current level
    
    Returns:
        XP threshold for next level
    """
    if current_level < 10:
        return (current_level + 1) * 500
    elif current_level < 25:
        return 5000 + (current_level - 10 + 1) * 1000
    elif current_level < 50:
        return 20000 + (current_level - 25 + 1) * 2000
    else:
        return 70000 + (current_level - 50 + 1) * 2000


def get_xp_progress(total_xp):
    """
    Get XP progress within current level.
    
    Args:
        total_xp: Total XP
    
    Returns:
        Dictionary with current_level, xp_current_level, xp_needed_next_level, progress_percent
    """
    current_level = get_level_from_xp(total_xp)
    xp_current_level_threshold = get_xp_for_next_level(current_level - 1) if current_level > 1 else 0
    xp_next_level_threshold = get_xp_for_next_level(current_level)
    
    xp_in_current_level = total_xp - xp_current_level_threshold
    xp_needed_for_next = xp_next_level_threshold - xp_current_level_threshold
    
    progress_percent = (xp_in_current_level / xp_needed_for_next) * 100 if xp_needed_for_next > 0 else 0
    
    return {
        "current_level": current_level,
        "xp_in_current_level": xp_in_current_level,
        "xp_needed_for_next": xp_needed_for_next,
        "progress_percent": min(100, progress_percent)
    }


def award_xp(user_id, xp_amount):
    """
    Award XP to a user and update their level.
    
    Args:
        user_id: User ID
        xp_amount: Amount of XP to award
    
    Returns:
        Dictionary with level_up info if applicable
    """
    db = get_db()
    
    try:
        # Get current XP and level
        user = db.cursor.execute(
            'SELECT total_xp FROM users WHERE user_id = ?', (user_id,)
        ).fetchone()
        
        if not user:
            return {"error": "User not found"}
        
        old_xp = user['total_xp']
        old_level = get_level_from_xp(old_xp)
        
        # Update XP
        new_xp = old_xp + xp_amount
        new_level = get_level_from_xp(new_xp)
        
        db.cursor.execute(
            'UPDATE users SET total_xp = ? WHERE user_id = ?',
            (new_xp, user_id)
        )
        db.conn.commit()
        
        # Check for level up
        level_up = new_level > old_level
        
        result = {
            "xp_awarded": xp_amount,
            "total_xp": new_xp,
            "old_level": old_level,
            "new_level": new_level,
            "level_up": level_up
        }
        
        if level_up:
            result["level_up_message"] = f"Congratulations! You reached Level {new_level}!"
            
            # Check for level-up rewards
            rewards = get_level_rewards(new_level)
            if rewards:
                result["rewards"] = rewards
        
        return result
        
    finally:
        db.disconnect()


def get_level_rewards(level):
    """
    Get rewards for reaching a level.
    
    Args:
        level: Level number
    
    Returns:
        List of rewards (strings)
    """
    rewards = []
    
    if level % 10 == 0:
        rewards.append(f"New title unlocked!")
    
    if level % 5 == 0:
        rewards.append(f"New avatar frame unlocked!")
    
    if level == 25:
        rewards.append("Study Group Creator feature unlocked!")
    
    if level == 50:
        rewards.append("Course Champion status unlocked!")
    
    return rewards


def check_achievements(user_id):
    """
    Check all achievement conditions for a user and award any newly earned ones.
    
    Args:
        user_id: User ID
    
    Returns:
        List of newly earned achievements
    """
    db = get_db()
    newly_earned = []
    
    try:
        # Get all achievements
        achievements = db.cursor.execute('SELECT * FROM achievements').fetchall()
        
        # Get user's current achievements
        user_achievements = db.cursor.execute(
            'SELECT achievement_id FROM user_achievements WHERE user_id = ?',
            (user_id,)
        ).fetchall()
        
        earned_ids = [a['achievement_id'] for a in user_achievements]
        
        # Get user progress for checking conditions
        progress = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ?', (user_id,)
        ).fetchall()
        
        user = db.cursor.execute(
            'SELECT * FROM users WHERE user_id = ?', (user_id,)
        ).fetchone()
        
        total_attempts = sum(p['attempts'] for p in progress)
        total_correct = sum(p['correct'] for p in progress)
        mastered_topics = sum(1 for p in progress if p['mastery'] >= 1.0)
        
        # Check each achievement
        for achievement in achievements:
            if achievement['achievement_id'] in earned_ids:
                continue  # Already earned
            
            requirement_type = achievement['requirement_type']
            requirement_value = achievement['requirement_value']
            earned = False
            
            # Check different achievement types
            if requirement_type == 'questions':
                if total_attempts >= int(requirement_value):
                    earned = True
            
            elif requirement_type == 'streak':
                if user['study_streak'] >= int(requirement_value):
                    earned = True
            
            elif requirement_type == 'streak_correct':
                # Check for consecutive correct answers
                max_streak = 0
                current_streak = 0
                for p in progress:
                    if p['streak_correct'] > current_streak:
                        current_streak = p['streak_correct']
                    if current_streak > max_streak:
                        max_streak = current_streak
                
                if max_streak >= int(requirement_value):
                    earned = True
            
            elif requirement_type == 'mastery':
                # Check for any topic with 100% mastery
                if mastered_topics >= 1:
                    earned = True
            
            elif requirement_type == 'mastered_topics':
                if mastered_topics >= int(requirement_value):
                    earned = True
            
            # Award achievement if earned
            if earned:
                award_achievement(user_id, achievement['achievement_id'])
                newly_earned.append(dict(achievement))
        
        return newly_earned
        
    finally:
        db.disconnect()


def award_achievement(user_id, achievement_id):
    """
    Award an achievement to a user.
    
    Args:
        user_id: User ID
        achievement_id: Achievement ID
    """
    db = get_db()
    
    try:
        # Check if already earned
        existing = db.cursor.execute(
            'SELECT * FROM user_achievements WHERE user_id = ? AND achievement_id = ?',
            (user_id, achievement_id)
        ).fetchone()
        
        if existing:
            return  # Already earned
        
        # Award achievement
        db.cursor.execute(
            'INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)',
            (user_id, achievement_id)
        )
        
        # Award XP bonus
        achievement = db.cursor.execute(
            'SELECT xp_reward FROM achievements WHERE achievement_id = ?',
            (achievement_id,)
        ).fetchone()
        
        if achievement and achievement['xp_reward'] > 0:
            db.cursor.execute(
                'UPDATE users SET total_xp = total_xp + ? WHERE user_id = ?',
                (achievement['xp_reward'], user_id)
            )
        
        db.conn.commit()
        
    except Exception as e:
        print(f"Error awarding achievement: {e}")
        db.conn.rollback()
    finally:
        db.disconnect()


def get_user_achievements(user_id):
    """
    Get all achievements for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of dictionaries with achievement data and unlock timestamps
    """
    db = get_db()
    
    try:
        achievements = db.cursor.execute('''
            SELECT a.*, ua.unlocked_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.achievement_id
            WHERE ua.user_id = ?
            ORDER BY ua.unlocked_at DESC
        ''', (user_id,)).fetchall()
        
        return [dict(a) for a in achievements]
        
    finally:
        db.disconnect()


def get_all_achievements_with_status(user_id):
    """
    Get all achievements with user's unlock status.
    
    Args:
        user_id: User ID
    
    Returns:
        List of achievements with unlocked status
    """
    db = get_db()
    
    try:
        achievements = db.cursor.execute('''
            SELECT a.*, 
                   CASE WHEN ua.user_achievement_id IS NOT NULL THEN 1 ELSE 0 END as unlocked,
                   ua.unlocked_at
            FROM achievements a
            LEFT JOIN user_achievements ua ON a.achievement_id = ua.achievement_id AND ua.user_id = ?
            ORDER BY a.achievement_id
        ''', (user_id,)).fetchall()
        
        return [dict(a) for a in achievements]
        
    finally:
        db.disconnect()

