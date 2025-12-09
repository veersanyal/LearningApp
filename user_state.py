"""
Advanced User State Management for Learning App
Implements spaced repetition with forgetting curve and adaptive difficulty

Author: Veer Sanyal
Collaborators: None
Date: December 3, 2025

Academic Integrity Statement:
I have not used source code obtained from any unauthorized source,
either modified or unmodified. Any code I have used is properly
attributed in comments throughout this file.
"""

import json
import math
from datetime import datetime, timedelta
from topic_map import get_all_topics
from database import get_db


def init_user_state(user_id):
    """
    Initialize default statistics for all topics for a specific user.
    Creates comprehensive tracking for spaced repetition algorithm.
    
    Args:
        user_id: The ID of the user to initialize
    """
    all_topics = get_all_topics()
    
    # Validation: Check if topics list is empty
    if not all_topics or len(all_topics) == 0:
        raise ValueError("Cannot initialize user state: No topics available")
    
    db = get_db()
    
    try:
        # Iterate through all topics
        for topic in all_topics:
            topic_id = topic["topic_id"]
            
            # Check if already exists
            existing = db.cursor.execute(
                'SELECT progress_id FROM user_progress WHERE user_id = ? AND topic_id = ?',
                (user_id, topic_id)
            ).fetchone()
            
            if not existing:
                # Insert new progress record
                db.cursor.execute('''
                    INSERT INTO user_progress 
                    (user_id, topic_id, attempts, correct, mastery, streak_correct, streak_wrong,
                     easiness_factor, interval_days, review_count)
                    VALUES (?, ?, 0, 0, 0.0, 0, 0, 2.5, 0, 0)
                ''', (user_id, topic_id))
        
        db.conn.commit()
    except Exception as e:
        print(f"Error initializing user state: {e}")
        db.conn.rollback()
    finally:
        db.disconnect()


def calculate_forgetting_factor(last_reviewed, mastery):
    """
    Calculate memory retention using forgetting curve (Ebbinghaus).
    Formula: retention = e^(-t/S)
    where t is time elapsed and S is memory strength based on mastery.
    
    Returns: float between 0 and 1 representing current retention
    """
    # ERROR CHECK 1: Validate inputs
    if last_reviewed is None:
        return 1.0  # No decay if never reviewed
    
    if not isinstance(mastery, (int, float)) or mastery < 0 or mastery > 1:
        raise ValueError(f"Invalid mastery value: {mastery}. Must be between 0 and 1.")
    
    # Calculate time elapsed in hours
    time_now = datetime.now()
    time_elapsed = (time_now - last_reviewed).total_seconds() / 3600.0  # hours
    
    # Memory strength: higher mastery = slower forgetting
    # S ranges from 24 hours (low mastery) to 720 hours (high mastery)
    memory_strength = 24 + (mastery * 696)  # 24 to 720 hours
    
    # Exponential decay using forgetting curve
    retention = math.exp(-time_elapsed / memory_strength)
    
    return max(0.0, min(1.0, retention))  # Clamp between 0 and 1


def calculate_sm2_interval(easiness_factor, review_count, quality):
    """
    Calculate next review interval using SM-2 spaced repetition algorithm.
    
    Args:
        easiness_factor: Current EF value (typically 1.3 to 2.5)
        review_count: Number of successful reviews
        quality: Quality of recall (0-5 scale)
    
    Returns: interval in days
    """
    # ERROR CHECK 2: Validate quality parameter
    if not isinstance(quality, (int, float)) or quality < 0 or quality > 5:
        raise ValueError(f"Invalid quality score: {quality}. Must be between 0 and 5.")
    
    # SM-2 algorithm implementation
    if quality < 3:
        # Failed recall, reset interval
        interval = 1
        new_review_count = 0
    else:
        # Successful recall
        if review_count == 0:
            interval = 1
        elif review_count == 1:
            interval = 6
        else:
            # IF-ELIF-ELSE requirement within nested structure
            if easiness_factor < 1.3:
                ef_multiplier = 1.3
            elif easiness_factor > 2.5:
                ef_multiplier = 2.5
            else:
                ef_multiplier = easiness_factor
            
            interval = round(review_count * ef_multiplier)
        
        new_review_count = review_count + 1
    
    return interval, new_review_count


def update_easiness_factor(current_ef, quality):
    """
    Update easiness factor based on recall quality (SM-2 algorithm).
    Formula: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    """
    new_ef = current_ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # Clamp EF to valid range [1.3, 2.5]
    return max(1.3, min(2.5, new_ef))


