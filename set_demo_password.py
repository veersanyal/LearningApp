from werkzeug.security import generate_password_hash
from database import get_db, init_db

def set_demo_password():
    print("Setting demo password...")
    db = get_db()
    try:
        # Check if user exists
        user = db.cursor.execute("SELECT user_id FROM users WHERE username = 'veer.orgami'").fetchone()
        
        password = "password123"
        hashed = generate_password_hash(password)
        
        if user:
            print(f"Updating password for veer.orgami")
            db.cursor.execute("UPDATE users SET password_hash = ? WHERE username = 'veer.orgami'", (hashed,))
        else:
            print("Creating veer.orgami with password")
            db.cursor.execute('''
                INSERT INTO users (username, password_hash, full_name, email, major, graduation_year, total_xp, study_streak, course_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ('veer.orgami', hashed, 'Veer Sanyal', 'veer.orgami@purdue.edu', 'Computer Science', 2026, 1250, 5, 'CS 180'))
            
        db.conn.commit()
        print(f"Success! Login with: veer.orgami / {password}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    set_demo_password()
