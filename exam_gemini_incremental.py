"""
Incremental exam question extraction - processes 2 pages at a time and saves incrementally.
"""

import os
import json
import io
from typing import List, Dict, Optional
from PIL import Image
from pdf2image import convert_from_bytes
from database import get_db


def process_exam_incremental(file_bytes: bytes, file_type: str, exam_id: int, vision_model, 
                             callback=None) -> Dict:
    """
    Process exam incrementally - 2 pages at a time, saving as we go.
    
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
  "instruction_pages_skipped": [1] or []
}

For LaTeX/math notation:
- Use $...$ for inline math: $x^2 + y^2 = r^2$
- Use $$...$$ for display math: $$\\int_0^{\\infty} e^{-x} dx = 1$$
- Preserve all mathematical symbols exactly as they appear

Return ONLY the JSON, no markdown formatting, no explanations."""

    try:
        total_questions = 0
        total_pages = 0
        errors = []
        db = get_db()
        
        try:
            if file_type == 'pdf':
                # Convert PDF to images
                print("[INCREMENTAL] Converting PDF to images...")
                try:
                    pdf_images = convert_from_bytes(file_bytes, dpi=150)
                    total_pages = len(pdf_images)
                    print(f"[INCREMENTAL] Converted {total_pages} pages to images")
                except Exception as e:
                    print(f"[INCREMENTAL] Error converting PDF: {e}")
                    return {"error": f"Failed to convert PDF: {str(e)}"}
                
                # Update exam with total pages
                db.cursor.execute('''
                    UPDATE exams SET total_pages = ? WHERE exam_id = ?
                ''', (total_pages, exam_id))
                db.conn.commit()
                
                # Process 2 pages at a time
                chunk_size = 2
                for chunk_start in range(0, total_pages, chunk_size):
                    chunk_end = min(chunk_start + chunk_size, total_pages)
                    chunk_pages = list(range(chunk_start + 1, chunk_end + 1))
                    
                    print(f"[INCREMENTAL] Processing pages {chunk_pages[0]}-{chunk_pages[-1]} of {total_pages}...")
                    
                    # Process 2 pages together for better context
                    chunk_questions = []
                    page_num1 = chunk_start + 1
                    page_image1 = pdf_images[chunk_start]
                    
                    try:
                        if chunk_end - chunk_start == 2:
                            # Process 2 pages together
                            page_num2 = chunk_start + 2
                            page_image2 = pdf_images[chunk_start + 1]
                            page_prompt = prompt + f"\n\nThis is pages {page_num1}-{page_num2} of {total_pages}. Extract questions from BOTH pages. Make sure to include the page_number for each question."
                            
                            print(f"[INCREMENTAL] Sending pages {page_num1}-{page_num2} to Gemini...")
                            response = vision_model.generate_content(
                                [page_prompt, page_image1, page_image2],
                                request_options={"timeout": 25}
                            )
                        else:
                            # Only one page left
                            page_prompt = prompt + f"\n\nThis is page {page_num1} of {total_pages}. Extract questions from this page only."
                            print(f"[INCREMENTAL] Sending page {page_num1} to Gemini...")
                            response = vision_model.generate_content(
                                [page_prompt, page_image1],
                                request_options={"timeout": 20}
                            )
                            
                        response_text = response.text.strip()
                        # Remove markdown code blocks
                        if response_text.startswith("```"):
                            parts = response_text.split("```")
                            if len(parts) >= 2:
                                response_text = parts[1]
                                if response_text.startswith("json"):
                                    response_text = response_text[4:]
                        response_text = response_text.strip()
                        
                        # Parse JSON response
                        page_data = json.loads(response_text)
                        
                        # Check for skipped instruction pages
                        skipped_pages = page_data.get("instruction_pages_skipped", [])
                        
                        # Add questions from this chunk
                        if page_data.get("questions"):
                            for q in page_data["questions"]:
                                # Ensure page_number is set
                                if not q.get("page_number"):
                                    # Default to first page of chunk if not specified
                                    q["page_number"] = page_num1
                                # Skip if this question's page was marked as instructions
                                if q["page_number"] in skipped_pages:
                                    continue
                                chunk_questions.append(q)
                    
                    except json.JSONDecodeError as e:
                        error_msg = f"Failed to parse JSON from pages {chunk_pages[0]}-{chunk_pages[-1]}: {str(e)}"
                        print(f"[INCREMENTAL] {error_msg}")
                        print(f"[INCREMENTAL] Response preview: {response_text[:200]}...")
                        errors.append(error_msg)
                        continue
                    except Exception as e:
                        error_msg = f"Error processing pages {chunk_pages[0]}-{chunk_pages[-1]}: {str(e)}"
                        print(f"[INCREMENTAL] {error_msg}")
                        import traceback
                        traceback.print_exc()
                        errors.append(error_msg)
                        continue
                    
                    # Save this chunk's questions to database immediately
                    if chunk_questions:
                        saved_count = save_questions_chunk(db, exam_id, chunk_questions)
                        total_questions += saved_count
                        print(f"[INCREMENTAL] Saved {saved_count} questions from pages {chunk_pages[0]}-{chunk_pages[-1]}")
                        
                        # Update exam question count
                        db.cursor.execute('''
                            UPDATE exams SET total_questions = ? WHERE exam_id = ?
                        ''', (total_questions, exam_id))
                        db.conn.commit()
                    
                    # Callback for progress updates
                    if callback:
                        progress = (chunk_end / total_pages) * 100
                        callback({
                            "status": "processing",
                            "progress": progress,
                            "pages_processed": chunk_end,
                            "total_pages": total_pages,
                            "questions_extracted": total_questions
                        })
            
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
            
            return {
                "total_questions": total_questions,
                "total_pages": total_pages,
                "errors": errors
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
                (exam_id, page_num, question_number, raw_text, solved_json, difficulty, topics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                exam_id,
                q.get("page_number", 1),
                q.get("question_number", "?"),
                q.get("question_text", ""),
                question_json,
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
                        (exam_id, page_num, question_number, raw_text, solved_json, difficulty, topics_json)
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
            
            saved_count += 1
        
        except Exception as e:
            print(f"[INCREMENTAL] Error saving question: {e}")
            continue
    
    db.conn.commit()
    return saved_count

