import os
import json
import re
import base64
import uuid
from datetime import datetime
from typing import Optional, Dict
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import google.generativeai as genai
from PyPDF2 import PdfReader
from PIL import Image
import io
import concurrent.futures
from dotenv import load_dotenv

from topic_map import load_topics_from_json, get_all_topics, topics
from user_state import (init_user_state, record_answer, get_target_difficulty, get_user_state, 
                        clear_user_state, generate_progress_report)
from question_picker import pick_next_topic, get_recommended_study_order
from learning_analytics import (calculate_study_streak, identify_weak_topics, 
                                 identify_strong_topics, export_analytics_report)
from auth import (User, register_user, login_user as auth_login_user, get_users_online_count, 
                  update_user_streak, get_or_create_oauth_user)
from database import init_db, get_db
from gamification import (calculate_xp, award_xp, check_achievements, get_user_achievements,
                          get_all_achievements_with_status, get_xp_progress)
from leaderboards import (calculate_leaderboard, get_user_rank, get_course_statistics,
                          get_all_leaderboard_types, calculate_weekly_xp)
from activity_feed import (get_recent_activity, get_user_activity_feed, get_milestone_notifications,
                           get_social_proof_data, get_competitive_notifications)
from challenges import (create_direct_challenge, get_challenge_by_link, get_received_challenges,
                       accept_challenge, complete_challenge, submit_community_question,
                       get_community_questions, vote_community_question)
from exam_ocr import process_exam_file
from exam_gemini import extract_exam_questions_with_gemini, save_exam_questions_to_db
from exam_gemini import extract_exam_questions_with_gemini, save_exam_questions_to_db

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure session to use permanent cookies
app.config['PERMANENT_SESSION_LIFETIME'] = 31 * 24 * 60 * 60  # 31 days in seconds
# Detect production environment (Railway sets RAILWAY_ENVIRONMENT or PORT)
is_production = os.getenv('RAILWAY_ENVIRONMENT') == 'production' or os.getenv('PORT') is not None
app.config['SESSION_COOKIE_SECURE'] = is_production  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# Configure flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'  # Redirect to index if not logged in
login_manager.remember_cookie_duration = 31 * 24 * 60 * 60  # 31 days

@login_manager.user_loader
def load_user(user_id):
    """Load user for flask-login."""
    return User.get(int(user_id))

# Initialize database on first run
try:
    init_db()
    print("Database initialized successfully")
except Exception as e:
    print(f"Database already initialized or error: {e}")

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY environment variable is not set. Some features may not work.")
    # Don't crash on startup - allow app to start but features will fail gracefully
else:
    genai.configure(api_key=GEMINI_API_KEY)

# Models - using gemini-2.5-flash-lite (only initialize if API key is set)
if GEMINI_API_KEY:
    try:
        text_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        vision_model = genai.GenerativeModel('gemini-2.5-flash-lite')
        print("Initialized models: gemini-2.5-flash-lite")
    except Exception as e:
        print(f"Error initializing gemini-2.5-flash-lite: {e}")
        # Fallback to gemini-2.0-flash-lite if 2.5-flash-lite is not available
        try:
            text_model = genai.GenerativeModel('gemini-2.0-flash-lite')
            vision_model = genai.GenerativeModel('gemini-2.0-flash-lite')
            print("Fell back to gemini-2.0-flash-lite")
        except Exception as e2:
            print(f"Error initializing fallback models: {e2}")
            text_model = None
            vision_model = None
else:
    text_model = None
    vision_model = None


def extract_text_from_pdf(file_bytes, skip_instruction_pages=True):
    """Extract text from a PDF file, optionally skipping instruction pages."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        total_pages = len(reader.pages)
        skipped_pages = 0
        
        for idx in range(total_pages):
            page = reader.pages[idx]
            page_text = page.extract_text() or ""
            
            # Skip instruction pages if enabled
            if skip_instruction_pages and page_text:
                if is_instruction_content(page_text):
                    print(f"[PDF] Page {idx + 1} appears to be instructions - skipping")
                    skipped_pages += 1
                    continue
            
            text += page_text + "\n\n"
        
        if not text or len(text.strip()) < 50:
            print("Warning: PDF extraction returned very little or no text")
        print(f"Extracted {len(text)} characters from PDF ({total_pages} pages, {skipped_pages} instruction pages skipped)")
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        import traceback
        traceback.print_exc()
        raise


def is_instruction_content(content: str) -> bool:
    """Check if content appears to be exam instructions rather than questions."""
    content_lower = content.lower()
    
    instruction_keywords = [
        'scantron', 'fill in', 'bubble', 'pencil', '#2 pencil',
        'ta name', 'course number', 'section number', 'student id',
        'exam instructions', 'exam rules', 'academic integrity',
        'prohibited', 'not allowed', 'do not', 'must bring',
        'exam format', 'total questions', 'point value', 'time limit',
        'leave the room', 'electronic devices', 'notes', 'calculator',
        'show your work', 'write clearly', 'good luck', 'exam submission'
    ]
    
    keyword_count = sum(1 for keyword in instruction_keywords if keyword in content_lower)
    return keyword_count >= 3


def extract_topics_from_content(content, is_image=False, image_bytes=None):
    """Use Gemini to extract topics from content."""
    # Skip instruction/logistics content
    if not is_image and content and is_instruction_content(content):
        print("[EXTRACT_TOPICS] Content appears to be exam instructions - skipping topic extraction")
        return {"topics": [], "error": "This appears to be exam instructions/logistics rather than actual questions. Please upload pages with actual exam questions."}
    
    prompt = """Analyze this content and extract the main topics that could be tested.
IMPORTANT: Focus ONLY on actual exam questions and mathematical/technical concepts. 
IGNORE exam instructions, logistics, formatting rules, or administrative content.

Return a JSON object with this exact structure:
{
  "topics": [
    {
      "topic_id": "subject.category.specific_topic",
      "name": "Human readable topic name",
      "explanation": "A clear 2-3 sentence explanation of this concept that would help a student understand what it is and why it matters.",
      "coverage": "introduced",
      "frequency_estimate": 2,
      "difficulty_profile": { "easy": 1, "medium": 1, "hard": 1 }
    }
  ]
}

