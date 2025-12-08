import os
import json
import base64
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import google.generativeai as genai
from PyPDF2 import PdfReader
from PIL import Image
import io
from dotenv import load_dotenv

from topic_map import load_topics_from_json, get_all_topics, topics
from user_state import (init_user_state, record_answer, get_target_difficulty, get_user_state, 
                        clear_user_state, generate_progress_report)
from question_picker import pick_next_topic, get_recommended_study_order
from learning_analytics import (calculate_study_streak, identify_weak_topics, 
                                 identify_strong_topics, export_analytics_report)
from auth import (User, register_user, login_user as auth_login_user, get_users_online_count, 
                  update_user_streak, get_or_create_oauth_user)
from database import init_db
from gamification import (calculate_xp, award_xp, check_achievements, get_user_achievements,
                          get_all_achievements_with_status, get_xp_progress)
from leaderboards import (calculate_leaderboard, get_user_rank, get_course_statistics,
                          get_all_leaderboard_types, calculate_weekly_xp)
from activity_feed import (get_recent_activity, get_user_activity_feed, get_milestone_notifications,
                           get_social_proof_data, get_competitive_notifications)
from challenges import (create_direct_challenge, get_challenge_by_link, get_received_challenges,
                       accept_challenge, complete_challenge, submit_community_question,
                       get_community_questions, vote_community_question)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'  # Redirect to index if not logged in

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
    raise ValueError("GEMINI_API_KEY environment variable is required")
genai.configure(api_key=GEMINI_API_KEY)

# Models - using gemini-2.5-flash-lite
text_model = genai.GenerativeModel('gemini-2.5-flash-lite')
vision_model = genai.GenerativeModel('gemini-2.5-flash-lite')


def extract_text_from_pdf(file_bytes):
    """Extract text from a PDF file."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_topics_from_content(content, is_image=False, image_bytes=None):
    """Use Gemini to extract topics from content."""
    prompt = """Analyze this content and extract the main topics that could be tested.
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

IMPORTANT: Include a helpful "explanation" field for each topic that explains the concept clearly.
Only return the JSON, no other text."""

    try:
        if is_image and image_bytes:
            # Use vision model for images
            image = Image.open(io.BytesIO(image_bytes))
            response = vision_model.generate_content([prompt, image])
        else:
            # Use text model
            response = text_model.generate_content(f"{prompt}\n\nContent:\n{content}")
        
        # Parse the response
        response_text = response.text.strip()
        print(f"Gemini raw response: {response_text[:500]}...")  # Debug log
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            parts = response_text.split("```")
            if len(parts) >= 2:
                response_text = parts[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
        response_text = response_text.strip()
        
        print(f"Parsed JSON text: {response_text[:500]}...")  # Debug log
        result = json.loads(response_text)
        print(f"Extracted {len(result.get('topics', []))} topics")  # Debug log
        return result
    except Exception as e:
        print(f"Error extracting topics: {e}")
        import traceback
        traceback.print_exc()
        return {"topics": []}


def generate_question_for_topic(topic, difficulty):
    """Use Gemini to generate a question for a topic."""
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
    
    # Auto-login after registration
    login_user(user, remember=True)
    
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
    
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    
    user = auth_login_user(username, password)
    
    if not user:
        return jsonify({"error": "Invalid username or password"}), 401
    
    # Login with flask-login
    login_user(user, remember=True)
    
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
        
        # Login user
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
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    filename = file.filename.lower()
    file_bytes = file.read()
    
    try:
        if filename.endswith('.pdf'):
            # Extract text from PDF
            content = extract_text_from_pdf(file_bytes)
            topic_data = extract_topics_from_content(content)
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            # Use vision model for images
            topic_data = extract_topics_from_content(None, is_image=True, image_bytes=file_bytes)
        elif filename.endswith('.txt'):
            # Plain text file
            content = file_bytes.decode('utf-8')
            topic_data = extract_topics_from_content(content)
        else:
            return jsonify({"error": "Unsupported file type"}), 400
        
        # Check if any topics were extracted
        if not topic_data.get("topics"):
            return jsonify({"error": "No topics could be extracted from the document. Try a different file."}), 400
        
        # Clear existing topics and user state, then load new ones
        topics.clear()
        clear_user_state(current_user.id)
        load_topics_from_json(topic_data)
        init_user_state(current_user.id)
        
        print(f"Loaded {len(get_all_topics())} topics into memory")  # Debug log
        
        return jsonify({
            "success": True,
            "topics": get_all_topics()
        })
    except Exception as e:
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
        
        result = json.loads(response_text)
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


