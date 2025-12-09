"""
Use Gemini Vision to extract exam questions directly from PDFs/images.
This replaces OCR with AI-powered extraction that handles LaTeX, math, and complex formatting.
"""

import os
import json
import io
from typing import List, Dict, Optional
from PIL import Image
from pdf2image import convert_from_bytes
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
    
    prompt = """You are an expert at extracting exam questions from academic documents. 
Analyze this exam document and extract ALL questions in a structured format.

IMPORTANT INSTRUCTIONS:
1. Skip instruction pages, cover pages, and logistics (scantron instructions, etc.)
2. Extract ONLY actual exam questions
3. Preserve all mathematical notation, equations, and LaTeX formatting
4. Include diagrams, images, and visual elements in your description
5. Number questions correctly (handle subparts like 1a, 1b, etc.)

Return a JSON object with this EXACT structure:
{
  "questions": [
    {
      "question_number": "1",
      "question_text": "Full question text with all details, preserving LaTeX notation like $\\int_0^1 x^2 dx$ or $$\\frac{d}{dx}\\left(\\sin(x)\\right) = \\cos(x)$$",
      "question_type": "multiple_choice|free_response|true_false|short_answer",
      "options": ["Option A", "Option B", ...] or null if not multiple choice,
      "correct_answer": "Answer or solution" or null if not provided,
      "page_number": 2,
      "has_diagram": true/false,
      "diagram_description": "Description of any diagrams or images",
      "difficulty_estimate": 1-5,
      "topics": ["topic1", "topic2", ...],
      "subparts": [
        {
          "subpart_number": "1a",
          "subpart_text": "Text for subpart 1a",
          "options": [...],
          "correct_answer": "..."
        }
      ] or null
    }
  ],
  "total_pages": 10,
  "instruction_pages_skipped": [1]
}

For LaTeX/math notation:
- Use $...$ for inline math: $x^2 + y^2 = r^2$
- Use $$...$$ for display math: $$\\int_0^{\\infty} e^{-x} dx = 1$$
- Preserve all mathematical symbols exactly as they appear

Return ONLY the JSON, no markdown formatting, no explanations."""

    try:
        questions_data = []
        total_pages = 0
        instruction_pages = []
        
        if file_type == 'pdf':
            # Convert PDF to images
            print("[GEMINI_EXTRACT] Converting PDF to images...")
            try:
                pdf_images = convert_from_bytes(file_bytes, dpi=150)  # Lower DPI for faster processing
                total_pages = len(pdf_images)
                print(f"[GEMINI_EXTRACT] Converted {total_pages} pages to images")
            except Exception as e:
                print(f"[GEMINI_EXTRACT] Error converting PDF to images: {e}")
                import traceback
                traceback.print_exc()
                return {"error": f"Failed to convert PDF to images: {str(e)}"}
            
            # Limit pages to prevent timeout (process max 20 pages)
            max_pages_to_process = 20
            if total_pages > max_pages_to_process:
                print(f"[GEMINI_EXTRACT] Warning: PDF has {total_pages} pages, processing first {max_pages_to_process} pages only")
                pdf_images = pdf_images[:max_pages_to_process]
                total_pages = max_pages_to_process
            
            # Process each page with Gemini
            for page_idx, page_image in enumerate(pdf_images):
                page_num = page_idx + 1
                print(f"[GEMINI_EXTRACT] Processing page {page_num}/{total_pages} with Gemini...")
                
                try:
                    # Send page to Gemini with shorter timeout to prevent 502s
                    page_prompt = prompt + f"\n\nThis is page {page_num} of {total_pages}. Extract questions from this page only."
                    response = vision_model.generate_content(
                        [page_prompt, page_image],
                        request_options={"timeout": 20}  # Reduced from 30 to 20 seconds
                    )
                    
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
                    page_data = json.loads(response_text)
                    
                    # Check if this page was skipped (instruction page)
                    if page_data.get("instruction_pages_skipped"):
                        if page_num in page_data["instruction_pages_skipped"]:
                            print(f"[GEMINI_EXTRACT] Page {page_num} detected as instructions - skipping")
                            instruction_pages.append(page_num)
                            continue
                    
                    # Add questions from this page
                    if page_data.get("questions"):
                        for q in page_data["questions"]:
                            q["page_number"] = page_num
                            questions_data.append(q)
                        print(f"[GEMINI_EXTRACT] Extracted {len(page_data.get('questions', []))} questions from page {page_num}")
                    
                except json.JSONDecodeError as e:
                    print(f"[GEMINI_EXTRACT] Error parsing JSON from page {page_num}: {e}")
                    print(f"[GEMINI_EXTRACT] Response text: {response_text[:500]}")
                    import traceback
                    traceback.print_exc()
                    # Don't continue silently - return error for first page failure
                    if page_num == 1:
                        return {"error": f"Failed to parse Gemini response from page {page_num}. The AI may have returned invalid JSON. Try uploading again."}
                    continue
                except Exception as e:
                    print(f"[GEMINI_EXTRACT] Error processing page {page_num}: {e}")
                    import traceback
                    traceback.print_exc()
                    # Return error for first page failure
                    if page_num == 1:
                        return {"error": f"Failed to process page {page_num}: {str(e)}"}
                    continue
        
        elif file_type in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            # Single image
            print("[GEMINI_EXTRACT] Processing single image with Gemini...")
            image = Image.open(io.BytesIO(file_bytes))
            total_pages = 1
            
            try:
                response = vision_model.generate_content(
                    [prompt, image],
                    request_options={"timeout": 30}
                )
                
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
                page_data = json.loads(response_text)
                
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
        
        print(f"[GEMINI_EXTRACT] Total: {len(questions_data)} questions extracted from {total_pages} pages")
        
        return {
            "questions": questions_data,
            "total_pages": total_pages,
            "instruction_pages_skipped": instruction_pages
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


def save_exam_questions_to_db(user_id: int, exam_name: str, file_type: str, questions_data: List[Dict], total_pages: int) -> Dict:
    """
    Save extracted questions to the database.
    
    Args:
        user_id: User ID
        exam_name: Name of the exam
        file_type: File type ('pdf' or image extension)
        questions_data: List of question dictionaries from Gemini
        total_pages: Total number of pages
    
    Returns:
        Dict with 'exam_id' and 'total_questions'
    """
    db = get_db()
    try:
        # Create exam record
        exam_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'exams', str(user_id))
        os.makedirs(exam_dir, exist_ok=True)
        
        db.cursor.execute('''
            INSERT INTO exams (user_id, exam_name, file_type, total_pages, total_questions)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, exam_name, file_type, total_pages, len(questions_data)))
        db.conn.commit()
        exam_id = db.cursor.lastrowid
        
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
                "topics": q.get("topics", []),
                "subparts": q.get("subparts")
            })
            
            # Insert main question
            db.cursor.execute('''
                INSERT INTO exam_questions 
                (exam_id, page_number, question_number, raw_text, solved_json, difficulty, topics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                exam_id,
                q.get("page_number", 1),
                q.get("question_number", "?"),
                q.get("question_text", ""),  # Store in raw_text for display
                question_json,  # Store full structured data in solved_json
                q.get("difficulty_estimate", 3),
                json.dumps({"topics": q.get("topics", [])})
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

