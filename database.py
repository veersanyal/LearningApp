"""
Database Module for Learning App
SQLite database schema for Phase 2 social features

Author: Veer Sanyal
Date: December 2025

Academic Integrity Statement:
This is original work for future multi-user features.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class Database:
    """Database manager for learning app with social features."""
    
    def __init__(self, db_path="learning_app.db"):
        """Initialize database connection."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Create all necessary tables for Phase 2 features."""
        
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                email TEXT UNIQUE,
                full_name TEXT,
                major TEXT,
                graduation_year INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                study_streak INTEGER DEFAULT 0,
                total_xp INTEGER DEFAULT 0,
                oauth_provider TEXT,
                oauth_id TEXT,
                UNIQUE(oauth_provider, oauth_id)
            )
        ''')
        
        # Add OAuth columns if they don't exist (migration)
        try:
            self.cursor.execute('ALTER TABLE users ADD COLUMN oauth_provider TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            self.cursor.execute('ALTER TABLE users ADD COLUMN oauth_id TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Add course_code column if it doesn't exist
        try:
            self.cursor.execute('ALTER TABLE users ADD COLUMN course_code TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # User progress table (replaces JSON file)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_id TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                correct INTEGER DEFAULT 0,
                mastery REAL DEFAULT 0.0,
                streak_correct INTEGER DEFAULT 0,
                streak_wrong INTEGER DEFAULT 0,
                last_reviewed TIMESTAMP,
                next_review TIMESTAMP,
                easiness_factor REAL DEFAULT 2.5,
                interval_days INTEGER DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, topic_id)
            )
        ''')
        
        # Attempt history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS attempt_history (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic_id TEXT NOT NULL,
                correct BOOLEAN NOT NULL,
                mastery_at_time REAL,
                retention REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Friendships table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS friendships (
                friendship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accepted_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (friend_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(user_id, friend_id)
            )
        ''')
        
        # Study groups table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                course_code TEXT,
                description TEXT,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Group members table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES study_groups(group_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                UNIQUE(group_id, user_id)
            )
        ''')
        
        # Shared questions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS shared_questions (
                share_id INTEGER PRIMARY KEY AUTOINCREMENT,
                shared_by INTEGER NOT NULL,
                topic_id TEXT NOT NULL,
                question_text TEXT NOT NULL,
                options TEXT NOT NULL,
                correct_answer INTEGER NOT NULL,
                explanation TEXT,
                difficulty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                likes_count INTEGER DEFAULT 0,
                FOREIGN KEY (shared_by) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Question attempts (for shared questions)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_attempts (
                attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                share_id INTEGER NOT NULL,
                correct BOOLEAN NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (share_id) REFERENCES shared_questions(share_id) ON DELETE CASCADE
            )
        ''')
        
        # Leaderboard table (denormalized for performance)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboards (
                leaderboard_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_code TEXT,
                time_period TEXT,
                total_xp INTEGER DEFAULT 0,
                questions_answered INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0.0,
                rank INTEGER,
                week_start DATE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Campus locations (for heat maps)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS campus_locations (
                location_id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_name TEXT UNIQUE NOT NULL,
                building_code TEXT,
                location_type TEXT,
                latitude REAL,
                longitude REAL
            )
        ''')
        
        # Study sessions (for campus heat map)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                location_id INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                questions_answered INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (location_id) REFERENCES campus_locations(location_id)
            )
        ''')
        
        # Achievements table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                achievement_name TEXT UNIQUE NOT NULL,
                description TEXT,
                badge_icon TEXT,
                xp_reward INTEGER DEFAULT 0,
                requirement_type TEXT,
                requirement_value TEXT
            )
        ''')
        
        # User achievements
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id) ON DELETE CASCADE,
                UNIQUE(user_id, achievement_id)
            )
        ''')
        
        # Exam prep plans
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_name TEXT NOT NULL,
                exam_date DATE NOT NULL,
                target_mastery REAL DEFAULT 0.80,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # User exam plans (for onboarding)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_exam_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                course_code TEXT,
                exam_date DATE,
                topic_confidence TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Exam plan topics
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_plan_topics (
                plan_topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                topic_id TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES exam_plans(plan_id) ON DELETE CASCADE
            )
        ''')
        
        # Documents table (for storing uploaded files)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                document_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                topics_extracted TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Exams table (for storing exam metadata)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                exam_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exam_name TEXT NOT NULL,
                exam_type TEXT,
                file_path TEXT,
                file_type TEXT,
                total_pages INTEGER,
                total_questions INTEGER,
                exam_date DATE,
                semester TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
        # Add metadata columns if they don't exist (migration)
        try:
            self.cursor.execute('ALTER TABLE exams ADD COLUMN exam_date DATE')
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        try:
            self.cursor.execute('ALTER TABLE exams ADD COLUMN semester TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Exam questions table (for storing OCR'd questions)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_questions (
                question_id INTEGER PRIMARY KEY AUTOINCREMENT,
                exam_id INTEGER NOT NULL,
                page_number INTEGER,
                question_number TEXT,
                raw_text TEXT NOT NULL,
                ocr_confidence REAL,
                image_path TEXT,
                diagram_note TEXT,
                solved_json TEXT,
                difficulty REAL,
                topics_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE
            )
        ''')
        
        # Exam question skills table (for normalized skills mapping)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS exam_question_skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                skill_name TEXT NOT NULL,
                skill_type TEXT,
                is_prerequisite BOOLEAN DEFAULT 0,
                FOREIGN KEY (question_id) REFERENCES exam_questions(question_id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
    
    def create_indexes(self):
        """Create indexes for better query performance."""
        
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_user_progress_topic ON user_progress(topic_id)',
            'CREATE INDEX IF NOT EXISTS idx_attempt_history_user ON attempt_history(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_attempt_history_timestamp ON attempt_history(timestamp)',
            'CREATE INDEX IF NOT EXISTS idx_friendships_user ON friendships(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_friendships_friend ON friendships(friend_id)',
            'CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id)',
            'CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_shared_questions_user ON shared_questions(shared_by)',
            'CREATE INDEX IF NOT EXISTS idx_leaderboards_course ON leaderboards(course_code)',
            'CREATE INDEX IF NOT EXISTS idx_leaderboards_period ON leaderboards(time_period)',
            'CREATE INDEX IF NOT EXISTS idx_study_sessions_user ON study_sessions(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_study_sessions_location ON study_sessions(location_id)',
            'CREATE INDEX IF NOT EXISTS idx_exams_user ON exams(user_id)',
            'CREATE INDEX IF NOT EXISTS idx_exam_questions_exam ON exam_questions(exam_id)',
            'CREATE INDEX IF NOT EXISTS idx_exam_question_skills_question ON exam_question_skills(question_id)'
        ]
        
        for index_sql in indexes:
            self.cursor.execute(index_sql)
        
        self.conn.commit()
    
    def insert_default_achievements(self):
        """Insert default achievements."""
        
        achievements = [
            ('First Step', 'Answer your first question', '🎯', 10, 'questions', '1'),
            ('Getting Started', 'Answer 10 questions', '📚', 50, 'questions', '10'),
            ('Centurion', 'Answer 100 questions', '💯', 200, 'questions', '100'),
            ('Week Warrior', 'Maintain a 7-day streak', '🔥', 100, 'streak', '7'),
            ('Unstoppable', 'Maintain a 30-day streak', '⚡', 500, 'streak', '30'),
            ('Perfect Ten', 'Get 10 questions correct in a row', '✨', 150, 'streak_correct', '10'),
            ('Topic Master', 'Achieve 100% mastery in a topic', '🏆', 300, 'mastery', '1.0'),
            ('Scholar', 'Master 5 topics', '📖', 500, 'mastered_topics', '5'),
            ('Social Butterfly', 'Add 5 friends', '👥', 100, 'friends', '5'),
            ('Team Player', 'Join a study group', '🤝', 50, 'groups', '1'),
            ('Early Bird', 'Study before 8 AM', '🌅', 75, 'time', 'early'),
            ('Night Owl', 'Study after 10 PM', '🦉', 75, 'time', 'late')
        ]
        
        for achievement in achievements:
            try:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO achievements 
                    (achievement_name, description, badge_icon, xp_reward, requirement_type, requirement_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', achievement)
            except sqlite3.IntegrityError:
                pass  # Achievement already exists
        
        self.conn.commit()
    
    def insert_default_locations(self):
        """Insert default Purdue campus locations."""
        
        locations = [
            ('WALC', 'WALC', 'library', 40.4274, -86.9163),
            ('HSSE Library', 'HSSE', 'library', 40.4258, -86.9216),
            ('Krannert', 'KRAN', 'building', 40.4263, -86.9201),
            ('Lawson', 'LWSN', 'building', 40.4283, -86.9165),
            ('PMU', 'PMU', 'student_center', 40.4237, -86.9212),
            ('Marriott', 'MRRTT', 'library', 40.4272, -86.9209),
            ('Beering Hall', 'BRNG', 'building', 40.4273, -86.9250),
            ('Stewart Center', 'STEW', 'building', 40.4245, -86.9223)
        ]
        
        for location in locations:
            try:
                self.cursor.execute('''
                    INSERT OR IGNORE INTO campus_locations
                    (location_name, building_code, location_type, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?)
                ''', location)
            except sqlite3.IntegrityError:
                pass  # Location already exists
        
        self.conn.commit()
    
    def migrate_json_progress_to_db(self, user_id: int, progress_file="user_progress.json"):
        """
        Migrate existing JSON progress data to database.
        
        Args:
            user_id: The user ID to associate with this progress
            progress_file: Path to the JSON progress file
        """
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            
            for topic_id, stats in progress_data.items():
                # Insert user progress
                self.cursor.execute('''
                    INSERT OR REPLACE INTO user_progress
                    (user_id, topic_id, attempts, correct, mastery, streak_correct, streak_wrong,
                     last_reviewed, next_review, easiness_factor, interval_days, review_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, topic_id, stats['attempts'], stats['correct'], stats['mastery'],
                    stats['streak_correct'], stats['streak_wrong'],
                    stats.get('last_reviewed'), stats.get('next_review'),
                    stats['easiness_factor'], stats['interval_days'], stats['review_count']
                ))
                
                # Insert attempt history
                for attempt in stats.get('attempt_history', []):
                    self.cursor.execute('''
                        INSERT INTO attempt_history
                        (user_id, topic_id, correct, mastery_at_time, retention, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, topic_id, attempt['correct'],
                        attempt['mastery_at_time'], attempt['retention'], attempt['timestamp']
                    ))
            
            self.conn.commit()
            return True
        except FileNotFoundError:
            print(f"Progress file {progress_file} not found")
            return False
        except Exception as e:
            print(f"Error migrating progress: {e}")
            self.conn.rollback()
            return False
    
    def initialize_database(self):
        """Initialize database with tables, indexes, and default data."""
        self.connect()
        self.create_tables()
        self.create_indexes()
        self.insert_default_achievements()
        self.insert_default_locations()
        self.conn.commit()
        print("Database initialized successfully!")


# Utility functions for database operations
def get_db():
    """Get database instance."""
    db = Database()
    db.connect()
    return db


def init_db():
    """Initialize the database."""
    db = Database()
    db.initialize_database()
    db.disconnect()


if __name__ == '__main__':
    # Initialize database when run directly
    print("Initializing database...")
    init_db()
    print("Database setup complete!")