IMPORTANT: 
- Only extract topics from actual questions, not from instructions
- Include a helpful "explanation" field for each topic
- If the content is only instructions/logistics, return an empty topics array
Only return the JSON, no other text."""

    try:
        print("[EXTRACT_TOPICS] Starting topic extraction")
        # Check if models are initialized
        if not text_model or not vision_model:
            print("[EXTRACT_TOPICS] Error: Models not initialized")
            return {"topics": [], "error": "AI service not configured. Please check GEMINI_API_KEY environment variable."}
        
        print("[EXTRACT_TOPICS] Models are initialized")
        
        # Validate input
        if not is_image and (not content or len(content.strip()) < 50):
            print(f"[EXTRACT_TOPICS] Error: Content too short or empty ({len(content) if content else 0} chars)")
            return {"topics": [], "error": "Content too short or empty. Please upload a document with more text."}
        
        if is_image and not image_bytes:
            print("[EXTRACT_TOPICS] Error: Image bytes not provided")
            return {"topics": [], "error": "Image data not provided."}
        
        # No truncation: use full content
        primary_max_chars = None

        def call_model(active_content):
            request_timeout = 12  # seconds to avoid worker timeouts

            def _do_call():
                if is_image and image_bytes:
                    image = Image.open(io.BytesIO(image_bytes))
                    print(f"[EXTRACT_TOPICS] Using vision model with timeout {request_timeout}s")
                    return vision_model.generate_content(
                        [prompt, image],
                        request_options={"timeout": request_timeout}
                    )
                else:
                    full_prompt = f"{prompt}\n\nContent:\n{active_content}"
                    print(f"[EXTRACT_TOPICS] Using text model (content length: {len(active_content)} chars) with timeout {request_timeout}s")
                    return text_model.generate_content(
                        full_prompt,
                        request_options={"timeout": request_timeout}
                    )

            # Enforce our own timeout to avoid hanging requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_do_call)
                try:
                    return future.result(timeout=request_timeout + 3)  # small buffer
                except concurrent.futures.TimeoutError:
                    print("[EXTRACT_TOPICS] ERROR: Model call timed out")
                    return {"topics": [], "error": "AI request timed out. Please try again with a smaller document."}

        try:
            response = call_model(content)
        except Exception as e:
            err_msg = str(e).lower()
            print(f"[EXTRACT_TOPICS] First attempt failed: {e}")
            # Retry once with aggressive truncation for text timeouts
            if (("timeout" in err_msg or "deadline" in err_msg or "504" in err_msg) and not is_image):
                fallback_chars = 2000
                short_content = content[:fallback_chars] + "\n\n[Content truncated further for retry...]"
                print(f"[EXTRACT_TOPICS] Retrying with shorter content ({len(short_content)} chars)")
                try:
                    response = call_model(short_content)
                except Exception as e2:
                    print(f"[EXTRACT_TOPICS] Retry failed: {e2}")
                    return {"topics": [], "error": f"AI timeout on retry: {e2}"}
            else:
                return {"topics": [], "error": f"AI request failed: {e}"}
        
        # Parse the response
        print("[EXTRACT_TOPICS] Parsing Gemini response...")
        if not response or not response.text:
            print("[EXTRACT_TOPICS] Error: Empty response from Gemini")
            return {"topics": [], "error": "Empty response from AI. Please try again."}
        
        response_text = response.text.strip()
        print(f"[EXTRACT_TOPICS] Gemini raw response (first 500 chars): {response_text[:500]}...")
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 2:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
        response_text = response_text.strip()
        
        print(f"Parsed JSON text (first 500 chars): {response_text[:500]}...")  # Debug log
        
        # Try to parse JSON
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as json_err:
            print(f"JSON parsing error: {json_err}")
            print(f"Full response text: {response_text}")
            # Try to extract JSON from the response if it's embedded in text
            import re
            json_match = re.search(r'\{[^{}]*"topics"[^{}]*\[.*?\]\s*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(0))
                    print("Successfully extracted JSON from embedded text")
                except:
                    return {"topics": [], "error": f"Failed to parse AI response as JSON. Response: {response_text[:200]}..."}
            else:
                return {"topics": [], "error": f"AI response was not valid JSON. Please try again or upload a different file."}
        
        topics_list = result.get('topics', [])
        print(f"Extracted {len(topics_list)} topics")  # Debug log
        
        if not topics_list:
            return {"topics": [], "error": "AI could not identify any topics in the document. Try uploading a document with clearer educational content."}
        
        return result
    except Exception as e:
        print(f"Error extracting topics: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        if "API key" in error_msg.lower():
            return {"topics": [], "error": "API key error. Please check your Gemini API key configuration."}
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return {"topics": [], "error": "API rate limit exceeded. Please try again in a moment."}
        else:
            return {"topics": [], "error": f"Error processing document: {error_msg}"}


def generate_question_for_topic(topic, difficulty):
    """Use Gemini to generate a question for a topic."""
    if not text_model:
        return None
    
    prompt = f"""Generate a {difficulty} difficulty multiple choice question about: {topic['name']}

Return ONLY this JSON structure:
{{
  "question": "Question text here",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_answer": 0,
  "explanation": "Brief explanation"
}}

CRITICAL FORMATTING:
- Every mathematical expression MUST be wrapped in dollar signs
- In JSON, backslashes must be doubled

EXAMPLE for a polar curves question:
{{
  "question": "Which equation represents a circle?",
  "options": ["$r = 3$", "$r = 3\\\\cos(\\\\theta)$", "$r = 3\\\\sin(\\\\theta)$", "$r = \\\\theta$"],
  "correct_answer": 0,
  "explanation": "$r = 3$ is a circle because..."
}}