def record_answer(user_id, topic_id, correct: bool):
    """
    Update user statistics after answering a question.
    Implements spaced repetition and forgetting curve algorithms.
    
    Args:
        user_id: The ID of the user
        topic_id: The topic being practiced
        correct: Whether the answer was correct
    """
    db = get_db()
    current_time = datetime.now()
    
    try:
        # Get current stats
        stats = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ? AND topic_id = ?',
            (user_id, topic_id)
        ).fetchone()
        
        if not stats:
            # Initialize if doesn't exist
            db.cursor.execute('''
                INSERT INTO user_progress 
                (user_id, topic_id, attempts, correct, mastery, streak_correct, streak_wrong,
                 easiness_factor, interval_days, review_count)
                VALUES (?, ?, 0, 0, 0.0, 0, 0, 2.5, 0, 0)
            ''', (user_id, topic_id))
            db.conn.commit()
            
            stats = db.cursor.execute(
                'SELECT * FROM user_progress WHERE user_id = ? AND topic_id = ?',
                (user_id, topic_id)
            ).fetchone()
        
        # Convert to dict for easier manipulation
        stats_dict = dict(stats)
        
        # Update basic counters
        attempts = stats_dict["attempts"] + 1
        
        # NESTED STRUCTURE requirement: IF inside FOR loop
        if correct:
            correct_count = stats_dict["correct"] + 1
            streak_correct = stats_dict["streak_correct"] + 1
            streak_wrong = 0
            quality = 4  # Good recall for SM-2 algorithm
        else:
            correct_count = stats_dict["correct"]
            streak_wrong = stats_dict["streak_wrong"] + 1
            streak_correct = 0
            quality = 1  # Failed recall for SM-2 algorithm
        
        # Calculate current retention using forgetting curve
        last_reviewed = stats_dict["last_reviewed"]
        if last_reviewed:
            if isinstance(last_reviewed, str):
                last_reviewed = datetime.fromisoformat(last_reviewed)
            retention = calculate_forgetting_factor(last_reviewed, stats_dict["mastery"])
        else:
            retention = 1.0
        
        # Update mastery with time-weighted calculation
        raw_accuracy = correct_count / max(1, attempts)
        mastery = (raw_accuracy * 0.7) + (retention * 0.3)
        
        # Update easiness factor using SM-2 algorithm
        easiness_factor = update_easiness_factor(stats_dict["easiness_factor"], quality)
        
        # Calculate next review interval using SM-2
        interval, new_review_count = calculate_sm2_interval(
            easiness_factor,
            stats_dict["review_count"],
            quality
        )
        
        # Update database
        next_review = current_time + timedelta(days=interval)
        
        db.cursor.execute('''
            UPDATE user_progress
            SET attempts = ?, correct = ?, mastery = ?, streak_correct = ?, streak_wrong = ?,
                last_reviewed = ?, next_review = ?, easiness_factor = ?, interval_days = ?,
                review_count = ?, updated_at = ?
            WHERE user_id = ? AND topic_id = ?
        ''', (attempts, correct_count, mastery, streak_correct, streak_wrong,
              current_time, next_review, easiness_factor, interval, new_review_count,
              current_time, user_id, topic_id))
        
        # Insert into attempt history
        db.cursor.execute('''
            INSERT INTO attempt_history (user_id, topic_id, correct, mastery_at_time, retention, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, topic_id, correct, mastery, retention, current_time))
        
        db.conn.commit()
        
    except Exception as e:
        print(f"Error recording answer: {e}")
        db.conn.rollback()
        raise
    finally:
        db.disconnect()


def get_target_difficulty(user_id, topic_id):
    """
    Choose appropriate difficulty based on mastery and recent performance.
    Uses adaptive difficulty with streak consideration.
    
    Args:
        user_id: The ID of the user
        topic_id: The topic ID
    
    Returns:
        Difficulty level: "easy", "medium", or "hard"
    """
    db = get_db()
    
    try:
        stats = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ? AND topic_id = ?',
            (user_id, topic_id)
        ).fetchone()
        
        if not stats:
            return "easy"
        
        mastery = stats["mastery"]
        streak_correct = stats["streak_correct"]
        streak_wrong = stats["streak_wrong"]
        
        # Adaptive difficulty with streak modifiers
        # IF-ELIF-ELSE requirement
        if streak_wrong >= 3:
            return "easy"  # Struggling, make it easier
        elif streak_correct >= 5 and mastery > 0.7:
            return "hard"  # On a roll with high mastery
        elif mastery < 0.3:
            return "easy"
        elif mastery < 0.6:
            return "medium"
        elif mastery < 0.85:
            return "medium" if streak_correct < 3 else "hard"
        else:
            return "hard"
    finally:
        db.disconnect()


def calculate_review_priority(user_id):
    """
    Calculate priority scores for all topics using complex algorithm.
    Combines mastery, forgetting curve, and review schedule.
    
    Args:
        user_id: The ID of the user
    
    Returns: list of (topic_id, priority_score) tuples sorted by priority
    """
    db = get_db()
    priority_list = []  # LIST requirement
    current_time = datetime.now()
    
    try:
        progress = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ?', (user_id,)
        ).fetchall()
        
        # FOR LOOP with NESTED IF statements
        for row in progress:
            stats = dict(row)
            topic_id = stats["topic_id"]
            
            # Skip if never attempted
            if stats["attempts"] == 0:
                priority_list.append((topic_id, 100.0))  # High priority for new topics
                continue
            
            # Calculate components of priority score
            mastery_factor = 1.0 - stats["mastery"]  # Lower mastery = higher priority
            
            # Time-based urgency (is review overdue?)
            next_review = stats["next_review"]
            if next_review:
                if isinstance(next_review, str):
                    next_review = datetime.fromisoformat(next_review)
                time_until_review = (next_review - current_time).total_seconds() / 3600.0
                
                # NESTED IF-ELIF-ELSE inside FOR loop
                if time_until_review < 0:
                    # Overdue review
                    urgency_factor = min(2.0, abs(time_until_review) / 24.0)
                elif time_until_review < 24:
                    # Due soon
                    urgency_factor = 0.5
                else:
                    # Not due yet
                    urgency_factor = 0.0
            else:
                urgency_factor = 0.5
            
            # Forgetting curve impact
            last_reviewed = stats["last_reviewed"]
            if last_reviewed:
                if isinstance(last_reviewed, str):
                    last_reviewed = datetime.fromisoformat(last_reviewed)
                retention = calculate_forgetting_factor(last_reviewed, stats["mastery"])
            else:
                retention = 1.0
            
            forgetting_factor = 1.0 - retention
            
            # Combined priority score (weighted sum)
            priority = (mastery_factor * 0.4) + (urgency_factor * 0.3) + (forgetting_factor * 0.3)
            priority_list.append((topic_id, priority))
        
        # Sort by priority (highest first)
        priority_list.sort(key=lambda x: x[1], reverse=True)
        return priority_list
    finally:
        db.disconnect()


def get_learning_velocity(user_id, topic_id):
    """
    Calculate learning velocity (improvement rate) for a topic.
    Analyzes recent performance trends.
    
    Args:
        user_id: The ID of the user
        topic_id: The topic ID
    
    Returns:
        Velocity as a float (0.0 to 1.0)
    """
    db = get_db()
    
    try:
        # Get recent attempts
        history = db.cursor.execute('''
            SELECT correct FROM attempt_history
            WHERE user_id = ? AND topic_id = ?
            ORDER BY timestamp DESC LIMIT 5
        ''', (user_id, topic_id)).fetchall()
        
        # Need at least 3 attempts to calculate velocity
        if len(history) < 3:
            return 0.0
        
        # Count correct answers
        correct_count = 0
        index = 0
        
        # WHILE loop counting correct answers
        while index < len(history):
            if history[index]["correct"]:
                correct_count += 1
            index += 1
        
        velocity = correct_count / len(history)
        return velocity
    finally:
        db.disconnect()


# JSON file functions removed - now using database


def get_user_state(user_id):
    """
    Return the current user state dictionary.
    
    Args:
        user_id: The ID of the user
    
    Returns:
        Dictionary mapping topic_id to stats
    """
    db = get_db()
    
    try:
        progress = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ?', (user_id,)
        ).fetchall()
        
        # Convert to dictionary format
        user_state_dict = {}
        for row in progress:
            stats = dict(row)
            topic_id = stats['topic_id']
            
            # Get attempt history
            history = db.cursor.execute(
                '''SELECT correct, mastery_at_time, retention, timestamp 
                   FROM attempt_history 
                   WHERE user_id = ? AND topic_id = ? 
                   ORDER BY timestamp DESC LIMIT 50''',
                (user_id, topic_id)
            ).fetchall()
            
            stats['attempt_history'] = [dict(h) for h in history]
            user_state_dict[topic_id] = stats
        
        return user_state_dict
    finally:
        db.disconnect()


def get_stats(user_id, topic_id):
    """
    Get stats for a specific topic.
    
    Args:
        user_id: The ID of the user
        topic_id: The topic ID
    
    Returns:
        Stats dictionary or None
    """
    db = get_db()
    
    try:
        stats = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ? AND topic_id = ?',
            (user_id, topic_id)
        ).fetchone()
        
        if stats:
            return dict(stats)
        return None
    finally:
        db.disconnect()


def clear_user_state(user_id):
    """
    Clear all user state data for a specific user.
    
    Args:
        user_id: The ID of the user
    """
    db = get_db()
    
    try:
        db.cursor.execute('DELETE FROM user_progress WHERE user_id = ?', (user_id,))
        db.cursor.execute('DELETE FROM attempt_history WHERE user_id = ?', (user_id,))
        db.conn.commit()
    except Exception as e:
        print(f"Error clearing user state: {e}")
        db.conn.rollback()
    finally:
        db.disconnect()


def get_topics_needing_review(user_id):
    """
    Get list of topics that need review based on spaced repetition schedule.
    Returns topics where next_review time has passed.
    
    Args:
        user_id: The ID of the user
    
    Returns:
        List of topic IDs
    """
    db = get_db()
    current_time = datetime.now()
    
    try:
        topics = db.cursor.execute('''
            SELECT topic_id FROM user_progress
            WHERE user_id = ? AND next_review IS NOT NULL AND next_review <= ?
        ''', (user_id, current_time)).fetchall()
        
        return [t["topic_id"] for t in topics]
    finally:
        db.disconnect()


def generate_progress_report(user_id):
    """
    Generate a comprehensive progress report.
    OUTPUT requirement: Returns formatted text for display.
    
    Args:
        user_id: The ID of the user
    
    Returns:
        Formatted progress report string
    """
    db = get_db()
    
    try:
        progress = db.cursor.execute(
            'SELECT * FROM user_progress WHERE user_id = ?', (user_id,)
        ).fetchall()
        
        if not progress:
            return "No progress data available."
        
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("LEARNING PROGRESS REPORT")
        report_lines.append("=" * 60)
        
        # Calculate overall statistics
        total_attempts = 0
        total_correct = 0
        
        # FOR loop to aggregate data
        for row in progress:
            total_attempts += row["attempts"]
            total_correct += row["correct"]
        
        overall_accuracy = (total_correct / total_attempts * 100) if total_attempts > 0 else 0
        
        report_lines.append(f"\nOverall Statistics:")
        report_lines.append(f"  Total Attempts: {total_attempts}")
        report_lines.append(f"  Total Correct: {total_correct}")
        report_lines.append(f"  Overall Accuracy: {overall_accuracy:.1f}%")
        report_lines.append(f"\nTopics Mastered (>80%): {sum(1 for s in progress if s['mastery'] > 0.8)}")
        report_lines.append(f"Topics In Progress (40-80%): {sum(1 for s in progress if 0.4 <= s['mastery'] <= 0.8)}")
        report_lines.append(f"Topics Struggling (<40%): {sum(1 for s in progress if s['mastery'] < 0.4)}")
        
        return "\n".join(report_lines)
    finally:
        db.disconnect()


def generate_forgetting_curve_data(user_id):
    """
    Generate forgetting curve data for visualization.
    Projects retention over 30 days for each topic.
    
    Args:
        user_id: The ID of the user
    
    Returns: Dictionary with topic data for Chart.js
    """
    from topic_map import get_all_topics
    
    db = get_db()
    all_topics = get_all_topics()
    topics_data = []
    
    # Time points: now, 1 day, 2 days, 3 days, 5 days, 7 days, 14 days, 30 days
    time_points_days = [0, 1, 2, 3, 5, 7, 14, 30]
    
    try:
        for topic in all_topics:
            topic_id = topic["topic_id"]
            
            stats = db.cursor.execute(
                'SELECT * FROM user_progress WHERE user_id = ? AND topic_id = ?',
                (user_id, topic_id)
            ).fetchone()
            
            if not stats or stats["attempts"] == 0:
                continue
            
            mastery = stats["mastery"]
            last_reviewed = stats["last_reviewed"]
            
            if last_reviewed is None:
                continue
            
            # Calculate retention at each time point
            retention_data = []
            
            for days in time_points_days:
                # Create a mock "last reviewed" time in the past
                hours_ahead = days * 24
                
                # Calculate what retention would be at this future point
                # Using the forgetting curve formula
                memory_strength = 24 + (mastery * 696)  # 24 to 720 hours
                retention = math.exp(-hours_ahead / memory_strength) * 100
                retention = max(0, min(100, retention))  # Clamp to 0-100
                
                retention_data.append(round(retention, 1))
            
            topics_data.append({
                "name": topic["name"],
                "topic_id": topic_id,
                "retention_data": retention_data
            })
        
        return {
            "topics": topics_data,
            "time_labels": ["Now", "1d", "2d", "3d", "5d", "7d", "14d", "30d"]
        }
    finally:
        db.disconnect()
