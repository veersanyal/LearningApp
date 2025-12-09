"""
OCR Module for Exam Question Extraction
Handles PDF to image conversion, OCR, and question segmentation
"""

import os
import re
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
import io
import json
from typing import List, Dict, Tuple, Optional


def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[Image.Image]:
    """
    Convert PDF bytes to PIL Images.
    
    Args:
        pdf_bytes: PDF file as bytes
        dpi: Resolution for conversion (higher = better quality but slower)
    
    Returns:
        List of PIL Image objects, one per page
    """
    try:
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        return images
    except Exception as e:
        print(f"[OCR] Error converting PDF to images: {e}")
        raise


def ocr_image(image: Image.Image, preserve_math: bool = True) -> Tuple[str, float]:
    """
    Perform OCR on an image, preserving math notation.
    
    Args:
        image: PIL Image to OCR
        preserve_math: Whether to use math-aware OCR settings
    
    Returns:
        Tuple of (extracted_text, confidence_score)
    """
    try:
        # Configure Tesseract for better math/equation recognition
        config = '--psm 6'  # Assume uniform block of text
        if preserve_math:
            # Add math-specific config
            config += ' -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz+-=()[]{}.,;:!?/\\|_^<>∫∑∏√∞αβγδεθλμπσφωΔ∇∂∮⟨⟩·×÷±≤≥≠≈∝∈∉⊂⊃∪∩∅∀∃∴∵'
        
        # Perform OCR
        text = pytesseract.image_to_string(image, config=config)
        
        # Get confidence (average confidence of all words)
        try:
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        except:
            avg_confidence = 0.0
        
        return text.strip(), avg_confidence
    except Exception as e:
        print(f"[OCR] Error performing OCR: {e}")
        return "", 0.0


def is_instruction_page(text: str) -> bool:
    """
    Detect if a page contains exam instructions rather than questions.
    
    Args:
        text: OCR text from a page
    
    Returns:
        True if this appears to be an instruction/logistics page
    """
    text_lower = text.lower()
    
    # Keywords that indicate instruction/logistics pages
    instruction_keywords = [
        'scantron', 'fill in', 'bubble', 'pencil', '#2 pencil',
        'ta name', 'course number', 'section number', 'student id',
        'exam instructions', 'exam rules', 'academic integrity',
        'prohibited', 'not allowed', 'do not', 'must bring',
        'exam format', 'total questions', 'point value', 'time limit',
        'leave the room', 'electronic devices', 'notes', 'calculator',
        'show your work', 'write clearly', 'good luck'
    ]
    
    # Count how many instruction keywords appear
    keyword_count = sum(1 for keyword in instruction_keywords if keyword in text_lower)
    
    # If 3+ instruction keywords found, likely an instruction page
    if keyword_count >= 3:
        return True
    
    # Check for instruction-like patterns
    instruction_patterns = [
        r'scantron\s+sheet',
        r'fill\s+in\s+the',
        r'use\s+a\s+#2',
        r'course\s+number',
        r'ta\'?s?\s+name',
        r'section\s+number',
        r'student\s+id',
        r'exam\s+instructions',
        r'not\s+allowed',
        r'prohibited',
        r'must\s+bring'
    ]
    
    pattern_matches = sum(1 for pattern in instruction_patterns if re.search(pattern, text_lower))
    
    # If 2+ patterns match, likely instruction page
    if pattern_matches >= 2:
        return True
    
    # Check if page is mostly short lines (typical of instruction formatting)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 0:
        avg_line_length = sum(len(line) for line in lines) / len(lines)
        # Instruction pages often have short, bullet-point style lines
        if avg_line_length < 40 and len(lines) > 5:
            return True
    
    return False