Return ONLY valid JSON, no markdown, no explanation."""

    try:
        response = text_model.generate_content(prompt)
        response_text = response.text.strip()
        print(f"Question generation raw response: {response_text[:300]}...")  # Debug
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 2:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
        response_text = response_text.strip()
        
        # Try to parse JSON, with fallback escaping if needed
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Escape all backslashes and try again
            escaped_text = response_text.replace('\\', '\\\\')
            # Fix over-escaped ones (quadruple -> double)
            escaped_text = escaped_text.replace('\\\\\\\\', '\\\\')
            try:
                result = json.loads(escaped_text)
            except json.JSONDecodeError as e2:
                print(f"JSON parsing error after escaping: {e2}")
                print(f"Response text was: {escaped_text[:500]}")
                return None
        
        # Post-process to ensure LaTeX is properly formatted for MathJax
        # MathJax needs single backslashes in HTML, JSON parsing gives us that
        print(f"Question generated successfully for topic: {topic['name']}")  # Debug
        return result
    except Exception as e:
        print(f"Error generating question: {e}")
        import traceback
        traceback.print_exc()
        return None


@app.route('/')
def index():
    return render_template('index.html')


# Authentication Routes
@app.route('/auth/register', methods=['POST'])
def auth_register():
    """Register a new user."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    full_name = data.get('full_name')
    major = data.get('major')
    graduation_year = data.get('graduation_year')
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    # Validate username length
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    
    # Validate password length
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    user = register_user(username, password, email, full_name, major, graduation_year)
    
    if not user:
        return jsonify({"error": "Username already exists"}), 409
    
    # Get remember preference (default to True for better UX)
    remember = data.get('remember', True)
    
    # Auto-login after registration (remember parameter controls cookie persistence)
    login_user(user, remember=remember)
    
    return jsonify({
        "success": True,
        "message": "Registration successful",
        "user": user.to_dict()
    })


@app.route('/auth/login', methods=['POST'])
def auth_login():
    """Login user."""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', True)  # Default to True for better UX
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    user = auth_login_user(username, password)
    
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Login with flask-login (remember parameter controls cookie persistence)
    login_user(user, remember=remember)
    
    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": user.to_dict()
    })


@app.route('/auth/logout', methods=['POST'])
@login_required
def auth_logout():
    """Logout user."""
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully"})


@app.route('/auth/me', methods=['GET'])
@login_required
def auth_me():
    """Get current user info."""
    xp_progress = get_xp_progress(current_user.total_xp)
    
    return jsonify({
        "user": current_user.to_dict(),
        "users_online": get_users_online_count(),
        "xp_progress": xp_progress
    })


