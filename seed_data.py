
import sqlite3
import random
import time
from datetime import datetime, timedelta
import uuid

# Database path
DB_PATH = 'learning_app.db'

# Sample Data
MAJORS = ['Computer Science', 'Data Science', 'Engineering', 'Mathematics', 'Physics', 'Biology', 'Chemistry', 'Business', 'Liberal Arts']
FIRST_NAMES = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Jamie', 'Quinn', 'Avery', 'Skyler', 'Charlie', 'Sam', 'Peyton', 'Reese', 'Dakota', 'Cameron', 'Sage', 'Rowan', 'Sawyer', 'Emerson']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin']
TOPICS = ['calculus_1', 'linear_algebra', 'physics_mechanics', 'intro_cs', 'chemistry_101', 'biology_101', 'macroeconomics', 'psychology_101']
LOCATIONS = [
    ('WALC', 'WALC', 'library', 40.4274, -86.9163),
    ('HSSE Library', 'HSSE', 'library', 40.4258, -86.9216),
    ('Krannert', 'KRAN', 'building', 40.4263, -86.9201),
    ('Lawson', 'LWSN', 'building', 40.4283, -86.9165),
    ('PMU', 'PMU', 'student_center', 40.4237, -86.9212),
    ('Marriott', 'MRRTT', 'library', 40.4272, -86.9209),
    ('Beering Hall', 'BRNG', 'building', 40.4273, -86.9250),
    ('Stewart Center', 'STEW', 'building', 40.4245, -86.9223)
]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def seed_locations(cursor):
    print("Seeding locations...")
    for loc in LOCATIONS:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO campus_locations 
                (location_name, building_code, location_type, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
            ''', loc)
        except Exception as e:
            print(f"Error seeding location {loc[0]}: {e}")

def seed_users(cursor, count=50):
    print(f"Seeding {count} users...")
    user_ids = []
    
    # Get existing users to avoid duplicates
    cursor.execute("SELECT username FROM users")
    existing_users = set(row[0] for row in cursor.fetchall())
    
    for _ in range(count):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        username = f"{fname.lower()}{lname.lower()}{random.randint(1, 999)}"
        
        if username in existing_users:
            continue
            
        full_name = f"{fname} {lname}"
        major = random.choice(MAJORS)
        grad_year = 2025 + random.randint(0, 3)
        total_xp = random.randint(50, 5000)
        study_streak = random.randint(0, 30)
        
        if random.random() < 0.2: # High achiever
            total_xp += 5000
            study_streak += 20
            
        cursor.execute('''
            INSERT INTO users (username, full_name, major, graduation_year, total_xp, study_streak, course_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, full_name, major, grad_year, total_xp, study_streak, 'CS 180'))
        
        user_ids.append(cursor.lastrowid)
        existing_users.add(username)
        
    return user_ids

def seed_progress(cursor, user_ids):
    print("Seeding user progress...")
    for user_id in user_ids:
        # Each user studies 2-5 topics
        num_topics = random.randint(2, 5)
        user_topics = random.sample(TOPICS, num_topics)
        
        for topic in user_topics:
            attempts = random.randint(5, 50)
            correct = int(attempts * random.uniform(0.4, 0.95))
            mastery = random.uniform(0.1, 1.0)
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_progress 
                (user_id, topic_id, attempts, correct, mastery, last_reviewed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, topic, attempts, correct, mastery, datetime.now()))
            
            # Add to leaderboard/cache table if it exists or we can rely on dynamic calc
            # For now, just ensuring user_progress is enough for calculate_leaderboard

def seed_study_sessions(cursor, user_ids):
    print("Seeding study sessions (heatmap)...")
    
    # Get location IDs
    cursor.execute("SELECT location_id FROM campus_locations")
    location_ids = [row[0] for row in cursor.fetchall()]
    
    if not location_ids:
        print("No locations found! Run seed_locations first.")
        return

    # Create active sessions (last 2 hours)
    now = datetime.now()
    
    for user_id in user_ids:
        # 30% chance a user is currently studying
        if random.random() < 0.3:
            loc_id = random.choice(location_ids)
            start_time = now - timedelta(minutes=random.randint(10, 120))
            
            cursor.execute('''
                INSERT INTO study_sessions (user_id, location_id, start_time)
                VALUES (?, ?, ?)
            ''', (user_id, loc_id, start_time))

def seed_retention_history(cursor, user_ids):
    print("Seeding retention history...")
    for user_id in user_ids:
        # Generate last 14 days of history
        base_retention = random.uniform(0.6, 0.9)
        for i in range(14):
            day_offset = 14 - i
            date = datetime.now() - timedelta(days=day_offset)
            
            # Simulate a natural curve with some noise
            # Retention starts high, decays, bumps up on review
            daily_retention = base_retention * (0.8 + (random.random() * 0.4)) 
            daily_retention = min(0.99, max(0.1, daily_retention))
            
            # Create a fake attempt to log this retention
            cursor.execute('''
                INSERT INTO attempt_history 
                (user_id, topic_id, correct, mastery_at_time, retention, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, 'fake_topic', True, 0.8, daily_retention, date))

def main():
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        seed_locations(cursor)
        conn.commit()
        
        users = seed_users(cursor, 50)
        conn.commit()
        
        seed_progress(cursor, users)
        conn.commit()
        
        seed_progress(cursor, users)
        conn.commit()
        
        seed_study_sessions(cursor, users)
        conn.commit()

        seed_retention_history(cursor, users)
        conn.commit()

        # Seed data for specific demo user 'veer.orgami' if not exists
        print("Seeding demo user 'veer.orgami'...")
        cursor.execute("SELECT user_id FROM users WHERE username = 'veer.orgami'")
        demo_user = cursor.fetchone()
        
        if demo_user:
            demo_user_id = demo_user[0]
            print(f"Found demo user (ID: {demo_user_id})")
        else:
            print("Demo user 'veer.orgami' not found. Creating...")
            cursor.execute('''
                INSERT INTO users (username, full_name, email, major, graduation_year, total_xp, study_streak)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ('veer.orgami', 'Veer Sanyal', 'veer.orgami@purdue.edu', 'Computer Science', 2026, 1250, 5))
            demo_user_id = cursor.lastrowid
            
        # Ensure demo user has history
        seed_retention_history(cursor, [demo_user_id])
        seed_progress(cursor, [demo_user_id])
        conn.commit()

        # Update leaderboard cache
        print("Updating leaderboard cache...")
        from leaderboards import update_leaderboard_cache
        update_leaderboard_cache()
        
        print("Seeding complete!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
