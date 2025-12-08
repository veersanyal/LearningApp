"""
Activity Feed Module for Learning App
Live activity tracking and social proof

Author: Veer Sanyal
Date: December 2025

Academic Integrity Statement:
This is original work for activity feed features.
"""

from database import get_db
from datetime import datetime, timedelta


def record_activity(user_id, activity_type, data):
    """
    Record an activity event.
    
    Args:
        user_id: User who performed the activity
        activity_type: Type of activity ('level_up', 'achievement', 'rank_change', 'milestone')
        data: Additional data as JSON string
    
    Note: This would ideally use an activities table, but for Phase 2 we're
    tracking through existing tables (user_achievements, user_progress, etc.)
    """
    # Placeholder - in production would insert into activities table
    pass


def get_recent_activity(limit=10, hours=24):
    """
    Get recent activity across all users.
    
    Args:
        limit: Maximum number of activities to return
        hours: How many hours back to look
    
    Returns:
        List of activity items
    """
    db = get_db()
    activities = []
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Get recent achievements
        recent_achievements = db.cursor.execute('''
            SELECT 
                u.username,
                a.achievement_name,
                a.badge_icon,
                ua.unlocked_at
            FROM user_achievements ua
            JOIN users u ON ua.user_id = u.user_id
            JOIN achievements a ON ua.achievement_id = a.achievement_id
            WHERE ua.unlocked_at >= ?
            ORDER BY ua.unlocked_at DESC
            LIMIT ?
        ''', (cutoff_time, limit // 2)).fetchall()
        
        for ach in recent_achievements:
            activities.append({
                "type": "achievement",
                "username": ach['username'],
                "message": f"{ach['username']} unlocked {ach['badge_icon']} {ach['achievement_name']}!",
                "timestamp": ach['unlocked_at'],
                "icon": "🎉"
            })
        
        # Get recent level ups (users with high XP recently gained)
        # This is an approximation - ideally we'd track level-up events
        high_xp_users = db.cursor.execute('''
            SELECT 
                u.username,
                u.total_xp
            FROM users u
            WHERE u.last_login >= ?
            ORDER BY u.total_xp DESC
            LIMIT ?
        ''', (cutoff_time, limit // 4)).fetchall()
        
        for user in high_xp_users:
            # Calculate level
            from gamification import get_level_from_xp
            level = get_level_from_xp(user['total_xp'])
            
            if level >= 10:  # Only show significant levels
                activities.append({
                    "type": "level_up",
                    "username": user['username'],
                    "message": f"{user['username']} reached Level {level}!",
                    "timestamp": datetime.now().isoformat(),
                    "icon": "⭐"
                })
        
        # Get topic mastery achievements
        recent_mastery = db.cursor.execute('''
            SELECT 
                u.username,
                up.topic_id,
                up.updated_at
            FROM user_progress up
            JOIN users u ON up.user_id = u.user_id
            WHERE up.mastery >= 0.95 AND up.updated_at >= ?
            ORDER BY up.updated_at DESC
            LIMIT ?
        ''', (cutoff_time, limit // 4)).fetchall()
        
        for mastery in recent_mastery:
            activities.append({
                "type": "mastery",
                "username": mastery['username'],
                "message": f"{mastery['username']} mastered {mastery['topic_id']}!",
                "timestamp": mastery['updated_at'],
                "icon": "🏆"
            })
        
        # Sort all activities by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activities[:limit]
        
    finally:
        db.disconnect()


def get_user_activity_feed(user_id, limit=20):
    """
    Get activity feed for a specific user.
    
    Args:
        user_id: User ID
        limit: Maximum activities to return
    
    Returns:
        List of user's recent activities
    """
    db = get_db()
    activities = []
    
    try:
        # User's achievements
        achievements = db.cursor.execute('''
            SELECT 
                a.achievement_name,
                a.badge_icon,
                ua.unlocked_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.achievement_id
            WHERE ua.user_id = ?
            ORDER BY ua.unlocked_at DESC
            LIMIT ?
        ''', (user_id, limit // 2)).fetchall()
        
        for ach in achievements:
            activities.append({
                "type": "achievement",
                "message": f"Unlocked {ach['badge_icon']} {ach['achievement_name']}",
                "timestamp": ach['unlocked_at'],
                "icon": "🎉"
            })
        
        # User's topic mastery
        mastery = db.cursor.execute('''
            SELECT 
                topic_id,
                mastery,
                updated_at
            FROM user_progress
            WHERE user_id = ? AND mastery >= 0.8
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (user_id, limit // 2)).fetchall()
        
        for m in mastery:
            activities.append({
                "type": "mastery",
                "message": f"Mastered {m['topic_id']} ({int(m['mastery'] * 100)}%)",
                "timestamp": m['updated_at'],
                "icon": "🏆"
            })
        
        # Sort by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return activities[:limit]
        
    finally:
        db.disconnect()


def get_milestone_notifications(user_id):
    """
    Get pending milestone notifications for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of milestone notifications
    """
    db = get_db()
    notifications = []
    
    try:
        user = db.cursor.execute(
            'SELECT * FROM users WHERE user_id = ?', (user_id,)
        ).fetchone()
        
        if not user:
            return notifications
        
        # Check for streak milestones
        streak = user['study_streak']
        if streak > 0 and streak % 7 == 0:
            notifications.append({
                "type": "streak_milestone",
                "message": f"🔥 Amazing! You're on a {streak}-day streak!",
                "priority": "high"
            })
        
        # Check for XP milestones
        total_xp = user['total_xp']
        if total_xp > 0 and total_xp % 1000 == 0:
            notifications.append({
                "type": "xp_milestone",
                "message": f"⭐ You've earned {total_xp} total XP!",
                "priority": "medium"
            })
        
        # Check for questions answered milestones
        total_questions = db.cursor.execute('''
            SELECT SUM(attempts) as total FROM user_progress WHERE user_id = ?
        ''', (user_id,)).fetchone()
        
        if total_questions and total_questions['total']:
            total = total_questions['total']
            if total > 0 and total % 50 == 0:
                notifications.append({
                    "type": "questions_milestone",
                    "message": f"📚 You've answered {total} questions!",
                    "priority": "medium"
                })
        
        return notifications
        
    finally:
        db.disconnect()


def get_social_proof_data():
    """
    Get social proof statistics for display.
    
    Returns:
        Dictionary with social proof data
    """
    db = get_db()
    
    try:
        # Total users
        total_users = db.cursor.execute(
            'SELECT COUNT(*) as count FROM users'
        ).fetchone()
        
        # Active users (logged in within 30 minutes)
        active_users = db.cursor.execute('''
            SELECT COUNT(*) as count FROM users 
            WHERE last_login >= datetime('now', '-30 minutes')
        ''').fetchone()
        
        # Questions answered today
        questions_today = db.cursor.execute('''
            SELECT COUNT(*) as count FROM attempt_history
            WHERE timestamp >= datetime('now', 'start of day')
        ''').fetchone()
        
        # Current study streaks
        avg_streak = db.cursor.execute('''
            SELECT AVG(study_streak) as avg FROM users WHERE study_streak > 0
        ''').fetchone()
        
        return {
            "total_users": total_users['count'] if total_users else 0,
            "active_now": active_users['count'] if active_users else 0,
            "questions_today": questions_today['count'] if questions_today else 0,
            "average_streak": round(avg_streak['avg'], 1) if avg_streak and avg_streak['avg'] else 0
        }
        
    finally:
        db.disconnect()


def get_competitive_notifications(user_id):
    """
    Get competitive notifications (rank changes, etc.).
    
    Args:
        user_id: User ID
    
    Returns:
        List of competitive notifications
    """
    # Placeholder - would need historical rank tracking
    notifications = []
    
    # For now, return sample notification structure
    # In production, this would compare current rank to previous rank
    
    return notifications