@app.route('/auth/google', methods=['POST'])
def auth_google():
    """Handle Google OAuth login."""
    data = request.json
    credential = data.get('credential')  # JWT token from Google
    
    if not credential:
        return jsonify({"error": "Google credential required"}), 400
    
    try:
        import jwt
        from jwt.algorithms import RSAAlgorithm
        
        # Decode the JWT token (without verification for now - in production verify with Google's public keys)
        # For production, you should verify the token signature
        decoded = jwt.decode(credential, options={"verify_signature": False})
        
        email = decoded.get('email')
        name = decoded.get('name', '')
        google_id = decoded.get('sub')  # Google user ID
        
        if not email:
            return jsonify({"error": "Email not provided by Google"}), 400
        
        # Get or create user
        user = get_or_create_oauth_user(email, name, 'google', google_id)
        
        if not user:
            return jsonify({"error": "Failed to create user"}), 500
        
        # Login user (always remember for OAuth logins)
        login_user(user, remember=True)
        
        return jsonify({
            "success": True,
            "message": "Google login successful",
            "user": user.to_dict()
        })
    
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/auth/config', methods=['GET'])
def auth_config():
    """Get OAuth configuration (client IDs)."""
    return jsonify({
        "google_client_id": os.getenv('GOOGLE_CLIENT_ID', '')
    })


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """Handle document upload and extract topics."""
    file_path = None
    try:
        print("[UPLOAD] ========== STARTING UPLOAD ==========")
        print(f"[UPLOAD] User ID: {current_user.id}")
        
    if 'file' not in request.files:
            print("[UPLOAD] ERROR: No file in request.files")
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
            print("[UPLOAD] ERROR: Empty filename")
        return jsonify({"error": "No file selected"}), 400
    
        original_filename = file.filename
        filename = original_filename.lower()
        print(f"[UPLOAD] Processing file: {original_filename} (lowercase: {filename})")
        
    file_bytes = file.read()
        file_size = len(file_bytes)
        print(f"[UPLOAD] File size: {file_size} bytes")

        # Enforce a hard file size limit to prevent timeouts (8 MB)
        max_file_size = 8 * 1024 * 1024
        if file_size > max_file_size:
            print(f"[UPLOAD] ERROR: File too large ({file_size} bytes). Limit is {max_file_size} bytes.")
            return jsonify({"error": "File too large. Please upload a file under 8 MB."}), 413
        
        # Check if models are initialized
        print(f"[UPLOAD] Checking models - text_model: {text_model is not None}, vision_model: {vision_model is not None}")
        if not text_model or not vision_model:
            print("[UPLOAD] ERROR: Models not initialized!")
            return jsonify({"error": "AI service not configured. Please check GEMINI_API_KEY environment variable."}), 500
        
        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads', str(current_user.id))
        print(f"[UPLOAD] Creating uploads directory: {uploads_dir}")
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate unique filename to avoid conflicts
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(uploads_dir, unique_filename)
        print(f"[UPLOAD] Generated file path: {file_path}")
        
        # Determine file type and extract topics
        topic_data = None
        print(f"[UPLOAD] File extension: {file_ext}")
        
        if filename.endswith('.pdf'):
            print("[UPLOAD] Processing as PDF")
            file_type = 'pdf'
            try:
                print("[UPLOAD] Step 1: Extracting text from PDF...")
            content = extract_text_from_pdf(file_bytes)
                print(f"[UPLOAD] Step 1 complete: Extracted {len(content)} characters")
                print("[UPLOAD] Step 2: Extracting topics from content...")
            topic_data = extract_topics_from_content(content)
                print(f"[UPLOAD] Step 2 complete: Got topic_data: {topic_data}")
            except Exception as e:
                print(f"[UPLOAD] EXCEPTION processing PDF: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": f"Error processing PDF: {str(e)}"}), 500
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            print("[UPLOAD] Processing as image")
            file_type = 'image'
            try:
                print("[UPLOAD] Extracting topics from image...")
            topic_data = extract_topics_from_content(None, is_image=True, image_bytes=file_bytes)
                print(f"[UPLOAD] Got topic_data: {topic_data}")
            except Exception as e:
                print(f"[UPLOAD] EXCEPTION processing image: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": f"Error processing image: {str(e)}"}), 500
        elif filename.endswith('.txt'):
            print("[UPLOAD] Processing as text file")
            file_type = 'text'
            try:
                print("[UPLOAD] Decoding text file...")
            content = file_bytes.decode('utf-8')
                print(f"[UPLOAD] Decoded {len(content)} characters")
                print("[UPLOAD] Extracting topics from content...")
            topic_data = extract_topics_from_content(content)
                print(f"[UPLOAD] Got topic_data: {topic_data}")
            except Exception as e:
                print(f"[UPLOAD] EXCEPTION processing text file: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": f"Error processing text file: {str(e)}"}), 500
        else:
            print(f"[UPLOAD] ERROR: Unsupported file type: {file_ext}")
            return jsonify({"error": "Unsupported file type"}), 400
        
        # Check if any topics were extracted
        if not topic_data or not topic_data.get("topics"):
            error_msg = topic_data.get("error", "No topics could be extracted from the document. Try a different file.") if topic_data else "Failed to extract topics from document."
            print(f"Topic extraction failed: {error_msg}")
            print(f"Topic data received: {topic_data}")
            return jsonify({"error": error_msg}), 400
        
        # Save file to disk
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        # Store document metadata in database
        db = get_db()
        try:
            topics_json = json.dumps(topic_data.get("topics", []))
            db.cursor.execute('''
                INSERT INTO documents (user_id, filename, file_path, file_type, file_size, topics_extracted)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (current_user.id, original_filename, file_path, file_type, file_size, topics_json))
            db.conn.commit()
            document_id = db.cursor.lastrowid
        finally:
            db.disconnect()
        
        # Clear existing topics and user state, then load new ones
        topics.clear()
        clear_user_state(current_user.id)
        load_topics_from_json(topic_data)
        init_user_state(current_user.id)
        
        all_topics = get_all_topics()
        print(f"Loaded {len(all_topics)} topics into memory")  # Debug log
        
        # Ensure we return a list, not None
        if not all_topics:
            all_topics = []
        
        return jsonify({
            "success": True,
            "topics": all_topics,
            "document_id": document_id
        })
    except Exception as e:
        # Clean up file if database insert failed
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        return jsonify({"error": str(e)}), 500


@app.route('/generate-question', methods=['POST'])
@login_required
def generate_question():
    """Generate a question for a topic (specific or auto-selected)."""
    all_topics = get_all_topics()
    
    if not all_topics:
        return jsonify({"error": "No topics loaded. Please upload a document first."}), 400
    
    try:
        # Check if a specific topic_id was requested
        data = request.json or {}
        requested_topic_id = data.get('topic_id')
        
        if requested_topic_id:
            # Use the specific topic requested
            topic_id = requested_topic_id
            topic = next((t for t in all_topics if t['topic_id'] == topic_id), None)
            if not topic:
                return jsonify({"error": f"Topic '{topic_id}' not found"}), 404
        else:
            # Pick the next topic automatically
            topic_id = pick_next_topic(current_user.id)
            topic = next((t for t in all_topics if t['topic_id'] == topic_id), None)
            if not topic:
                return jsonify({"error": "Topic not found"}), 404
        
        # Get appropriate difficulty
        difficulty = get_target_difficulty(current_user.id, topic_id)
        
        # Generate question using Gemini
        question_data = generate_question_for_topic(topic, difficulty)
        
        if not question_data:
            return jsonify({"error": "Failed to generate question"}), 500
        
        question_data['topic_id'] = topic_id
        question_data['topic_name'] = topic['name']
        question_data['difficulty'] = difficulty
        
        return jsonify(question_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    """Submit an answer and update user state."""
    data = request.json
    topic_id = data.get('topic_id')
    is_correct = data.get('is_correct', False)
    difficulty = data.get('difficulty', 'medium')
    time_taken = data.get('time_taken')  # Optional: time in seconds
    used_guide_me = data.get('used_guide_me', False)
    
    if not topic_id:
        return jsonify({"error": "No topic_id provided"}), 400
    
    try:
        # Record the answer
        record_answer(current_user.id, topic_id, is_correct)
        
        # Calculate and award XP if correct
        xp_result = None
        if is_correct:
            xp_earned = calculate_xp(
                difficulty=difficulty,
                is_correct=True,
                is_first_attempt=False,  # TODO: Track this
                time_taken=time_taken,
                used_guide_me=used_guide_me,
                user_streak=current_user.study_streak
            )
            
            xp_result = award_xp(current_user.id, xp_earned)
        
        # Check for newly earned achievements
        new_achievements = check_achievements(current_user.id)
        
        # Get updated user state
        user_state = get_user_state(current_user.id)
        
        # Get XP progress
        xp_progress = get_xp_progress(current_user.total_xp + (xp_result['xp_awarded'] if xp_result else 0))
        
        return jsonify({
            "success": True,
            "user_state": user_state,
            "xp_result": xp_result,
            "new_achievements": new_achievements,
            "xp_progress": xp_progress
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get current user stats."""
    return jsonify({
        "topics": get_all_topics(),
        "user_state": get_user_state(current_user.id)
    })


@app.route('/analytics', methods=['GET'])
@login_required
def get_analytics():
    """Get advanced learning analytics."""
    try:
        streak = calculate_study_streak(current_user.id)
        weak = identify_weak_topics(current_user.id)[:5]
        strong = identify_strong_topics(current_user.id)[:5]
        
        return jsonify({
            "study_streak": streak,
            "weak_topics": [{"topic_id": t[0], "mastery": t[1], "attempts": t[2]} for t in weak],
            "strong_topics": [{"topic_id": t[0], "mastery": t[1], "attempts": t[2]} for t in strong],
            "progress_report": generate_progress_report(current_user.id)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/forgetting-curve-data', methods=['GET'])
@login_required
def get_forgetting_curve_data():
    """Generate forgetting curve data for all topics."""
    try:
        from user_state import generate_forgetting_curve_data
        curve_data = generate_forgetting_curve_data(current_user.id)
        return jsonify(curve_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/performance-dashboard', methods=['GET'])
@login_required
def get_performance_dashboard():
    """Get comprehensive performance dashboard data."""
    try:
        from learning_analytics import (
            calculate_topic_mastery_over_time,
            get_topic_time_distribution,
            get_comparative_stats
        )
        
        mastery_data = calculate_topic_mastery_over_time(current_user.id)
        topic_dist = get_topic_time_distribution(current_user.id)
        comparative = get_comparative_stats(current_user.id)
        
        return jsonify({
            "mastery_over_time": mastery_data,
            "topic_distribution": topic_dist,
            "comparative_stats": comparative
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/time-of-day-stats', methods=['GET'])
@login_required
def get_time_of_day_stats():
    """Get performance statistics by time of day."""
    try:
        from learning_analytics import calculate_time_of_day_performance
        stats = calculate_time_of_day_performance(current_user.id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/guide-me', methods=['POST'])
@login_required
def guide_me():
    """Generate step-by-step breakdown of a question."""
    data = request.json
    question = data.get('question')
    topic = data.get('topic')
    difficulty = data.get('difficulty')
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    prompt = f"""Break down this {difficulty} question about {topic} into 3-5 progressive sub-questions that guide a student to the answer.

Question: {question}

Return ONLY valid JSON in this format:
{{
  "sub_questions": [
    {{
      "step": 1,
      "question": "First, what concept do we need to identify?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": 0,
      "hint": "Think about the key terms in the question",
      "explanation": "Brief explanation after correct answer"
    }}
  ],
  "final_synthesis": "Now combine these insights to answer the original question"
}}

Each sub-question should be easier than the original and build toward the solution."""

    try:
        response = text_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 2:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
        response_text = response_text.strip()
        
        def parse_guide_json(raw_text: str):
            """Parse JSON from model output while tolerating stray backslashes/markdown."""
            cleaned = raw_text.strip()
            
            # First attempt: direct JSON parse
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass
            
            # Second attempt: escape invalid backslashes (e.g., LaTeX \alpha)
            sanitized = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', cleaned)
            sanitized = sanitized.replace('\n', '\\n')
            try:
                return json.loads(sanitized)
            except json.JSONDecodeError:
                pass
            
            # Final attempt: extract any JSON-looking object
            json_match = re.search(r'\{.*\}', sanitized, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # If all attempts fail, raise a clear error
            raise ValueError("AI response was not valid JSON")
        
        result = parse_guide_json(response_text)
        return jsonify(result)
    except Exception as e:
        print(f"Error in guide-me: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/exam-prep/create', methods=['POST'])
@login_required
def create_exam_prep():
    """Create an exam preparation plan."""
    data = request.json
    exam_name = data.get('exam_name')
    exam_date = data.get('exam_date')
    topics = data.get('topics', [])
    
    if not exam_name or not exam_date or not topics:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        from learning_analytics import predict_exam_readiness
        from datetime import datetime
        
        exam_date_obj = datetime.fromisoformat(exam_date.replace('Z', '+00:00'))
        readiness_data = predict_exam_readiness(current_user.id, topics, exam_date_obj)
        
        return jsonify(readiness_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/exam-prep/<exam_id>', methods=['GET'])
@login_required
def get_exam_prep(exam_id):
    """Get exam preparation data."""
    # This would retrieve saved exam prep data
    # For now, return placeholder
    return jsonify({"message": "Exam prep retrieval not yet implemented"}), 501


@app.route('/exam/upload', methods=['POST'])
@login_required
def upload_exam():
    """Upload exam file and extract questions using Gemini Vision."""
    try:
        print("[EXAM_UPLOAD] ========== STARTING EXAM UPLOAD ==========")
        print(f"[EXAM_UPLOAD] User ID: {current_user.id}")
        
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        exam_name = request.form.get('exam_name', file.filename or 'Untitled Exam')
        
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        filename = file.filename.lower()
        file_bytes = file.read()
        file_size = len(file_bytes)
        
        # Enforce file size limit (8 MB)
        max_file_size = 8 * 1024 * 1024
        if file_size > max_file_size:
            return jsonify({"error": f"File too large. Max size is {max_file_size / (1024 * 1024):.0f} MB."}), 413
        
        # Determine file type
        if filename.endswith('.pdf'):
            file_type = 'pdf'
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            file_type = filename.split('.')[-1]
        else:
            return jsonify({"error": "Unsupported file type. Please upload PDF or image."}), 400
        
        print(f"[EXAM_UPLOAD] Processing {file_type} file: {exam_name} ({file_size} bytes)")
        
        # Check if vision model is available
        if not vision_model:
            return jsonify({"error": "AI service not configured. Please check GEMINI_API_KEY environment variable."}), 500
        
        # Extract questions using Gemini Vision
        print("[EXAM_UPLOAD] Extracting questions with Gemini Vision...")
        extraction_result = extract_exam_questions_with_gemini(file_bytes, file_type, vision_model)
        
        if 'error' in extraction_result:
            return jsonify({"error": extraction_result['error']}), 500
        
        questions = extraction_result.get('questions', [])
        total_pages = extraction_result.get('total_pages', 0)
        
        if not questions:
            return jsonify({
                "error": "No questions found in the exam. Make sure the file contains actual exam questions, not just instructions."
            }), 400
        
        print(f"[EXAM_UPLOAD] Extracted {len(questions)} questions from {total_pages} pages")
        
        # Save to database
        print("[EXAM_UPLOAD] Saving questions to database...")
        save_result = save_exam_questions_to_db(
            current_user.id,
            exam_name,
            file_type,
            questions,
            total_pages
        )
        
        return jsonify({
            "success": True,
            "exam_id": save_result['exam_id'],
            "total_questions": save_result['total_questions'],
            "total_pages": total_pages,
            "message": f"Successfully extracted {save_result['total_questions']} questions from {total_pages} pages"
        })
    
    except Exception as e:
        print(f"[EXAM_UPLOAD] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def analyze_question_with_gemini(question_text: str, question_image_path: Optional[str] = None) -> Dict:
    """
    Use Gemini to solve a question and extract skills/difficulty.
    
    Args:
        question_text: OCR'd question text
        question_image_path: Optional path to question image
    
    Returns:
        Dictionary with solution, skills, difficulty, etc.
    """
    if not text_model:
        return {"error": "AI model not initialized"}
    
    prompt = """You are an expert tutor analyzing an exam question. Your task is to:
1. Solve the question completely
2. Identify ALL required skills and subskills (e.g., "u-substitution", "vector projections", "line integrals")
3. Identify prerequisite skills needed
4. Rate difficulty from 1-5 (1=very easy, 5=very hard)
5. Classify the question type

Return ONLY a JSON object with this exact structure:
{
  "solution": "Complete step-by-step solution",
  "answer": "Final answer",
  "required_skills": ["skill1", "skill2", ...],
  "prerequisite_skills": ["prereq1", "prereq2", ...],
  "difficulty": 3,
  "difficulty_reasoning": "Brief explanation of difficulty rating",
  "question_type": "classification (e.g., calculus/integration, linear_algebra/vectors)",
  "subskills": ["detailed subskill 1", "detailed subskill 2", ...]
}

Question text:
""" + question_text
    
    try:
        # Use vision model if image available
        if question_image_path:
            # Handle both absolute and relative paths
            if not os.path.isabs(question_image_path):
                # Relative path - construct full path
                question_image_path = os.path.join(os.path.dirname(__file__), 'uploads', question_image_path)
            
            if os.path.exists(question_image_path):
                image = Image.open(question_image_path)
                response = vision_model.generate_content([prompt, image])
            else:
                # Image path doesn't exist, use text only
                response = text_model.generate_content(prompt)
        else:
            response = text_model.generate_content(prompt)
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 2:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        return result
    
    except Exception as e:
        print(f"[GEMINI_ANALYSIS] Error: {e}")
        return {"error": str(e)}


@app.route('/exam/<int:exam_id>/analyze', methods=['POST'])
@login_required
def analyze_exam(exam_id):
    """Analyze all questions in an exam using Gemini."""
    try:
        db = get_db()
        try:
            # Verify exam belongs to user
            exam = db.cursor.execute(
                'SELECT exam_id, exam_name FROM exams WHERE exam_id = ? AND user_id = ?',
                (exam_id, current_user.id)
            ).fetchone()
            
            if not exam:
                return jsonify({"error": "Exam not found"}), 404
            
            # Get all questions for this exam
            questions = db.cursor.execute('''
                SELECT question_id, raw_text, image_path, solved_json
                FROM exam_questions
                WHERE exam_id = ?
                ORDER BY page_number, question_number
            ''', (exam_id,)).fetchall()
            
            if not questions:
                return jsonify({"error": "No questions found for this exam"}), 404
            
            print(f"[EXAM_ANALYZE] Analyzing {len(questions)} questions for exam {exam_id}")
            
            analyzed_count = 0
            errors = []
            
            # Analyze each question
            for question in questions:
                question_id = question['question_id']
                question_text = question['raw_text']
                image_path = question['image_path']
                
                # Skip if already analyzed
                if question['solved_json']:
                    continue
                
                try:
                    print(f"[EXAM_ANALYZE] Analyzing question {question_id}...")
                    analysis = analyze_question_with_gemini(question_text, image_path)
                    
                    if 'error' in analysis:
                        errors.append(f"Question {question_id}: {analysis['error']}")
                        continue
                    
                    # Extract skills and store
                    required_skills = analysis.get('required_skills', [])
                    prerequisite_skills = analysis.get('prerequisite_skills', [])
                    subskills = analysis.get('subskills', [])
                    all_skills = list(set(required_skills + prerequisite_skills + subskills))
                    
                    difficulty = analysis.get('difficulty', 3)
                    topics_json = json.dumps({
                        'required_skills': required_skills,
                        'prerequisite_skills': prerequisite_skills,
                        'subskills': subskills,
                        'question_type': analysis.get('question_type', '')
                    })
                    
                    # Update question with analysis
                    db.cursor.execute('''
                        UPDATE exam_questions
                        SET solved_json = ?, difficulty = ?, topics_json = ?
                        WHERE question_id = ?
                    ''', (
                        json.dumps(analysis),
                        difficulty,
                        topics_json,
                        question_id
                    ))
                    
                    # Store skills in exam_question_skills table
                    for skill_name in all_skills:
                        is_prereq = skill_name in prerequisite_skills
                        db.cursor.execute('''
                            INSERT OR IGNORE INTO exam_question_skills
                            (question_id, skill_name, is_prerequisite)
                            VALUES (?, ?, ?)
                        ''', (question_id, skill_name, is_prereq))
                    
                    db.conn.commit()
                    analyzed_count += 1
                    
                except Exception as e:
                    print(f"[EXAM_ANALYZE] Error analyzing question {question_id}: {e}")
                    errors.append(f"Question {question_id}: {str(e)}")
            
            return jsonify({
                "success": True,
                "analyzed": analyzed_count,
                "total": len(questions),
                "errors": errors if errors else None
            })
        
        finally:
            db.disconnect()
    
    except Exception as e:
        print(f"[EXAM_ANALYZE] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/exam/<int:exam_id>/questions', methods=['GET'])
@login_required
def get_exam_questions(exam_id):
    """Get all questions for an exam."""
    try:
        db = get_db()
        try:
            # Verify exam belongs to user
            exam = db.cursor.execute(
                'SELECT exam_id, exam_name FROM exams WHERE exam_id = ? AND user_id = ?',
                (exam_id, current_user.id)
            ).fetchone()
            
            if not exam:
                return jsonify({"error": "Exam not found"}), 404
            
            # Get questions
            questions = db.cursor.execute('''
                SELECT question_id, page_number, question_number, raw_text, ocr_confidence,
                       image_path, solved_json, difficulty, topics_json
                FROM exam_questions
                WHERE exam_id = ?
                ORDER BY page_number, 
                         CASE 
                             WHEN question_number GLOB '[0-9]*' THEN CAST(question_number AS INTEGER)
                             ELSE 999999
                         END,
                         question_number
            ''', (exam_id,)).fetchall()
            
            print(f"[GET_EXAM_QUESTIONS] Found {len(questions)} questions for exam {exam_id}")
            
            result = []
            for q in questions:
                question_data = {
                    'question_id': q['question_id'],
                    'page_number': q['page_number'],
                    'question_number': q['question_number'],
                    'text': q['raw_text'],
                    'ocr_confidence': q['ocr_confidence'],
                    'image_path': q['image_path'],
                    'difficulty': q['difficulty'],
                    'analyzed': q['solved_json'] is not None
                }
                
                if q['solved_json']:
                    solved_data = json.loads(q['solved_json'])
                    question_data['solution'] = solved_data.get('solution')
                    question_data['answer'] = solved_data.get('answer')
                    question_data['difficulty_reasoning'] = solved_data.get('difficulty_reasoning')
                
                if q['topics_json']:
                    topics_data = json.loads(q['topics_json'])
                    question_data['skills'] = topics_data.get('required_skills', [])
                    question_data['prerequisite_skills'] = topics_data.get('prerequisite_skills', [])
                    question_data['subskills'] = topics_data.get('subskills', [])
                    question_data['question_type'] = topics_data.get('question_type')
                
                # Format image path for frontend
                if q.get('image_path'):
                    # Extract just the filename from the path
                    if 'exams/' in q['image_path']:
                        question_data['image_path'] = q['image_path'].split('exams/')[1]
                    else:
                        question_data['image_path'] = q['image_path']
                
                result.append(question_data)
            
            return jsonify({
                "exam_id": exam_id,
                "exam_name": exam['exam_name'],
                "questions": result
            })
        
        finally:
            db.disconnect()
    
    except Exception as e:
        print(f"[GET_EXAM_QUESTIONS] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/exams/<path:filename>')
@login_required
def serve_exam_image(filename):
    """Serve exam question images."""
    try:
        # Security: ensure user can only access their own exam images
        exam_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'exams', str(current_user.id))
        file_path = os.path.join(exam_dir, filename)
        
        # Verify file is within user's exam directory
        if not file_path.startswith(os.path.abspath(exam_dir)):
            return jsonify({"error": "Unauthorized"}), 403
        
        if os.path.exists(file_path):
            return send_from_directory(exam_dir, filename)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        print(f"[SERVE_EXAM_IMAGE] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/exam/<int:exam_id>/analytics', methods=['GET'])
@login_required
def get_exam_analytics_route(exam_id):
    """Get aggregated analytics for an exam."""
    try:
        from learning_analytics import get_exam_analytics
        
        # Verify exam belongs to user
        db = get_db()
        try:
            exam = db.cursor.execute(
                'SELECT exam_id FROM exams WHERE exam_id = ? AND user_id = ?',
                (exam_id, current_user.id)
            ).fetchone()
            
            if not exam:
                return jsonify({"error": "Exam not found"}), 404
        finally:
            db.disconnect()
        
        analytics = get_exam_analytics(current_user.id, exam_id)
        
        if analytics:
            return jsonify(analytics)
        else:
            return jsonify({"error": "No analytics available"}), 404
    
    except Exception as e:
        print(f"[GET_EXAM_ANALYTICS] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/exams', methods=['GET'])
@login_required
def get_exams():
    """Get all exams for the current user."""
    try:
        db = get_db()
        try:
            exams = db.cursor.execute('''
                SELECT exam_id, exam_name, file_type, total_pages, total_questions, created_at
                FROM exams
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (current_user.id,)).fetchall()
            
            result = []
            for exam in exams:
                # Count analyzed questions
                analyzed = db.cursor.execute('''
                    SELECT COUNT(*) FROM exam_questions
                    WHERE exam_id = ? AND solved_json IS NOT NULL
                ''', (exam['exam_id'],)).fetchone()[0]
                
                result.append({
                    'exam_id': exam['exam_id'],
                    'exam_name': exam['exam_name'],
                    'file_type': exam['file_type'],
                    'total_pages': exam['total_pages'],
                    'total_questions': exam['total_questions'],
                    'analyzed_questions': analyzed,
                    'created_at': exam['created_at']
                })
            
            return jsonify({"exams": result})
        
        finally:
            db.disconnect()
    
    except Exception as e:
        print(f"[GET_EXAMS] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/documents', methods=['GET'])
@login_required
def get_documents():
    """Get all documents for the current user."""
    try:
        db = get_db()
        try:
            documents = db.cursor.execute('''
                SELECT document_id, filename, file_type, file_size, uploaded_at, topics_extracted
                FROM documents
                WHERE user_id = ?
                ORDER BY uploaded_at DESC
            ''', (current_user.id,)).fetchall()
            
            result = []
            for doc in documents:
                topics = []
                if doc['topics_extracted']:
                    try:
                        topics = json.loads(doc['topics_extracted'])
                    except:
                        pass
                
                result.append({
                    'document_id': doc['document_id'],
                    'filename': doc['filename'],
                    'file_type': doc['file_type'],
                    'file_size': doc['file_size'],
                    'uploaded_at': doc['uploaded_at'],
                    'topics_count': len(topics) if isinstance(topics, list) else 0
                })
            
            return jsonify({"documents": result})
        finally:
            db.disconnect()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/documents/<int:document_id>/load', methods=['POST'])
@login_required
def load_document(document_id):
    """Load a document's topics into the current session."""
    try:
        db = get_db()
        try:
            # Get document
            doc = db.cursor.execute('''
                SELECT file_path, topics_extracted, user_id
                FROM documents
                WHERE document_id = ?
            ''', (document_id,)).fetchone()
            
            if not doc:
                return jsonify({"error": "Document not found"}), 404
            
            if doc['user_id'] != current_user.id:
                return jsonify({"error": "Unauthorized"}), 403
            
            # Parse topics
            topics_data = json.loads(doc['topics_extracted']) if doc['topics_extracted'] else []
            
            if not topics_data:
                return jsonify({"error": "No topics found in document"}), 400
            
            # Load topics
            topic_data = {"topics": topics_data}
            topics.clear()
            clear_user_state(current_user.id)
            load_topics_from_json(topic_data)
            init_user_state(current_user.id)
        
        return jsonify({
                "success": True,
                "topics": get_all_topics()
            })
        finally:
            db.disconnect()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/documents/<int:document_id>/delete', methods=['DELETE'])
@login_required
def delete_document(document_id):
    """Delete a document."""
    try:
        db = get_db()
        try:
            # Get document info
            doc = db.cursor.execute('''
                SELECT file_path, user_id
                FROM documents
                WHERE document_id = ?
            ''', (document_id,)).fetchone()
            
            if not doc:
                return jsonify({"error": "Document not found"}), 404
            
            if doc['user_id'] != current_user.id:
                return jsonify({"error": "Unauthorized"}), 403
            
            # Delete file
            if os.path.exists(doc['file_path']):
                try:
                    os.remove(doc['file_path'])
                except Exception as e:
                    print(f"Error deleting file: {e}")
            
            # Delete from database
            db.cursor.execute('DELETE FROM documents WHERE document_id = ?', (document_id,))
            db.conn.commit()
            
            return jsonify({"success": True})
        finally:
            db.disconnect()
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Gamification Endpoints
@app.route('/achievements', methods=['GET'])
@login_required
def get_achievements():
    """Get all achievements with user's unlock status."""
    try:
        achievements = get_all_achievements_with_status(current_user.id)
        return jsonify({"achievements": achievements})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/achievements/user', methods=['GET'])
@login_required
def get_user_achievements_route():
    """Get user's unlocked achievements."""
    try:
        achievements = get_user_achievements(current_user.id)
        return jsonify({"achievements": achievements})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/user/level', methods=['GET'])
@login_required
def get_user_level():
    """Get user's current level and XP progress."""
    try:
        xp_progress = get_xp_progress(current_user.total_xp)
        return jsonify({
            "total_xp": current_user.total_xp,
            **xp_progress
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Leaderboard Endpoints
@app.route('/leaderboard/<leaderboard_type>', methods=['GET'])
@login_required
def get_leaderboard(leaderboard_type):
    """Get leaderboard rankings."""
    try:
        filter_value = request.args.get('filter')
        period = request.args.get('period', 'alltime')
        limit = int(request.args.get('limit', 100))
        
        leaderboard = calculate_leaderboard(leaderboard_type, filter_value, period, limit)
        
        return jsonify({
            "leaderboard": leaderboard,
            "type": leaderboard_type,
            "filter": filter_value,
            "period": period
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/leaderboard/my-rank', methods=['GET'])
@login_required
def get_my_rank():
    """Get current user's rank and nearby users."""
    try:
        leaderboard_type = request.args.get('type', 'global')
        filter_value = request.args.get('filter')
        period = request.args.get('period', 'alltime')
        
        rank_data = get_user_rank(current_user.id, leaderboard_type, filter_value, period)
        
        return jsonify(rank_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/leaderboard/stats', methods=['GET'])
@login_required
def get_leaderboard_stats():
    """Get course/campus statistics."""
    try:
        course_code = request.args.get('course', 'CS 180')
        
        stats = get_course_statistics(course_code)
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/leaderboard/types', methods=['GET'])
@login_required
def get_leaderboard_types_route():
    """Get available leaderboard types and filters."""
    try:
        types_data = get_all_leaderboard_types()
        return jsonify(types_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Activity Feed Endpoints
@app.route('/activity/recent', methods=['GET'])
@login_required
def get_recent_activity_route():
    """Get recent activity across all users."""
    try:
        limit = int(request.args.get('limit', 10))
        hours = int(request.args.get('hours', 24))
        
        activities = get_recent_activity(limit, hours)
        
        return jsonify({"activities": activities})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/activity/user', methods=['GET'])
@login_required
def get_user_activity():
    """Get current user's activity feed."""
    try:
        limit = int(request.args.get('limit', 20))
        activities = get_user_activity_feed(current_user.id, limit)
        
        return jsonify({"activities": activities})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/notifications/milestones', methods=['GET'])
@login_required
def get_milestone_notifications_route():
    """Get milestone notifications for current user."""
    try:
        notifications = get_milestone_notifications(current_user.id)
        return jsonify({"notifications": notifications})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/social-proof', methods=['GET'])
def get_social_proof():
    """Get social proof statistics (public endpoint)."""
    try:
        data = get_social_proof_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Challenge Endpoints
@app.route('/challenges/create', methods=['POST'])
@login_required
def create_challenge():
    """Create a direct challenge."""
    try:
        data = request.json
        challenged_id = data.get('challenged_id')  # None for link-based
        question_data = data.get('question_data')
        
        if not question_data:
            return jsonify({"error": "Question data required"}), 400
        
        result = create_direct_challenge(current_user.id, challenged_id, question_data)
        
        if result:
            return jsonify({"success": True, **result})
        else:
            return jsonify({"error": "Failed to create challenge"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/challenges/link/<link_code>', methods=['GET'])
def get_challenge_link(link_code):
    """Get challenge by link code (public for sharing)."""
    try:
        challenge = get_challenge_by_link(link_code)
        
        if challenge:
            return jsonify({"success": True, "challenge": challenge})
        else:
            return jsonify({"error": "Challenge not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/challenges/received', methods=['GET'])
@login_required
def get_received_challenges_route():
    """Get challenges sent to current user."""
    try:
        challenges = get_received_challenges(current_user.id)
        return jsonify({"challenges": challenges})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/challenges/<int:challenge_id>/accept', methods=['POST'])
@login_required
def accept_challenge_route(challenge_id):
    """Accept a challenge."""
    try:
        question_data = accept_challenge(challenge_id, current_user.id)
        
        if question_data:
            return jsonify({"success": True, "question": question_data})
        else:
            return jsonify({"error": "Challenge not found or already completed"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/challenges/<int:challenge_id>/complete', methods=['POST'])
@login_required
def complete_challenge_route(challenge_id):
    """Submit answer for a challenge."""
    try:
        data = request.json
        is_correct = data.get('is_correct', False)
        
        result = complete_challenge(challenge_id, current_user.id, is_correct)
        
        if result:
            return jsonify({"success": True, **result})
        else:
            return jsonify({"error": "Failed to complete challenge"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Community Question Pool Endpoints
@app.route('/questions/community/submit', methods=['POST'])
@login_required
def submit_community_question_route():
    """Submit a question to the community pool."""
    try:
        question_data = request.json
        
        if not question_data:
            return jsonify({"error": "Question data required"}), 400
        
        question_id = submit_community_question(current_user.id, question_data)
        
        if question_id:
            return jsonify({"success": True, "question_id": question_id})
        else:
            return jsonify({"error": "Failed to submit question"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/questions/community', methods=['GET'])
@login_required
def get_community_questions_route():
    """Browse community questions."""
    try:
        course = request.args.get('course')
        topic = request.args.get('topic')
        limit = int(request.args.get('limit', 20))
        
        questions = get_community_questions(course, topic, limit)
        
        return jsonify({"questions": questions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/questions/community/<int:question_id>/vote', methods=['POST'])
@login_required
def vote_community_question_route(question_id):
    """Vote on a community question."""
    try:
        data = request.json
        vote_type = data.get('vote_type', 'up')  # 'up' or 'down'
        
        new_count = vote_community_question(current_user.id, question_id, vote_type)
        
        if new_count is not None:
            return jsonify({"success": True, "likes_count": new_count})
        else:
            return jsonify({"error": "Failed to vote"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Auto-initialize database on first run
with app.app_context():
    if not os.path.exists('learning_app.db'):
        init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)