def segment_questions(text: str, page_num: int = 0) -> List[Dict[str, any]]:
    """
    Segment OCR text into individual questions.
    Skips instruction/logistics pages.
    
    Args:
        text: Full OCR text from a page
        page_num: Page number for reference
    
    Returns:
        List of question dictionaries with question_number and text
    """
    # Skip instruction pages
    if is_instruction_page(text):
        print(f"[OCR] Page {page_num} appears to be instructions/logistics - skipping")
        return []
    
    questions = []
    
    # Patterns to identify question starts
    # Matches: "1.", "Q1", "Question 1", "(1)", "1)", etc.
    question_patterns = [
        r'^(\d+)[.)]\s+',  # "1." or "1)"
        r'^[Qq]uestion\s+(\d+)[.:]?\s+',  # "Question 1:"
        r'^[Qq](\d+)[.:]?\s+',  # "Q1:" or "q1."
        r'^\((\d+)\)\s+',  # "(1)"
        r'^(\d+)\s+',  # "1 " at start of line
    ]
    
    lines = text.split('\n')
    current_question = None
    current_text = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check if this line starts a new question
        is_question_start = False
        question_num = None
        
        for pattern in question_patterns:
            match = re.match(pattern, line)
            if match:
                is_question_start = True
                question_num = match.group(1)
                break
        
        if is_question_start:
            # Save previous question if exists
            if current_question and current_text:
                questions.append({
                    'question_number': current_question,
                    'text': '\n'.join(current_text),
                    'page': page_num
                })
            
            # Start new question
            current_question = question_num
            # Remove question number prefix from line
            for pattern in question_patterns:
                line = re.sub(pattern, '', line).strip()
            current_text = [line] if line else []
        else:
            # Continuation of current question
            if current_question:
                current_text.append(line)
            else:
                # No question number found yet, might be preamble
                # Only treat as question if it has strong question indicators
                question_indicators = ['compute', 'find', 'solve', 'calculate', 'determine', 
                                     'evaluate', 'prove', 'show', 'what is', 'which of', 
                                     'how many', 'integral', 'derivative', 'limit', 'matrix',
                                     'vector', 'function', 'equation', 'graph']
                
                # Check if line contains math/question content
                has_math_symbols = bool(re.search(r'[∫∑∏√∞αβγδεθλμπσφωΔ∇∂∮⟨⟩·×÷±≤≥≠≈∝∈∉⊂⊃∪∩∅∀∃∴∵]', line))
                has_question_keywords = any(keyword in line.lower() for keyword in question_indicators)
                has_math_notation = bool(re.search(r'[\(\)\[\]\{\}]', line)) and len(line) > 20
                
                if has_question_keywords or has_math_symbols or has_math_notation:
                    # Likely a question without explicit numbering
                    if not current_question:
                        current_question = 'unnumbered'
                        current_text = [line]
                    else:
                        current_text.append(line)
                elif current_question == 'unnumbered':
                    current_text.append(line)
    
    # Save last question
    if current_question and current_text:
        questions.append({
            'question_number': current_question,
            'text': '\n'.join(current_text),
            'page': page_num
        })
    
    # Filter out questions that look like instructions
    filtered_questions = []
    for q in questions:
        q_text = q['text'].lower()
        # Skip if it looks like instructions
        if is_instruction_page(q_text):
            continue
        # Skip if too short (likely not a real question)
        if len(q['text'].strip()) < 30:
            continue
        # Skip if contains too many instruction keywords
        instruction_keywords = ['scantron', 'fill in', 'bubble', 'pencil', 'ta name', 
                              'course number', 'section', 'student id', 'exam instructions']
        if sum(1 for kw in instruction_keywords if kw in q_text) >= 2:
            continue
        filtered_questions.append(q)
    
    # If no questions found after filtering, don't create a default one
    # (it was likely an instruction page)
    return filtered_questions


