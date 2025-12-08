"""
Leaderboard Module for Learning App
Multi-dimensional competitive rankings

Author: Veer Sanyal
Date: December 2025

Academic Integrity Statement:
This is original work for leaderboard features.
"""

from database import get_db
from datetime import datetime, timedelta


def calculate_leaderboard(leaderboard_type='global', filter_value=None, period='alltime', limit=100):
    """
    Calculate leaderboard rankings.
    
    Args:
        leaderboard_type: Type of leaderboard ('global', 'course', 'major', 'building')
        filter_value: Filter value for specific course/major/building
        period: Time period ('week', 'month', 'alltime')
        limit: Number of users to return
    
    Returns:
        List of ranked users with stats
    """
    db = get_db()
    
    try:
        # Build query based on type and period
        base_query = '''
            SELECT 
                u.user_id,
                u.username,
                u.full_name,
                u.major,
                u.total_xp,
                u.study_streak,
                COUNT(DISTINCT up.topic_id) as topics_studied,
                SUM(up.attempts) as total_questions,
                SUM(up.correct) as total_correct
            FROM users u
            LEFT JOIN user_progress up ON u.user_id = up.user_id
        '''
        
        conditions = []
        params = []
        
        # Filter by type
        if leaderboard_type == 'course' and filter_value:
            # For course-specific, we'd need to track which courses users are in
            # For now, this is a placeholder
            pass
        elif leaderboard_type == 'major' and filter_value:
            conditions.append('u.major = ?')
            params.append(filter_value)
        elif leaderboard_type == 'building' and filter_value:
            # Would need check-in data from study_sessions table
            pass
        
        # Filter by period
        if period == 'week':
            conditions.append('up.updated_at >= datetime("now", "-7 days")')
        elif period == 'month':
            conditions.append('up.updated_at >= datetime("now", "-30 days")')
        
        # Add conditions to query
        if conditions:
            base_query += ' WHERE ' + ' AND '.join(conditions)
        
        base_query += '''
            GROUP BY u.user_id
            ORDER BY u.total_xp DESC
            LIMIT ?
        '''
        params.append(limit)
        
        results = db.cursor.execute(base_query, params).fetchall()
        
        # Add rankings
        leaderboard = []
        for i, row in enumerate(results, 1):
            user_data = dict(row)
            user_data['rank'] = i
            user_data['accuracy'] = (
                (user_data['total_correct'] / user_data['total_questions'] * 100)
                if user_data['total_questions'] > 0 else 0
            )
            leaderboard.append(user_data)
        
        return leaderboard
        
    finally:
        db.disconnect()


def get_user_rank(user_id, leaderboard_type='global', filter_value=None, period='alltime'):
    """
    Get a specific user's rank and nearby users.
    
    Args:
        user_id: User ID to find
        leaderboard_type: Type of leaderboard
        filter_value: Filter value
        period: Time period
    
    Returns:
        Dictionary with user's rank and nearby users
    """
    # Get full leaderboard
    leaderboard = calculate_leaderboard(leaderboard_type, filter_value, period, limit=1000)
    
    # Find user's position
    user_rank_data = None
    user_position = None
    
    for i, user in enumerate(leaderboard):
        if user['user_id'] == user_id:
            user_rank_data = user
            user_position = i
            break
    
    if not user_rank_data:
        return {
            "user_rank": None,
            "nearby_users": [],
            "total_users": len(leaderboard)
        }
    
    # Get nearby users (5 above and 5 below)
    start_idx = max(0, user_position - 5)
    end_idx = min(len(leaderboard), user_position + 6)
    nearby_users = leaderboard[start_idx:end_idx]
    
    return {
        "user_rank": user_rank_data,
        "nearby_users": nearby_users,
        "total_users": len(leaderboard)
    }


def calculate_weekly_xp(user_id):
    """
    Calculate XP earned in the last 7 days.
    
    Args:
        user_id: User ID
    
    Returns:
        Weekly XP total
    """
    db = get_db()
    
    try:
        # Get attempt history from last 7 days
        attempts = db.cursor.execute('''
            SELECT COUNT(*) as count
            FROM attempt_history
            WHERE user_id = ? AND correct = 1 AND timestamp >= datetime('now', '-7 days')
        ''', (user_id,)).fetchone()
        
        # Rough estimate: 10 XP per correct answer on average
        weekly_xp = attempts['count'] * 10 if attempts else 0
        
        return weekly_xp
        
    finally:
        db.disconnect()


