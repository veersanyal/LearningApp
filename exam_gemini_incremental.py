"""
Incremental exam question extraction - processes 1 page at a time and saves incrementally.
"""

import os
import json
import io
import sys
import re
from typing import List, Dict, Optional
from PIL import Image
from pdf2image import convert_from_bytes
from database import get_db

# Force stdout/stderr to be unbuffered
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None


def process_exam_incremental(file_bytes: bytes, file_type: str, exam_id: int, vision_model, 
                             callback=None) -> Dict:
    """
    Process exam incrementally - 1 page at a time, saving as we go.
    
    Args:
        file_bytes: File content as bytes
        file_type: 'pdf' or image extension
        exam_id: Exam ID to save questions to
        vision_model: Initialized Gemini vision model
        callback: Optional callback function(status, progress) called after each chunk
    
    Returns:
        Dict with 'total_questions', 'total_pages', 'errors'
    """
    if not vision_model:
        return {"error": "Vision model not initialized"}
    
    prompt = """You are an expert at extracting exam questions from academic documents. 
Analyze this exam document and extract ALL questions in a structured format.

CRITICAL: Extract EVERY question on these pages. Do not skip ANY pages. Look at EVERY page and extract ALL questions you find, regardless of whether there are instructions or other text on the page.

IMPORTANT INSTRUCTIONS:
1. Extract ALL actual exam questions - look for numbered questions (1, 2, 3...), multiple choice options (A, B, C...), and any question text
2. IGNORE instruction text, headers, footers, and other non-question content - but STILL extract questions from those pages if they have questions on them - not all pages need to have questions on them
3. Preserve all mathematical notation, equations, and LaTeX formatting exactly as shown
4. For diagrams/images: Provide a detailed description that would allow someone to recreate the diagram. Include all labels, axes, curves, shapes, and their relationships
5. Number questions correctly (handle subparts like 1a, 1b, etc.)
6. For multiple choice questions, extract ALL options (A, B, C, D, E, F, etc.) exactly as written

Return a JSON object with this EXACT structure:
{
  "questions": [
    {
      "question_number": "1",
      "question_text": "Full question text with all details, preserving LaTeX notation like $\\int_0^1 x^2 dx$ or $$\\frac{d}{dx}\\left(\\sin(x)\\right) = \\cos(x)$$",
      "question_type": "multiple_choice|free_response|true_false|short_answer",
      "options": ["Option A", "Option B", ...] or null if not multiple choice,
      "page_number": 2,
      "has_diagram": true/false,
      "diagram_description": "Description of any diagrams or images",
      "topics": ["topic1", "topic2", ...],
      "subparts": [
        {
          "subpart_number": "1a",
          "subpart_text": "Text for subpart 1a",
          "options": [...]
        }
      ] or null
    }
  ]
}

For LaTeX/math notation:
- Use $...$ for inline math: $x^2 + y^2 = r^2$
- Use $$...$$ for display math: $$\\int_0^{\\infty} e^{-x} dx = 1$$
- Preserve all mathematical symbols exactly as they appear

Return ONLY the JSON, no markdown formatting, no explanations."""

    try:
        print(f"[INCREMENTAL] ========== STARTING INCREMENTAL PROCESSING ==========", flush=True)
        print(f"[INCREMENTAL] Starting incremental processing for exam {exam_id}", flush=True)
        print(f"[INCREMENTAL] Vision model available: {vision_model is not None}", flush=True)
        sys.stdout.flush()
        if not vision_model:
            print(f"[INCREMENTAL] ERROR: Vision model is None!", flush=True)
            sys.stdout.flush()
            return {"error": "Vision model not initialized"}
        
        total_questions = 0
        total_pages = 0
        errors = []
        db = get_db()
        
        try:
            if file_type == 'pdf':
                # Convert PDF to images
                print("[INCREMENTAL] Converting PDF to images...", flush=True)
                try:
                    pdf_images = convert_from_bytes(file_bytes, dpi=150)
                    total_pages = len(pdf_images)
                    print(f"[INCREMENTAL] Converted {total_pages} pages to images", flush=True)
                    print(f"[INCREMENTAL] Will process ALL {total_pages} pages in chunks of 2", flush=True)
                except Exception as e:
                    print(f"[INCREMENTAL] Error converting PDF: {e}", flush=True)
                    return {"error": f"Failed to convert PDF: {str(e)}"}
                
                # Update exam with total pages
                db.cursor.execute('''
                    UPDATE exams SET total_pages = ? WHERE exam_id = ?
                ''', (total_pages, exam_id))
                db.conn.commit()
                print(f"[INCREMENTAL] Updated exam {exam_id} with total_pages = {total_pages}", flush=True)
                
                # Process one page at a time - process ALL pages
                for page_idx in range(total_pages):
                    page_num = page_idx + 1
                    page_image = pdf_images[page_idx]
                    
                    print(f"[INCREMENTAL] ========== Processing page {page_num} of {total_pages} ==========", flush=True)
                    
                    # Update progress in database
                    db.cursor.execute('''
                        UPDATE exams SET total_questions = ? WHERE exam_id = ?
                    ''', (-page_num, exam_id))  # Negative indicates current page being processed
                    db.conn.commit()
                    
                    # Call callback if provided
                    if callback:
                        callback({
                            "status": "extracting",
                            "current_page": page_num,
                            "total_pages": total_pages,
                            "questions_extracted": total_questions
                        })
                    
                    page_questions = []
                    response_text = None
                    try:
                        page_prompt = prompt + f"\n\nThis is page {page_num} of {total_pages}. Extract questions from this page only. Make sure to set page_number to {page_num} for all questions."
                        print(f"[INCREMENTAL] Sending page {page_num} to Gemini...", flush=True)
                        response = vision_model.generate_content(
                            [page_prompt, page_image],
                            request_options={"timeout": 20}
                        )
                        print(f"[INCREMENTAL] Received response from Gemini for page {page_num}", flush=True)
                            
                        if not response or not hasattr(response, 'text'):
                            print(f"[INCREMENTAL] ERROR: Invalid response from Gemini for page {page_num}", flush=True)
                            errors.append(f"Invalid response from Gemini for page {page_num}")
                            continue
                            
                        response_text = response.text.strip()
                        print(f"[INCREMENTAL] Response length: {len(response_text)} characters", flush=True)
                        # Remove markdown code blocks
                        if response_text.startswith("```"):
                            parts = response_text.split("```")
                            if len(parts) >= 2:
                                response_text = parts[1]
                                if response_text.startswith("json"):
                                    response_text = response_text[4:]
                        response_text = response_text.strip()
                        
                        # Parse JSON response with better error handling for LaTeX backslashes
                        print(f"[INCREMENTAL] Parsing JSON response from page {page_num}...", flush=True)
                        try:
                            page_data = json.loads(response_text)
                        except json.JSONDecodeError as json_err:
                            # Try to fix common JSON issues with LaTeX backslashes
                            print(f"[INCREMENTAL] JSON parse error at position {json_err.pos}: {json_err.msg}", flush=True)
                            print(f"[INCREMENTAL] Attempting to fix escaped backslashes in LaTeX notation...", flush=True)
                            
                            # Fix unescaped backslashes in LaTeX notation within string values
                            # Strategy: Find all string values and escape backslashes that aren't part of valid JSON escape sequences
                            def fix_json_backslashes(text):
                                """Fix unescaped backslashes in JSON string values."""
                                # Find all string values (between quotes)
                                result = []
                                i = 0
                                in_string = False
                                escape_next = False
                                
                                while i < len(text):
                                    char = text[i]
                                    
                                    if escape_next:
                                        # We're escaping the next character
                                        result.append(char)
                                        escape_next = False
                                        i += 1
                                        continue
                                    
                                    if char == '\\':
                                        if in_string:
                                            # Check if this is a valid JSON escape sequence
                                            if i + 1 < len(text):
                                                next_char = text[i + 1]
                                                # Valid JSON escapes: ", \, /, b, f, n, r, t, u
                                                if next_char in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                                                    result.append('\\')
                                                    result.append(next_char)
                                                    i += 2
                                                    continue
                                                else:
                                                    # Invalid escape - double it
                                                    result.append('\\\\')
                                                    result.append(next_char)
                                                    i += 2
                                                    continue
                                            else:
                                                # Backslash at end - escape it
                                                result.append('\\\\')
                                                i += 1
                                        else:
                                            # Not in string, keep as is
                                            result.append(char)
                                            i += 1
                                    elif char == '"':
                                        # Toggle string state
                                        in_string = not in_string
                                        result.append(char)
                                        i += 1
                                    else:
                                        result.append(char)
                                        i += 1
                                
                                return ''.join(result)
                            
                            fixed_text = fix_json_backslashes(response_text)
                            try:
                                page_data = json.loads(fixed_text)
                                print(f"[INCREMENTAL] ✓ Successfully parsed after fixing backslashes", flush=True)
                            except json.JSONDecodeError as json_err2:
                                print(f"[INCREMENTAL] Still failed after fixing backslashes: {json_err2.msg} at position {json_err2.pos}", flush=True)
                                # Log the problematic area
                                error_start = max(0, json_err2.pos - 100)
                                error_end = min(len(fixed_text), json_err2.pos + 100)
                                print(f"[INCREMENTAL] Problematic area: {fixed_text[error_start:error_end]}", flush=True)
                                raise json_err  # Re-raise original error
                        print(f"[INCREMENTAL] Parsed response, found {len(page_data.get('questions', []))} questions", flush=True)
                        
                        # Add ALL questions from this page - NO SKIPPING
                        if page_data.get("questions"):
                            questions_found = page_data["questions"]
                            print(f"[INCREMENTAL] Found {len(questions_found)} questions in response from page {page_num}", flush=True)
                            
                            for q in questions_found:
                                # Ensure page_number is set correctly
                                if not q.get("page_number"):
                                    q["page_number"] = page_num
                                    print(f"[INCREMENTAL] Question {q.get('question_number', '?')} missing page_number, setting to {page_num}", flush=True)
                                
                                # Validate page_number matches current page
                                if q["page_number"] != page_num:
                                    print(f"[INCREMENTAL] WARNING: Question {q.get('question_number', '?')} has page_number {q['page_number']} but we're processing page {page_num}, adjusting to {page_num}", flush=True)
                                    q["page_number"] = page_num
                                
                                # NO SKIPPING - add all questions found
                                print(f"[INCREMENTAL] Adding question {q.get('question_number', '?')} from page {q.get('page_number', '?')}", flush=True)
                                page_questions.append(q)
                        else:
                            print(f"[INCREMENTAL] ⚠️ WARNING: No questions found in response from page {page_num}", flush=True)
                            print(f"[INCREMENTAL] This could mean: 1) Gemini didn't find questions on this page, 2) Response parsing failed, or 3) Page is truly empty", flush=True)
                    
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse JSON from page {page_num}: {str(e)}"
                        print(f"[INCREMENTAL] ERROR: {error_msg}", flush=True)
                        try:
                            print(f"[INCREMENTAL] Response preview (first 500 chars): {response_text[:500]}...", flush=True)
                            print(f"[INCREMENTAL] Full response length: {len(response_text)}", flush=True)
                        except Exception as print_err:
                            print(f"[INCREMENTAL] Could not get response text: {print_err}", flush=True)
                        errors.append(error_msg)
                        sys.stdout.flush()
                        # Still try to save any questions we might have extracted before the error
                        if page_questions:
                            try:
                                saved_count = save_questions_chunk(db, exam_id, page_questions)
                                total_questions += saved_count
                                db.cursor.execute('''
                                    UPDATE exams SET total_questions = ? WHERE exam_id = ?
                                ''', (total_questions, exam_id))
                                db.conn.commit()
                            except:
                                pass
                        continue
                    except Exception as e:
                        error_msg = f"Error processing page {page_num}: {str(e)}"
                        print(f"[INCREMENTAL] EXCEPTION: {error_msg}", flush=True)
                        import traceback
                        traceback.print_exc()
                        print(f"[INCREMENTAL] Exception type: {type(e).__name__}", flush=True)
                        errors.append(error_msg)
                        sys.stdout.flush()
                        # Still try to save any questions we might have extracted before the error
                        if page_questions:
                            try:
                                saved_count = save_questions_chunk(db, exam_id, page_questions)
                                total_questions += saved_count
                                db.cursor.execute('''
                                    UPDATE exams SET total_questions = ? WHERE exam_id = ?
                                ''', (total_questions, exam_id))
                                db.conn.commit()
                            except:
                                pass
                        continue
                    
                    # Save this page's questions to database immediately
                    if page_questions:
                        print(f"[INCREMENTAL] Saving {len(page_questions)} questions from page {page_num}...", flush=True)
                        saved_count = save_questions_chunk(db, exam_id, page_questions)
                        total_questions += saved_count
                        print(f"[INCREMENTAL] ✓ Saved {saved_count} questions from page {page_num} (total: {total_questions})", flush=True)
                        
                        # Update exam question count
                        db.cursor.execute('''
                            UPDATE exams SET total_questions = ? WHERE exam_id = ?
                        ''', (total_questions, exam_id))
                        db.conn.commit()
                        print(f"[INCREMENTAL] Updated exam {exam_id} with {total_questions} total questions", flush=True)
                    else:
                        print(f"[INCREMENTAL] ⚠ No questions to save from page {page_num}", flush=True)
            
            elif file_type in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                # Single image - process normally
                image = Image.open(io.BytesIO(file_bytes))
                total_pages = 1
                
                response = vision_model.generate_content(
                    [prompt, image],
                    request_options={"timeout": 20}
                )
                
                response_text = response.text.strip()
                if response_text.startswith("```"):
                    parts = response_text.split("```")
                    if len(parts) >= 2:
                        response_text = parts[1]
                        if response_text.startswith("json"):
                            response_text = response_text[4:]
                response_text = response_text.strip()
                
                page_data = json.loads(response_text)
                
                if page_data.get("questions"):
                    for q in page_data["questions"]:
                        q["page_number"] = 1
                    saved_count = save_questions_chunk(db, exam_id, page_data["questions"])
                    total_questions = saved_count
                    
                    db.cursor.execute('''
                        UPDATE exams SET total_pages = ?, total_questions = ? WHERE exam_id = ?
                    ''', (1, total_questions, exam_id))
                    db.conn.commit()
            
            # Final summary
            print(f"[INCREMENTAL] ========== EXTRACTION COMPLETE ==========", flush=True)
            print(f"[INCREMENTAL] Total pages in PDF: {total_pages}", flush=True)
            print(f"[INCREMENTAL] Total questions extracted: {total_questions}", flush=True)
            print(f"[INCREMENTAL] ✓ Successfully processed all {total_pages} pages", flush=True)
            
            # Update exam with final question count (positive number indicates extraction complete)
            db.cursor.execute('''
                UPDATE exams SET total_questions = ? WHERE exam_id = ?
            ''', (total_questions, exam_id))
            db.conn.commit()
            
            if errors:
                print(f"[INCREMENTAL] Errors encountered: {len(errors)}", flush=True)
                for error in errors:
                    print(f"[INCREMENTAL]   - {error}", flush=True)
            
            return {
                "total_questions": total_questions,
                "total_pages": total_pages,
                "errors": errors,
                "extraction_complete": True
            }
        
        finally:
            db.disconnect()
    
    except Exception as e:
        print(f"[INCREMENTAL] Top-level error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to extract questions: {str(e)}"}