def process_exam_file(file_bytes: bytes, file_type: str, user_id: int, exam_name: str) -> Dict:
    """
    Process an exam file (PDF or image) and extract questions.
    
    Args:
        file_bytes: File content as bytes
        file_type: 'pdf' or 'image'
        user_id: User ID for file storage
        exam_name: Name of the exam
    
    Returns:
        Dictionary with exam_id, questions list, and metadata
    """
    from database import get_db
    
    questions_data = []
    page_images = []  # List of (page_num, image) tuples
    
    try:
        if file_type == 'pdf':
            # Convert PDF to images
            print(f"[OCR] Converting PDF to images...")
            pdf_images = pdf_to_images(file_bytes)
            print(f"[OCR] Converted {len(pdf_images)} pages to images")
            
            # OCR each page
            for page_idx, image in enumerate(pdf_images):
                print(f"[OCR] Processing page {page_idx + 1}...")
                text, confidence = ocr_image(image, preserve_math=True)
                print(f"[OCR] Page {page_idx + 1}: {len(text)} chars, confidence: {confidence:.1f}%")
                
                # Quick check: skip if this looks like an instruction page
                if is_instruction_page(text):
                    print(f"[OCR] Page {page_idx + 1} detected as instructions - skipping OCR segmentation")
                    # Still store image in case user wants to see it
                    page_images.append((page_idx + 1, image))
                    continue
                
                # Segment questions from this page
                page_questions = segment_questions(text, page_num=page_idx + 1)
                if page_questions:
                    questions_data.extend(page_questions)
                    # Store image for questions on this page
                    page_images.append((page_idx + 1, image))
                else:
                    print(f"[OCR] No questions found on page {page_idx + 1}")
        
        elif file_type in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
            # Single image
            image = Image.open(io.BytesIO(file_bytes))
            print(f"[OCR] Processing single image...")
            text, confidence = ocr_image(image, preserve_math=True)
            print(f"[OCR] Image: {len(text)} chars, confidence: {confidence:.1f}%")
            
            # Segment questions
            page_questions = segment_questions(text, page_num=1)
            questions_data.extend(page_questions)
            page_images.append((1, image))
        
        print(f"[OCR] Extracted {len(questions_data)} questions total")
        
        # Save exam and questions to database
        db = get_db()
        try:
            # Create exam record
            exam_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'exams', str(user_id))
            os.makedirs(exam_dir, exist_ok=True)
            
            db.cursor.execute('''
                INSERT INTO exams (user_id, exam_name, file_type, total_pages, total_questions)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, exam_name, file_type, len(page_images), len(questions_data)))
            db.conn.commit()
            exam_id = db.cursor.lastrowid
            
            # Save images and create question records
            question_ids = []
            for q_idx, question in enumerate(questions_data):
                # Save image for this question if available
                image_path = None
                page_num = question.get('page', 1)
                
                # Find corresponding image
                for img_page, img_obj in page_images:
                    if img_page == page_num:
                        # Save image
                        image_filename = f"exam_{exam_id}_page_{page_num}_q_{question['question_number']}.png"
                        image_path = os.path.join(exam_dir, image_filename)
                        img_obj.save(image_path, 'PNG')
                        # Store relative path for serving
                        image_path = f"exams/{user_id}/{image_filename}"
                        break
                
                # Insert question
                db.cursor.execute('''
                    INSERT INTO exam_questions 
                    (exam_id, page_number, question_number, raw_text, ocr_confidence, image_path)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    exam_id,
                    page_num,
                    question['question_number'],
                    question['text'],
                    confidence if 'confidence' in locals() else 0.0,
                    image_path
                ))
                db.conn.commit()
                question_ids.append(db.cursor.lastrowid)
            
            return {
                'exam_id': exam_id,
                'total_questions': len(questions_data),
                'total_pages': len(page_images),
                'questions': questions_data,
                'question_ids': question_ids
            }
        finally:
            db.disconnect()
    
    except Exception as e:
        print(f"[OCR] Error processing exam file: {e}")
        import traceback
        traceback.print_exc()
        raise

