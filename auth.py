"""
Authentication Module for Learning App
User registration, login, and session management

Author: Veer Sanyal
Date: December 2025

Academic Integrity Statement:
This is original work for user authentication.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db
from datetime import datetime
import requests
import os


class User(UserMixin):
    """User class for flask-login."""
    
    def __init__(self, user_id, username, email, full_name, major, graduation_year, 
                 study_streak, total_xp, created_at, last_login):
        self.id = user_id
        self.username = username
        self.email = email
        self.full_name = full_name
        self.major = major
        self.graduation_year = graduation_year
        self.study_streak = study_streak
        self.total_xp = total_xp
        self.created_at = created_at
        self.last_login = last_login
    
    @staticmethod
    def get(user_id):
        """Get user by ID."""
        db = get_db()
        try:
            user_data = db.cursor.execute(
                'SELECT * FROM users WHERE user_id = ?', (user_id,)
            ).fetchone()
            
            if user_data:
                return User(
                    user_id=user_data['user_id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    major=user_data['major'],
                    graduation_year=user_data['graduation_year'],
                    study_streak=user_data['study_streak'],
                    total_xp=user_data['total_xp'],
                    created_at=user_data['created_at'],
                    last_login=user_data['last_login']
                )
            return None
        finally:
            db.disconnect()
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'user_id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'major': self.major,
            'graduation_year': self.graduation_year,
            'study_streak': self.study_streak,
            'total_xp': self.total_xp,
            'created_at': self.created_at,
            'last_login': self.last_login
        }


def register_user(username, password, email=None, full_name=None, major=None, graduation_year=None):
    """
    Register a new user.
    
    Args:
        username: Unique username
        password: Plain text password (will be hashed)
        email: Optional email address
        full_name: Optional full name
        major: Optional major
        graduation_year: Optional graduation year
    
    Returns:
        User object if successful, None if username exists
    """
    db = get_db()
    
    try:
        # Check if username already exists
        existing = db.cursor.execute(
            'SELECT user_id FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if existing:
            return None
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Insert new user
        db.cursor.execute('''
            INSERT INTO users (username, password_hash, email, full_name, major, graduation_year)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password_hash, email, full_name, major, graduation_year))
        
        db.conn.commit()
        
        # Get the created user
        user_id = db.cursor.lastrowid
        return User.get(user_id)
    
    except Exception as e:
        print(f"Error registering user: {e}")
        db.conn.rollback()
        return None
    finally:
        db.disconnect()


def login_user(username, password):
    """
    Authenticate user and return User object if successful.
    
    Args:
        username: Username
        password: Plain text password
    
    Returns:
        User object if successful, None otherwise
    """
    db = get_db()
    
    try:
        user_data = db.cursor.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if not user_data:
            return None
        
        # Check password
        if not check_password_hash(user_data['password_hash'], password):
            return None
        
        # Update last login
        db.cursor.execute(
            'UPDATE users SET last_login = ? WHERE user_id = ?',
            (datetime.now(), user_data['user_id'])
        )
        db.conn.commit()
        
        # Return User object
        return User(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            full_name=user_data['full_name'],
            major=user_data['major'],
            graduation_year=user_data['graduation_year'],
            study_streak=user_data['study_streak'],
            total_xp=user_data['total_xp'],
            created_at=user_data['created_at'],
            last_login=datetime.now()
        )
    
    except Exception as e:
        print(f"Error logging in user: {e}")
        return None
    finally:
        db.disconnect()


def get_user_by_username(username):
    """Get user by username."""
    db = get_db()
    
    try:
        user_data = db.cursor.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()
        
        if user_data:
            return User(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email'],
                full_name=user_data['full_name'],
                major=user_data['major'],
                graduation_year=user_data['graduation_year'],
                study_streak=user_data['study_streak'],
                total_xp=user_data['total_xp'],
                created_at=user_data['created_at'],
                last_login=user_data['last_login']
            )
        return None
    finally:
        db.disconnect()


def update_user_xp(user_id, xp_to_add):
    """
    Add XP to user's total.
    
    Args:
        user_id: User ID
        xp_to_add: Amount of XP to add
    """
    db = get_db()
    
    try:
        db.cursor.execute(
            'UPDATE users SET total_xp = total_xp + ? WHERE user_id = ?',
            (xp_to_add, user_id)
        )
        db.conn.commit()
    except Exception as e:
        print(f"Error updating user XP: {e}")
        db.conn.rollback()
    finally:
        db.disconnect()


def update_user_streak(user_id, new_streak):
    """
    Update user's study streak.
    
    Args:
        user_id: User ID
        new_streak: New streak value
    """
    db = get_db()
    
    try:
        db.cursor.execute(
            'UPDATE users SET study_streak = ? WHERE user_id = ?',
            (new_streak, user_id)
        )
        db.conn.commit()
    except Exception as e:
        print(f"Error updating user streak: {e}")
        db.conn.rollback()
    finally:
        db.disconnect()


def get_all_users_count():
    """Get total number of registered users."""
    db = get_db()
    
    try:
        result = db.cursor.execute('SELECT COUNT(*) as count FROM users').fetchone()
        return result['count'] if result else 0
    finally:
        db.disconnect()


def get_users_online_count():
    """
    Get count of users who have been active in last 30 minutes.
    
    Returns:
        Number of active users
    """
    db = get_db()
    
    try:
        # Users active in last 30 minutes
        result = db.cursor.execute('''
            SELECT COUNT(*) as count FROM users 
            WHERE last_login > datetime('now', '-30 minutes')
        ''').fetchone()
        
        return result['count'] if result else 0
    finally:
        db.disconnect()


def get_or_create_oauth_user(email, name, provider, provider_id):
    """
    Get existing user or create new user from OAuth provider.
    
    Args:
        email: User's email from OAuth provider
        name: User's name from OAuth provider
        provider: 'google'
        provider_id: Unique ID from OAuth provider
    
    Returns:
        User object
    """
    db = get_db()
    
    try:
        # Check if user exists by email
        user_data = db.cursor.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        
        if user_data:
            # Update last login
            db.cursor.execute(
                'UPDATE users SET last_login = ? WHERE user_id = ?',
                (datetime.now(), user_data['user_id'])
            )
            db.conn.commit()
            return User.get(user_data['user_id'])
        
        # Create new user
        # Generate username from email (before @)
        username = email.split('@')[0]
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while db.cursor.execute('SELECT user_id FROM users WHERE username = ?', (username,)).fetchone():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Insert new user (no password for OAuth users - use NULL)
        db.cursor.execute('''
            INSERT INTO users (username, email, full_name, password_hash, oauth_provider, oauth_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, email, name, None, provider, provider_id))
        
        db.conn.commit()
        user_id = db.cursor.lastrowid
        
        return User.get(user_id)
    
    except Exception as e:
        print(f"Error in get_or_create_oauth_user: {e}")
        db.conn.rollback()
        return None
    finally:
        db.disconnect()

