import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db, get_db
from exam_gemini import extract_exam_questions_with_gemini, save_exam_questions_to_db

# Load environment variables
load_dotenv()

def ensure_user_exists():
    """Ensure at least one user exists in the database to associate exams with."""
    db = get_db()
    try:
        # Check if any user exists
        db.cursor.execute("SELECT user_id FROM users LIMIT 1")
        user = db.cursor.fetchone()
        
        if user:
            print(f"Using existing user ID: {user['user_id']}")
            return user['user_id']
        else:
            print("No users found. Creating default admin user...")
            db.cursor.execute('''
                INSERT INTO users (username, password_hash, email, full_name, major, graduation_year)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('admin', 'hashed_password_placeholder', 'admin@example.com', 'Admin User', 'Computer Science', 2025))
            db.conn.commit()
            user_id = db.cursor.lastrowid
            print(f"Created default user with ID: {user_id}")
            return user_id
    finally:
        db.disconnect()

def main():
    # 1. Initialize Database
    try:
        init_db()
        print("Database initialized.")
    except Exception as e:
        print(f"Database initialization note: {e}")

    # 2. Configure Gemini
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return

    genai.configure(api_key=api_key)
    
    try:
        # Use existing model logic from app.py or direct
        vision_model = genai.GenerativeModel('gemini-2.0-flash-lite')
        print("Vision model initialized.")
    except Exception as e:
        print(f"Error initializing text model: {e}")
        return

    # 3. Process the Exam PDF
    pdf_filename = "MA161Exam1.php.pdf"
    if not os.path.exists(pdf_filename):
        print(f"Error: File {pdf_filename} not found.")
        return

    print(f"Reading {pdf_filename}...")
    with open(pdf_filename, 'rb') as f:
        file_bytes = f.read()

    # 4. Get User ID
    user_id = ensure_user_exists()

    # 5. Extract Questions
    print("Starting extraction (this may take a minute)...")
    result = extract_exam_questions_with_gemini(
        file_bytes=file_bytes, 
        file_type='pdf', 
        vision_model=vision_model
    )

    if "error" in result:
        print(f"Extraction failed: {result['error']}")
        return

    questions = result.get("questions", [])
    total_pages = result.get("total_pages", 0)
    print(f"Successfully extracted {len(questions)} questions from {total_pages} pages.")

    # 6. Save to Database
    if questions:
        print("Saving to database...")
        db_result = save_exam_questions_to_db(
            user_id=user_id,
            exam_name="MA161 Exam 1",
            file_type="pdf",
            questions_data=questions,
            total_pages=total_pages
        )
        print(f"Saved to DB! Exam ID: {db_result['exam_id']}")
    else:
        print("No questions found to save.")

if __name__ == "__main__":
    main()
