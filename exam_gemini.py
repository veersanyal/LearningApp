"""
Use Gemini Vision to extract exam questions directly from PDFs/images.
This replaces OCR with AI-powered extraction that handles LaTeX, math, and complex formatting.
"""


import os
import json
import io
import time
import tempfile
from typing import List, Dict, Optional
from PIL import Image
import google.generativeai as genai
from database import get_db
from datetime import datetime


def extract_exam_questions_with_gemini(file_bytes: bytes, file_type: str, vision_model) -> Dict:
    """
    Use Gemini Vision to extract exam questions directly from PDF/image.
    
    Args:
        file_bytes: File content as bytes
        file_type: 'pdf' or image extension ('png', 'jpg', etc.)
        vision_model: Initialized Gemini vision model
    
    Returns:
        Dict with 'questions' list and 'total_pages'
    """
    if not vision_model:
        return {"error": "Vision model not initialized"}
    
    prompt = """Analyze this exam file and extract structured data.
    
CRITICAL INSTRUCTIONS:
1. Extract metadata: Look for Year (e.g. 2023), Semester (Fall/Spring/Summer), Course Code (e.g. MA 161), and Exam Name.
2. Extract ALL questions: Numbered items (1, 2, 3...) definitions, or problems.
3. For Multiple Choice: Extract options as a list. REMOVE leading labels like "(A)" or "a." from the text.
4. Math/LaTeX: Use $ for inline math and $$ for display math. e.g. $\\int x dx$.
5. Diagrams: If a question has an image/diagram, set "has_diagram": true and provide a description.

Return raw JSON (no markdown formatting) matching this schema:
{
  "exam_metadata": {
    "course_code": "String",
    "semester": "String (Fall/Spring/Summer)",
    "year": 2024,
    "exam_type": "String (e.g. Exam 1)"
  },
  "questions": [
    {
      "question_number": "String",
      "question_text": "String (LaTeX included)",
      "question_type": "multiple_choice | free_response",
      "options": ["Option 1 text", "Option 2 text"] (null if not MC),
      "correct_answer": "String (if marked)",
      "page_number": Integer,
      "has_diagram": Boolean,
      "difficulty_estimate": Integer (1-5),
      "topics": ["String"]
    }
  ],
  "total_pages": Integer
}"""

    try:
        questions_data = []
        total_pages = 0
        instruction_pages = []
        exam_metadata = {}
        
        if file_type == 'pdf':
            # Use Gemini File API for PDF
            print("[GEMINI_EXTRACT] Uploading PDF to Gemini File API...")
            
            # Create a temporary file to upload
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf.write(file_bytes)
                temp_pdf_path = temp_pdf.name
                
            try:
                # Upload the file
                uploaded_file = genai.upload_file(temp_pdf_path, mime_type="application/pdf")
                print(f"[GEMINI_EXTRACT] Uploaded file: {uploaded_file.name}")
                
                # Wait for file to be active
                print("[GEMINI_EXTRACT] Waiting for file processing...")
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_file = genai.get_file(uploaded_file.name)
                
                if uploaded_file.state.name == "FAILED":
                    raise ValueError("Gemini File API failed to process the PDF.")
                
                print("[GEMINI_EXTRACT] File processed successfully. Generating content...")
                
                # Generate content
                response = vision_model.generate_content(
                    [prompt, uploaded_file],
                    request_options={"timeout": 600}  # Long timeout for full PDF processing
                )
                
                # Process response
                response_text = response.text.strip()
                    
                # Remove markdown code blocks if present
                if response_text.startswith("```"):
                    parts = response_text.split("```")
                    if len(parts) >= 2:
                        response_text = parts[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                response_text = response_text.strip()
                
                # Parse JSON response
                try:
                    data = json.loads(response_text)
                    if data.get("questions"):
                        questions_data = data["questions"]
                        print(f"[GEMINI_EXTRACT] Extracted {len(questions_data)} questions from PDF")
                        
                    total_pages = data.get("total_pages", 1) # AI estimate
                    instruction_pages = data.get("instruction_pages_skipped", [])
                    exam_metadata = data.get("exam_metadata", {})
                    
                except json.JSONDecodeError as e:
                    print(f"[GEMINI_EXTRACT] Error parsing JSON: {e}")
                    print(f"[GEMINI_EXTRACT] Raw PDF response: {response_text[:500]}...")
                    # Try to find JSON array in text
                    import re
                    json_match = re.search(r'\{.*"questions".*\}', response_text, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(0))
                            questions_data = data.get("questions", [])
                            print(f"[GEMINI_EXTRACT] Recovered {len(questions_data)} questions from messy response")
                        except:
                            print(f"[GEMINI_EXTRACT] Failed to recover JSON")
                
                # Clean up remote file
                try:
                    genai.delete_file(uploaded_file.name)
                    print("[GEMINI_EXTRACT] Deleted remote file")
                except:
                    pass
                    
            except Exception as e:
                print(f"[GEMINI_EXTRACT] Error using Gemini File API: {e}")
                import traceback
                traceback.print_exc()
                # Clean up remote file if it exists and we have the ref
                if 'uploaded_file' in locals():
                    try:
                        genai.delete_file(uploaded_file.name)
                    except:
                        pass
                raise e
            finally:
                # Clean up local temp file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
        
        elif file_type in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            # Single image - use direct inline data
            print("[GEMINI_EXTRACT] Processing single image with Gemini...")
            image = Image.open(io.BytesIO(file_bytes))
            total_pages = 1
            
            try:
                response = vision_model.generate_content(
                    [prompt, image],
                    request_options={"timeout": 30}
                )
                
                response_text = response.text.strip()
                print(f"[GEMINI_EXTRACT] Raw Image Response Length: {len(response_text)}")
                
                # Robust JSON extraction: Find parsed outer braces
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    response_text = response_text[start_idx : end_idx + 1]
                    print("[GEMINI_EXTRACT] Found JSON bounds, trimming reponse.")
                else:
                    print("[GEMINI_EXTRACT] Warning: Could not find JSON braces in response.")

                # Parse JSON response
                page_data = json.loads(response_text)
                print(f"[GEMINI_EXTRACT] Parsed Keys: {list(page_data.keys())}")
                
                exam_metadata = page_data.get("exam_metadata", {})
                
                # Add questions
                if page_data.get("questions"):
                    for q in page_data["questions"]:
                        q["page_number"] = 1
                        questions_data.append(q)
                    print(f"[GEMINI_EXTRACT] Extracted {len(page_data.get('questions', []))} questions from image")
                
            except json.JSONDecodeError as e:
                print(f"[GEMINI_EXTRACT] Error parsing JSON from image: {e}")
                print(f"[GEMINI_EXTRACT] Response text: {response_text[:500]}")
                import traceback
                traceback.print_exc()
                return {"error": f"Failed to parse Gemini response. The AI may have returned invalid JSON. Response preview: {response_text[:200]}..."}
            except Exception as e:
                print(f"[GEMINI_EXTRACT] Error processing image: {e}")
                import traceback
                traceback.print_exc()
                return {"error": f"Failed to process image: {str(e)}"}
        
        else:
            return {"error": f"Unsupported file type: {file_type}"}
        
        print(f"[GEMINI_EXTRACT] Total: {len(questions_data)} questions extracted")
        
        return {
            "questions": questions_data,
            "total_pages": total_pages,
            "instruction_pages_skipped": instruction_pages,
            "exam_metadata": exam_metadata
        }
    
    except Exception as e:
        print(f"[GEMINI_EXTRACT] Top-level error: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        # Provide more helpful error messages
        if "timeout" in error_msg.lower() or "deadline" in error_msg.lower():
            return {"error": "Request timed out. The exam file may be too large. Try splitting it into smaller parts or use a smaller file."}
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return {"error": "API rate limit exceeded. Please try again in a few moments."}
        elif "api key" in error_msg.lower() or "unauthorized" in error_msg.lower():
            return {"error": "API key error. Please check your Gemini API key configuration."}
        else:
            return {"error": f"Failed to extract questions: {error_msg}"}


def save_exam_questions_to_db(user_id: int, exam_name: str, file_type: str, questions_data: List[Dict], total_pages: int, exam_year: int = None, semester: str = None, course_name: str = None, exam_type: str = None, exam_id: int = None) -> Dict:
    """
    Save extracted questions to the database (Create or Update).
    
    Args:
        user_id: User ID
        exam_name: Name of the exam
        file_type: File type ('pdf' or image extension)
        questions_data: List of question dictionaries from Gemini
        total_pages: Total number of pages
        exam_year: Year of the exam (integer)
        semester: Semester (e.g., "Fall 2024")
        course_name: Course code/name (e.g. "CS 101")
        exam_type: Type of exam (e.g. "Midterm 1")
        exam_id: Optional ID for updating an existing exam
    
    Returns:
        Dict with 'exam_id' and 'total_questions'
    """
    db = get_db()
    try:
        # Create or Update exam record
        exam_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'exams', str(user_id))
        os.makedirs(exam_dir, exist_ok=True)
        
        if exam_id:
             # UPDATE existing exam
             db.cursor.execute('''
                UPDATE exams 
                SET exam_name=?, file_type=?, total_pages=?, total_questions=?, exam_year=?, semester=?, course_name=?, exam_type=?
                WHERE exam_id=? AND user_id=?
            ''', (exam_name, file_type, total_pages, len(questions_data), exam_year, semester, course_name, exam_type, exam_id, user_id))
             
             # For simplicity in this edit flow, we'll clear old questions and re-insert them. 
             # A smarter diff approach could be used later.
             db.cursor.execute('DELETE FROM exam_questions WHERE exam_id=?', (exam_id,))
             
        else:
            # CREATE new exam
            db.cursor.execute('''
                INSERT INTO exams (user_id, exam_name, file_type, total_pages, total_questions, exam_year, semester, course_name, exam_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, exam_name, file_type, total_pages, len(questions_data), exam_year, semester, course_name, exam_type))
            exam_id = db.cursor.lastrowid
        
        db.conn.commit()
        
        # Save questions
        for q in questions_data:
            # Store question data as JSON
            question_json = json.dumps({
                "question_text": q.get("question_text", ""),
                "question_type": q.get("question_type", "free_response"),
                "options": q.get("options"),
                "correct_answer": q.get("correct_answer"),
                "has_diagram": q.get("has_diagram", False),
                "diagram_description": q.get("diagram_description"),
                "image_path": q.get("image_path"),
                "topics": q.get("topics", []),
                "subparts": q.get("subparts"),
                # Solution fields
                "steps": q.get("steps"),
                "guiding_questions": q.get("guiding_questions"),
                "explanation": q.get("explanation"),
                "key_concept": q.get("key_concept"),
                # Keep solution/answer for backward compatibility or if structure differs
                "solution": q.get("solution"),
                "answer": q.get("answer")
            })
            
            # Insert main question
            db.cursor.execute('''
                INSERT INTO exam_questions 
                (exam_id, page_number, question_number, raw_text, solved_json, difficulty, topics_json, diagram_note, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                exam_id,
                q.get("page_number", 1),
                q.get("question_number", "?"),
                q.get("question_text") or q.get("text", ""),  # Handle both keys
                question_json,  # Store full structured data in solved_json
                q.get("difficulty_estimate", 3),
                json.dumps({"topics": q.get("topics", [])}),
                q.get("diagram_description"),  # Store diagram description in diagram_note column
                q.get("image_path")  # Store image path in column
            ))
            
            question_id = db.cursor.lastrowid
            
            # Save subparts if any
            if q.get("subparts"):
                for subpart in q["subparts"]:
                    subpart_json = json.dumps(subpart)
                    db.cursor.execute('''
                        INSERT INTO exam_questions 
                        (exam_id, page_number, question_number, raw_text, solved_json, difficulty, topics_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        exam_id,
                        q.get("page_number", 1),
                        subpart.get("subpart_number", "?"),
                        subpart.get("subpart_text", ""),
                        subpart_json,
                        q.get("difficulty_estimate", 3),
                        json.dumps({"topics": q.get("topics", [])})
                    ))
        
        db.conn.commit()
        
        return {
            "exam_id": exam_id,
            "total_questions": len(questions_data)
        }
    
    except Exception as e:
        db.conn.rollback()
        print(f"[SAVE_EXAM] Database error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.disconnect()


def solve_exam_questions(questions: List[Dict], text_model) -> List[Dict]:
    """
    Analyzes questions using Gemini to find correct answers and generate steps.
    Returns the updated list with 'correct_answer' and solution fields.
    """
    if not text_model:
        raise Exception("Text model not initialized")

    print(f"[GEMINI_SOLVE] Solving {len(questions)} questions...")
    
    # Construct a single prompt for all questions
    questions_subset = []
    for i, q in enumerate(questions):
        # Sanitize options to ensure they are strings
        raw_options = q.get('options', [])
        sanitized_options = []
        if isinstance(raw_options, list):
            for opt in raw_options:
                if isinstance(opt, dict):
                    sanitized_options.append(str(opt.get('text', '')))
                else:
                    sanitized_options.append(str(opt))
        
        questions_subset.append({
            "id": i,
            "text": str(q.get('question_text', '')),
            "options": sanitized_options,
            "has_image": bool(q.get('has_diagram')) or bool(q.get('image_path'))
        })
    
    prompt = """You are an expert tutor. Solve these exam questions.

For EACH question, you must generate a "Guide Me" solution that strictly follows this generation rubric:

1. **One micro-goal per step**: Each step has a single job (identify, choose, compute, compare, conclude). No combo steps.
2. **True Hint Ladder (CRITICAL)**:
    - Hint 1 (Nudge): Conceptual direction (no formulas). "What determines..."
    - Hint 2 (Method): The specific rule or formula. "Use distance = |coord|..."
    - Hint 3 (Setup): What values to substitute. "Substitute z = -4..."
    - DO NOT skip tiers. DO NOT give the answer in the hint.
3. **NO PRE-COMPUTATION (CRITICAL)**: Never state the values the user must find in the question text. (e.g. DO NOT say "Since d=4..."). Make the *user* compute them.
4. **Socratic & Active**: Prompts should force a decision or calculation. "Calculate the distance..." or "Which condition is met?"
5. **Anchor to decision rule**: Center guidance on repeatable rules.
6. **Actionable Feedback**: For wrong options, explain *why* it's wrong (e.g. "You used the x-coordinate instead of z").
7. **Consistent Notation**: Use standard consistent variables (e.g. if using h,k,l for center, stick to it).
8. **Consistent Structure**: Title, Prompt, Input/Choice, Hints, Checkpoint.
9. **Generalization Hook**: End with a one-liner transferring the skill.
10. **EXACTLY 4 OPTIONS**: Every single guiding question MUST have exactly 4 options (A, B, C, D). If you only have 3 plausible ones, create a distractor based on a common misconception.

Input Data:
""" + json.dumps(questions_subset, indent=2) + """

OUTPUT FORMAT: Return a JSON Object where keys are the question indices (0, 1, 2...) and values have:
{
  "correct_answer": "Final Answer string",
  "steps": ["Step 1...", "Step 2..."],
  "explanation": "Detailed summary using <b>bold</b> and <br>...",
  "key_concept": "Concept",
  "guiding_questions": [
     {
       "title": "Micro-goal (e.g. COMPUTE DISTANCE TO XZ-PLANE)",
       "question": "Use the center (h,k,l) to find the distance...",
       "options": [
          {"text": "2", "feedback": "Correct! The distance is |y| = |-2| = 2."},
          {"text": "4", "feedback": "Incorrect. That is the distance to the xy-plane (|z|)."},
          {"text": "-2", "feedback": "Incorrect. Distance must be non-negative."},
          {"text": "1", "feedback": "Incorrect. This is the distance to the yz-plane (|x|)."}
       ],
       "correct_answer": "2",
       "hints": [
          "Nudge: The distance to the xz-plane depends on the coordinate *perpendicular* to it.",
          "Method: distance = |y|",
          "Setup: The y-coordinate of the center is -2."
       ],
       "checkpoint": "Distance matches |y|.",
       "generalization": "For any coordinate plane, distance is the absolute value of the missing variable."
     }
  ]
}

IMPORTANT:
- If the answer or steps contain LaTeX (e.g. \\frac, \\pi), you MUST escape the backslashes (e.g. \\\\frac, \\\\pi) so the Output is valid JSON.
- Do not use markdown backticks ```json ... ``` in the response, just the raw JSON string.

Return ONLY valid JSON."""

    try:
        response = text_model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Robust JSON extraction
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1:
            response_text = response_text[start:end+1]
            
        solutions = json.loads(response_text)
        
        # Merge solutions back into questions
        for i, sol in solutions.items():
            idx = int(i)
            if 0 <= idx < len(questions):
                questions[idx]['correct_answer'] = sol.get('correct_answer')
                questions[idx]['steps'] = sol.get('steps')
                questions[idx]['guiding_questions'] = sol.get('guiding_questions')
                questions[idx]['explanation'] = sol.get('explanation')
                questions[idx]['key_concept'] = sol.get('key_concept')
                
        print("[GEMINI_SOLVE] Analysis complete.")
        return questions
        
    except Exception as e:
        print(f"[GEMINI_SOLVE] Error: {e}")
        # import traceback
        # traceback.print_exc()
        raise e