def get_course_statistics(course_code):
    """
    Get statistics for a specific course.
    
    Args:
        course_code: Course code (e.g., "CS 180")
    
    Returns:
        Dictionary with course stats
    """
    db = get_db()
    
    try:
        # This is a placeholder - would need course tracking in database
        # For now, return mock data structure
        
        total_students = db.cursor.execute('SELECT COUNT(*) as count FROM users').fetchone()
        
        avg_streak = db.cursor.execute('''
            SELECT AVG(study_streak) as avg_streak FROM users
        ''').fetchone()
        
        return {
            "course_code": course_code,
            "total_students": total_students['count'] if total_students else 0,
            "average_streak": round(avg_streak['avg_streak'], 1) if avg_streak and avg_streak['avg_streak'] else 0,
            "most_practiced_topic": "Arrays & Loops",  # Placeholder
            "class_average_mastery": 72  # Placeholder
        }
        
    finally:
        db.disconnect()


def update_leaderboard_cache():
    """
    Update denormalized leaderboard data for performance.
    This should be run periodically (e.g., every 5 minutes).
    
    For Phase 2, we're calculating on-demand. In production, this would
    populate the leaderboards table for faster queries.
    """
    db = get_db()
    
    try:
        # Get current week start (Monday)
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Clear existing week's leaderboard cache
        db.cursor.execute('''
            DELETE FROM leaderboards 
            WHERE time_period = 'week' AND week_start = ?
        ''', (week_start.date(),))
        
        # Calculate global weekly leaderboard
        weekly_users = db.cursor.execute('''
            SELECT 
                u.user_id,
                u.total_xp,
                COUNT(ah.attempt_id) as questions_answered,
                SUM(CASE WHEN ah.correct = 1 THEN 1 ELSE 0 END) as correct_answers
            FROM users u
            LEFT JOIN attempt_history ah ON u.user_id = ah.user_id 
                AND ah.timestamp >= ?
            GROUP BY u.user_id
            ORDER BY questions_answered DESC
        ''', (week_start,)).fetchall()
        
        # Insert into leaderboards table
        for rank, user in enumerate(weekly_users, 1):
            accuracy = (user['correct_answers'] / user['questions_answered'] * 100) if user['questions_answered'] > 0 else 0
            
            db.cursor.execute('''
                INSERT INTO leaderboards 
                (user_id, time_period, total_xp, questions_answered, accuracy, rank, week_start)
                VALUES (?, 'week', ?, ?, ?, ?, ?)
            ''', (user['user_id'], user['total_xp'], user['questions_answered'], 
                  accuracy, rank, week_start.date()))
        
        db.conn.commit()
        
    except Exception as e:
        print(f"Error updating leaderboard cache: {e}")
        db.conn.rollback()
    finally:
        db.disconnect()


def get_all_leaderboard_types():
    """
    Get available leaderboard types and filters.
    
    Returns:
        Dictionary with leaderboard configuration
    """
    db = get_db()
    
    try:
        # Get unique majors
        majors = db.cursor.execute('''
            SELECT DISTINCT major FROM users WHERE major IS NOT NULL
        ''').fetchall()
        
        # Get unique buildings from locations
        buildings = db.cursor.execute('''
            SELECT location_name FROM campus_locations
        ''').fetchall()
        
        return {
            "types": [
                {"id": "global", "name": "Global", "requires_filter": False},
                {"id": "course", "name": "By Course", "requires_filter": True},
                {"id": "major", "name": "By Major", "requires_filter": True},
                {"id": "building", "name": "By Building", "requires_filter": True}
            ],
            "periods": [
                {"id": "week", "name": "This Week"},
                {"id": "month", "name": "This Month"},
                {"id": "alltime", "name": "All Time"}
            ],
            "majors": [m['major'] for m in majors if m['major']],
            "buildings": [b['location_name'] for b in buildings]
        }
        
    finally:
        db.disconnect()


def get_rank_change(user_id, leaderboard_type='global'):
    """
    Get user's rank change compared to yesterday.
    
    Args:
        user_id: User ID
        leaderboard_type: Type of leaderboard
    
    Returns:
        Rank change (positive = moved up, negative = moved down)
    """
    # Placeholder - would need historical leaderboard snapshots
    # For now, return 0 (no change)
    return 0

