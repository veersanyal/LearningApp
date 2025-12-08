"""
Challenge System Module for Learning App
Direct challenges and question sharing

Author: Veer Sanyal
Date: December 2025

Academic Integrity Statement:
This is original work for challenge features.
"""

from database import get_db
from datetime import datetime
import secrets
import string


def generate_challenge_link():
    """
    Generate a unique challenge link code.
    
    Returns:
        6-character alphanumeric code
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))


def create_direct_challenge(challenger_id, challenged_id, question_data):
    """
    Create a direct challenge to another user.
    
    Args:
        challenger_id: User creating the challenge
        challenged_id: User being challenged (can be None for link-based)
        question_data: Dictionary with question details
    
    Returns:
        Challenge ID and link if applicable
    """
    db = get_db()
    
    try:
        # First, save the question to shared_questions
        db.cursor.execute('''
            INSERT INTO shared_questions 
            (shared_by, topic_id, question_text, options, correct_answer, explanation, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            challenger_id,
            question_data.get('topic_id'),
            question_data.get('question'),
            str(question_data.get('options')),  # Store as JSON string
            question_data.get('correct_answer'),
            question_data.get('explanation'),
            question_data.get('difficulty')
        ))
        
        share_id = db.cursor.lastrowid
        
        # Generate challenge link if no specific user targeted
        challenge_link = generate_challenge_link() if not challenged_id else None
        
        # Create challenge record
        db.cursor.execute('''
            INSERT INTO challenges 
            (challenger_id, challenged_id, share_id, challenge_link, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (challenger_id, challenged_id, share_id, challenge_link))
        
        challenge_id = db.cursor.lastrowid
        
        db.conn.commit()
        
        return {
            "challenge_id": challenge_id,
            "challenge_link": challenge_link,
            "share_id": share_id
        }
        
    except Exception as e:
        print(f"Error creating challenge: {e}")
        db.conn.rollback()
        return None
    finally:
        db.disconnect()


def get_challenge_by_link(challenge_link):
    """
    Get challenge details by link code.
    
    Args:
        challenge_link: 6-character challenge code
    
    Returns:
        Challenge data or None
    """
    db = get_db()
    
    try:
        challenge = db.cursor.execute('''
            SELECT c.*, sq.*,  u.username as challenger_username
            FROM challenges c
            JOIN shared_questions sq ON c.share_id = sq.share_id
            JOIN users u ON c.challenger_id = u.user_id
            WHERE c.challenge_link = ?
        ''', (challenge_link,)).fetchone()
        
        if challenge:
            return dict(challenge)
        return None
        
    finally:
        db.disconnect()


def get_received_challenges(user_id):
    """
    Get challenges sent to a user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of pending challenges
    """
    db = get_db()
    
    try:
        challenges = db.cursor.execute('''
            SELECT 
                c.*,
                sq.question_text,
                sq.topic_id,
                sq.difficulty,
                u.username as challenger_username
            FROM challenges c
            JOIN shared_questions sq ON c.share_id = sq.share_id
            JOIN users u ON c.challenger_id = u.user_id
            WHERE c.challenged_id = ? AND c.status = 'pending'
            ORDER BY c.created_at DESC
        ''', (user_id,)).fetchall()
        
        return [dict(c) for c in challenges]
        
    finally:
        db.disconnect()


def accept_challenge(challenge_id, user_id):
    """
    Accept a challenge.
    
    Args:
        challenge_id: Challenge ID
        user_id: User accepting
    
    Returns:
        Challenge question data
    """
    db = get_db()
    
    try:
        # Get challenge
        challenge = db.cursor.execute('''
            SELECT c.*, sq.*
            FROM challenges c
            JOIN shared_questions sq ON c.share_id = sq.share_id
            WHERE c.challenge_id = ?
        ''', (challenge_id,)).fetchone()
        
        if not challenge:
            return None
        
        # Update status
        db.cursor.execute('''
            UPDATE challenges SET status = 'accepted' WHERE challenge_id = ?
        ''', (challenge_id,))
        
        db.conn.commit()
        
        # Return question data
        import json
        return {
            "challenge_id": challenge['challenge_id'],
            "question": challenge['question_text'],
            "options": eval(challenge['options']),  # Convert string back to list
            "correct_answer": challenge['correct_answer'],
            "explanation": challenge['explanation'],
            "difficulty": challenge['difficulty'],
            "topic_id": challenge['topic_id']
        }
        
    finally:
        db.disconnect()


def complete_challenge(challenge_id, user_id, is_correct):
    """
    Mark challenge as completed and record score.
    
    Args:
        challenge_id: Challenge ID
        user_id: User completing
        is_correct: Whether answer was correct
    
    Returns:
        Comparison results
    """
    db = get_db()
    
    try:
        # Get challenge
        challenge = db.cursor.execute(
            'SELECT * FROM challenges WHERE challenge_id = ?', (challenge_id,)
        ).fetchone()
        
        if not challenge:
            return None
        
        # Determine if this is challenger or challenged
        is_challenger = (challenge['challenger_id'] == user_id)
        
        # Update appropriate score
        if is_challenger:
            db.cursor.execute('''
                UPDATE challenges 
                SET challenger_score = ?, status = 'completed'
                WHERE challenge_id = ?
            ''', (is_correct, challenge_id))
        else:
            db.cursor.execute('''
                UPDATE challenges 
                SET challenged_score = ?, status = 'completed', completed_at = ?
                WHERE challenge_id = ?
            ''', (is_correct, datetime.now(), challenge_id))
        
        # Record attempt
        db.cursor.execute('''
            INSERT INTO question_attempts (user_id, share_id, correct)
            VALUES (?, ?, ?)
        ''', (user_id, challenge['share_id'], is_correct))
        
        db.conn.commit()
        
        # Get updated challenge for comparison
        updated = db.cursor.execute(
            'SELECT * FROM challenges WHERE challenge_id = ?', (challenge_id,)
        ).fetchone()
        
        return {
            "challenge_id": challenge_id,
            "challenger_score": updated['challenger_score'],
            "challenged_score": updated['challenged_score'],
            "winner": determine_winner(updated)
        }
        
    except Exception as e:
        print(f"Error completing challenge: {e}")
        db.conn.rollback()
        return None
    finally:
        db.disconnect()


def determine_winner(challenge):
    """
    Determine challenge winner.
    
    Args:
        challenge: Challenge record
    
    Returns:
        'challenger', 'challenged', 'tie', or 'pending'
    """
    if challenge['challenger_score'] is None or challenge['challenged_score'] is None:
        return 'pending'
    
    if challenge['challenger_score'] == challenge['challenged_score']:
        return 'tie'
    
    if challenge['challenger_score']:
        return 'challenger'
    else:
        return 'challenged'


def submit_community_question(user_id, question_data):
    """
    Submit a question to the community pool.
    
    Args:
        user_id: User submitting
        question_data: Question details
    
    Returns:
        Question ID
    """
    db = get_db()
    
    try:
        db.cursor.execute('''
            INSERT INTO shared_questions 
            (shared_by, topic_id, question_text, options, correct_answer, explanation, difficulty)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            question_data.get('topic_id'),
            question_data.get('question'),
            str(question_data.get('options')),
            question_data.get('correct_answer'),
            question_data.get('explanation'),
            question_data.get('difficulty')
        ))
        
        question_id = db.cursor.lastrowid
        db.conn.commit()
        
        return question_id
        
    except Exception as e:
        print(f"Error submitting community question: {e}")
        db.conn.rollback()
        return None
    finally:
        db.disconnect()


def get_community_questions(course=None, topic=None, limit=20):
    """
    Browse community questions.
    
    Args:
        course: Filter by course code
        topic: Filter by topic ID
        limit: Maximum questions to return
    
    Returns:
        List of community questions
    """
    db = get_db()
    
    try:
        query = '''
            SELECT 
                sq.*,
                u.username as author,
                COUNT(DISTINCT qa.attempt_id) as attempt_count
            FROM shared_questions sq
            JOIN users u ON sq.shared_by = u.user_id
            LEFT JOIN question_attempts qa ON sq.share_id = qa.share_id
        '''
        
        conditions = []
        params = []
        
        if topic:
            conditions.append('sq.topic_id = ?')
            params.append(topic)
        
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        
        query += '''
            GROUP BY sq.share_id
            ORDER BY sq.created_at DESC, sq.likes_count DESC
            LIMIT ?
        '''
        params.append(limit)
        
        questions = db.cursor.execute(query, params).fetchall()
        
        return [dict(q) for q in questions]
        
    finally:
        db.disconnect()


def vote_community_question(user_id, question_id, vote_type):
    """
    Upvote or downvote a community question.
    
    Args:
        user_id: User voting
        question_id: Question ID
        vote_type: 'up' or 'down'
    
    Returns:
        New vote count
    """
    db = get_db()
    
    try:
        # For simplicity, just increment/decrement likes_count
        # In production, would track individual votes to prevent duplicates
        
        if vote_type == 'up':
            db.cursor.execute('''
                UPDATE shared_questions 
                SET likes_count = likes_count + 1
                WHERE share_id = ?
            ''', (question_id,))
        else:
            db.cursor.execute('''
                UPDATE shared_questions 
                SET likes_count = likes_count - 1
                WHERE share_id = ?
            ''', (question_id,))
        
        db.conn.commit()
        
        # Get new count
        result = db.cursor.execute(
            'SELECT likes_count FROM shared_questions WHERE share_id = ?',
            (question_id,)
        ).fetchone()
        
        return result['likes_count'] if result else 0
        
    except Exception as e:
        print(f"Error voting: {e}")
        db.conn.rollback()
        return None
    finally:
        db.disconnect()