def save_questions_chunk(db, exam_id: int, questions: List[Dict]) -> int:
    """Save a chunk of questions to the database."""
    saved_count = 0
    
    for q in questions:
        try:
            # Store question data as JSON (correct_answer will be added during analysis)
            question_json = json.dumps({
                "question_text": q.get("question_text", ""),
                "question_type": q.get("question_type", "free_response"),
                "options": q.get("options"),
                "has_diagram": q.get("has_diagram", False),
                "diagram_description": q.get("diagram_description"),
                "topics": q.get("topics", []),
                "subparts": q.get("subparts")
            })
            
            # Insert main question (difficulty will be NULL until analyzed)
            db.cursor.execute('''
                INSERT INTO exam_questions 
                (exam_id, page_number, question_number, raw_text, solved_json, difficulty, topics_json, diagram_note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                exam_id,
                q.get("page_number", 1),
                q.get("question_number", "?"),
                q.get("question_text", ""),
                question_json,
                None,  # Difficulty will be set during analysis phase
                json.dumps({"topics": q.get("topics", [])}),
                q.get("diagram_description")  # Store diagram description in diagram_note column
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
                        None,  # Difficulty will be set during analysis phase
                        json.dumps({"topics": q.get("topics", [])})
                    ))
            
            saved_count += 1
        
        except Exception as e:
            print(f"[INCREMENTAL] Error saving question: {e}")
            continue
    
    db.conn.commit()
    return saved_count

