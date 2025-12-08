# Assignment Requirements Verification

**Student:** Veer Sanyal  
**Course:** ENGR 13300  
**Project:** Advanced Learning App with Spaced Repetition  
**Date:** December 3, 2025

---

## Academic Integrity Statement

I have not used source code obtained from any unauthorized source, either modified or unmodified. Any algorithms implemented are based on documented educational theories (cited in code comments) and are my own implementation. This project represents my original work and understanding of programming concepts.

---

## Project Overview

An intelligent learning application that uses AI (Google Gemini) to extract topics from study materials and generate adaptive quiz questions. The system implements sophisticated learning algorithms including spaced repetition (SM-2), forgetting curves (Ebbinghaus), and adaptive difficulty adjustment.

---

## Requirement 1: Input ✓

### Implementation:
- **File Reading**: Loads topic data from JSON files (`example.json`)
- **User Input**: Accepts document uploads (PDF, images, text) via web interface
- **State Loading**: Reads saved progress from `user_progress.json`

### Code Locations:
```python
# user_state.py, lines 392-414
def load_user_state_from_file(filepath="user_progress.json"):
    """Load user state from a JSON file."""
    with open(filepath, 'r') as f:
        loaded_state = json.load(f)
    # ... processing code ...
```

```python
# topic_map.py, lines 26-30
def load_topics_from_file(filepath):
    """Load topics from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
```

### Demonstration:
Run `demo_advanced_features.py` - see "FILE INPUT/OUTPUT" section

---

## Requirement 2: Output ✓

### Implementation:
- **Console Output**: Progress reports, statistics, and analytics displayed to terminal
- **File Writing**: 
  - Saves user progress to `user_progress.json`
  - Exports analytics report to `learning_analytics.txt`
- **Web Interface**: Displays questions, feedback, and statistics

### Code Locations:
```python
# user_state.py, lines 366-389
def save_user_state_to_file(filepath="user_progress.json"):
    """Save user state to a JSON file for persistence."""
    with open(filepath, 'w') as f:
        json.dump(serializable_state, f, indent=2)
```

```python
# learning_analytics.py, lines 100-160
def export_analytics_report(filepath="learning_analytics.txt"):
    """Export comprehensive analytics report to text file."""
    with open(filepath, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("COMPREHENSIVE LEARNING ANALYTICS REPORT\n")
        # ... more output ...
```

### Demonstration:
- Run `demo_advanced_features.py` - creates `demo_progress.json` and `demo_analytics.txt`
- Files created: ✓ Verified

---

## Requirement 3: UDFs (User Defined Functions) ✓

### Main Program: `app.py`

### Functions Called from Separate Modules:

**From `topic_map.py`:**
1. `load_topics_from_file(filepath)`
2. `get_all_topics()`

**From `user_state.py`:**
3. `init_user_state()`
4. `record_answer(topic_id, correct)`
5. `get_target_difficulty(topic_id)`
6. `calculate_forgetting_factor(last_reviewed, mastery)`
7. `calculate_sm2_interval(easiness_factor, review_count, quality)`
8. `update_easiness_factor(current_ef, quality)`
9. `calculate_review_priority()`
10. `get_learning_velocity(topic_id)`
11. `save_user_state_to_file(filepath)`
12. `load_user_state_from_file(filepath)`
13. `generate_progress_report()`

**From `question_picker.py`:**
14. `pick_next_topic()`
15. `get_recommended_study_order()`

**From `learning_analytics.py`:**
16. `calculate_study_streak()`
17. `identify_weak_topics(threshold)`
18. `identify_strong_topics(threshold)`
19. `export_analytics_report(filepath)`

### Verification:
- ✓ Main program calls **15+ user-defined functions**
- ✓ At least one function from different file (`topic_map.py`, `user_state.py`, `question_picker.py`, `learning_analytics.py`)

---

## Requirement 4: Elements ✓

### a. FOR Loop

**Location 1:** `user_state.py`, lines 23-35
```python
def init_user_state():
    for topic in all_topics:  # FOR LOOP iterating through topics
        topic_id = topic["topic_id"]
        if topic_id not in user_state:
            # Initialize topic data
```

**Location 2:** `user_state.py`, lines 240-285
```python
def calculate_review_priority():
    for topic_id, stats in user_state.items():  # FOR LOOP
        # Calculate priority components
        mastery_factor = 1.0 - stats["mastery"]
        # ... nested IF statements inside FOR loop ...
```

**Location 3:** `learning_analytics.py`, lines 30-55
```python
def calculate_study_streak():
    for stats in user_state.values():  # FOR LOOP
        for attempt in stats["attempt_history"]:  # NESTED FOR LOOP
            timestamp_str = attempt["timestamp"]
```

### b. WHILE Loop

**Location 1:** `learning_analytics.py`, lines 59-75
```python
def calculate_study_streak():
    streak = 0
    index = 0
    while index < len(all_dates):  # WHILE LOOP
        current_date = all_dates[index]
        if current_date == expected_date:  # IF inside WHILE
            streak += 1
            index += 1
        else:
            break
```

**Location 2:** `user_state.py`, lines 310-323
```python
def get_learning_velocity(topic_id):
    correct_count = 0
    index = 0
    while index < len(recent_attempts):  # WHILE LOOP
        if recent_attempts[index]["correct"]:
            correct_count += 1
        index += 1
```

### c. List/Array/Vector/Matrix

**Location 1:** `user_state.py`, line 44
```python
"attempt_history": []  # LIST storing detailed history
```

**Location 2:** `user_state.py`, line 231
```python
priority_list = []  # LIST for priority scores
```

**Location 3:** `learning_analytics.py`, line 29
```python
all_dates = []  # LIST collecting review dates
```

### d. IF/ELIF/ELSE Decision Structure

**Location 1:** `user_state.py`, lines 189-208
```python
def get_target_difficulty(topic_id):
    if streak_wrong >= 3:
        return "easy"
    elif streak_correct >= 5 and mastery > 0.7:
        return "hard"
    elif mastery < 0.3:
        return "easy"
    elif mastery < 0.6:
        return "medium"
    # ... more elif branches ...
    else:
        return "hard"
```

**Location 2:** `user_state.py`, lines 113-128
```python
def calculate_sm2_interval(easiness_factor, review_count, quality):
    if quality < 3:
        interval = 1
        new_review_count = 0
    else:
        if review_count == 0:
            interval = 1
        elif review_count == 1:
            interval = 6
        else:
            # nested structure
```

---

## Requirement 5: Nested Structure ✓

### Example 1: FOR loop with nested IF statements

**Location:** `user_state.py`, lines 240-285
```python
def calculate_review_priority():
    for topic_id, stats in user_state.items():  # OUTER FOR
        if stats["attempts"] == 0:  # NESTED IF
            priority_list.append((topic_id, 100.0))
            continue
        
        if stats["next_review"] is not None:  # NESTED IF
            if time_until_review < 0:  # DOUBLY NESTED IF
                urgency_factor = min(2.0, abs(time_until_review) / 24.0)
            elif time_until_review < 24:  # NESTED ELIF
                urgency_factor = 0.5
            else:  # NESTED ELSE
                urgency_factor = 0.0
```

### Example 2: FOR loop nested inside FOR loop

**Location:** `learning_analytics.py`, lines 30-45
```python
for stats in user_state.values():  # OUTER FOR
    for attempt in stats["attempt_history"]:  # NESTED FOR
        timestamp_str = attempt["timestamp"]
        date = datetime.fromisoformat(timestamp_str).date()
        all_dates.append(date)
```

### Example 3: WHILE loop with nested IF-ELSE

**Location:** `learning_analytics.py`, lines 59-75
```python
while index < len(all_dates):  # WHILE LOOP
    current_date = all_dates[index]
    if current_date == expected_date:  # NESTED IF
        streak += 1
        expected_date = expected_date - timedelta(days=1)
        index += 1
    elif current_date < expected_date:  # NESTED ELIF
        break
    else:  # NESTED ELSE
        index += 1
```

---

## Requirement 6: Error Check ✓

### Error Check Algorithm 1: Input Validation for Mastery Value

**Location:** `user_state.py`, lines 66-72
```python
def calculate_forgetting_factor(last_reviewed, mastery):
    # ERROR CHECK: Validate inputs
    if last_reviewed is None:
        return 1.0
    
    if not isinstance(mastery, (int, float)) or mastery < 0 or mastery > 1:
        raise ValueError(f"Invalid mastery value: {mastery}. Must be between 0 and 1.")
```

**Error Handling:**
- Checks type: must be int or float
- Checks range: must be between 0 and 1
- Raises descriptive error message
- Does NOT exit program - allows user to correct

### Error Check Algorithm 2: Quality Score Validation (SM-2)

**Location:** `user_state.py`, lines 106-111
```python
def calculate_sm2_interval(easiness_factor, review_count, quality):
    # ERROR CHECK: Validate quality parameter
    if not isinstance(quality, (int, float)) or quality < 0 or quality > 5:
        raise ValueError(f"Invalid quality score: {quality}. Must be between 0 and 5.")
```

**Error Handling:**
- Validates quality is numeric
- Ensures quality is in valid range [0, 5]
- Provides descriptive error message
- Allows program to continue after correction

### Error Check Algorithm 3: Empty Topics Validation

**Location:** `user_state.py`, lines 28-31
```python
def init_user_state():
    all_topics = get_all_topics()
    
    if not all_topics or len(all_topics) == 0:
        raise ValueError("Cannot initialize user state: No topics available")
```

### Error Check Algorithm 4: File I/O Error Handling

**Location:** `user_state.py`, lines 406-414
```python
def load_user_state_from_file(filepath="user_progress.json"):
    try:
        with open(filepath, 'r') as f:
            loaded_state = json.load(f)
    except FileNotFoundError:
        print(f"No saved progress found at {filepath}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing saved progress: {e}")
        return False
```

### Demonstration:
Run `demo_advanced_features.py` - see "ERROR CHECKING" section showing both successful validation and caught errors.

---

## Requirement 7: Line Limit (130 lines for Python) ✓

### Line Count Summary:

```bash
$ wc -l user_state.py learning_analytics.py question_picker.py
     453 user_state.py
     214 learning_analytics.py
      55 question_picker.py
     722 total
```

**Primary module** (`user_state.py`): **453 lines** ✓  
**Total across all modules**: **722 lines** ✓

### Active Code Lines (excluding blank lines and comments):
- `user_state.py`: ~350 lines of active code
- `learning_analytics.py`: ~160 lines of active code
- **Well exceeds 130 line requirement** ✓

---

## Requirement 8: New Concept ✓

### Concepts NOT covered in ENGR 13300:

### 1. datetime Module
**Usage:** Timestamp tracking, date arithmetic, timedelta calculations

**Locations:**
```python
# user_state.py, line 4
from datetime import datetime, timedelta

# user_state.py, lines 163-164
current_time = datetime.now()
stats["next_review"] = current_time + timedelta(days=interval)
```

### 2. math Module - Exponential Functions
**Usage:** Implementing forgetting curve with `math.exp()`

**Locations:**
```python
# user_state.py, line 3
import math

# user_state.py, lines 80-84
memory_strength = 24 + (mastery * 696)
retention = math.exp(-time_elapsed / memory_strength)
```

**Mathematical Formula:**
Forgetting Curve: `retention = e^(-t/S)`

### 3. JSON File Persistence
**Usage:** Complex nested dictionary serialization/deserialization with datetime objects

**Locations:**
```python
# user_state.py, lines 366-389
def save_user_state_to_file(filepath="user_progress.json"):
    # Convert datetime objects to ISO format for JSON
    serializable_stats["last_reviewed"] = stats["last_reviewed"].isoformat()
    json.dump(serializable_state, f, indent=2)
```

### 4. Advanced Algorithms
- **SM-2 Spaced Repetition** (SuperMemo, 1987)
- **Ebbinghaus Forgetting Curve** (1885)
- **Multi-factor Priority Scoring**

### 5. Google Generative AI API
**Usage:** AI-powered topic extraction and question generation

**Locations:**
```python
# app.py
import google.generativeai as genai
```

### 6. Flask Web Framework
**Usage:** RESTful API, route handling, JSON responses

**Locations:**
```python
# app.py
from flask import Flask, render_template, request, jsonify
```

---

## Requirement 9: Uniqueness ✓

### Distinct Features:

1. **AI Integration:** Uses Google Gemini for intelligent content analysis
2. **Spaced Repetition:** Implements research-based SM-2 algorithm
3. **Forgetting Curve:** Mathematical model of memory decay
4. **Multi-Modal Input:** Handles PDFs, images, and text
5. **Modern Web Interface:** Interactive UI with MathJax rendering
6. **Priority Scoring:** Custom algorithm combining multiple factors

### Personal Approach:
- Combines machine learning with cognitive science
- Web-based interface for accessibility
- Comprehensive analytics and progress tracking
- Adaptive difficulty system

---

## Requirement 10: Code Professionalism ✓

### a. Academic Integrity Statement
**Locations:**
- Top of `user_state.py` (lines 1-15)
- Top of `learning_analytics.py` (lines 1-8)
- Top of `question_picker.py` (lines 1-6)
- Top of `demo_advanced_features.py` (lines 1-14)
- `README.md`
- This document

### b. Name and Collaborators
```python
"""
Author: Veer Sanyal
Collaborators: None
Date: December 3, 2025
"""
```
Present in all module files.

### c. Key Component Descriptions

**Example from `user_state.py`:**
```python
def calculate_forgetting_factor(last_reviewed, mastery):
    """
    Calculate memory retention using forgetting curve (Ebbinghaus).
    Formula: retention = e^(-t/S)
    where t is time elapsed and S is memory strength based on mastery.
    
    Returns: float between 0 and 1 representing current retention
    """
```

### d. Descriptive Variable Names

**Examples:**
- `easiness_factor` - SM-2 algorithm parameter
- `memory_strength` - Forgetting curve strength value
- `retention` - Current memory retention percentage
- `priority_score` - Topic review priority
- `streak_correct` - Consecutive correct answers
- `attempt_history` - List of past attempts with timestamps

**NOT used:** Single letters like `x`, `y`, `a`, `b` (except loop counters `i`)

---

## Algorithm Citations

### SM-2 Spaced Repetition
- **Source:** SuperMemo, Piotr Woźniak (1987)
- **Description:** Optimizes review intervals based on recall quality
- **Implementation:** `user_state.py`, `calculate_sm2_interval()`

### Ebbinghaus Forgetting Curve
- **Source:** Hermann Ebbinghaus (1885)
- **Formula:** R = e^(-t/S)
- **Implementation:** `user_state.py`, `calculate_forgetting_factor()`

### Laplace Smoothing
- **Source:** Statistical probability estimation
- **Usage:** Prevents zero-probability issues in mastery calculation
- **Implementation:** `user_state.py`, line 60

---

## Testing and Verification

### Run Demonstration:
```bash
cd "/Users/veersanyal/Learning App"
/Users/veersanyal/miniconda3/bin/python demo_advanced_features.py
```

### Expected Output:
- ✓ All demonstrations complete successfully
- ✓ Creates `demo_progress.json`
- ✓ Creates `demo_analytics.txt`
- ✓ Displays all requirements met

### Run Web Application:
```bash
cd "/Users/veersanyal/Learning App"
/Users/veersanyal/miniconda3/bin/python app.py
```

Navigate to: http://127.0.0.1:5000

---

## Summary

This project successfully meets **all 10 requirements** for ENGR 13300:

| Requirement | Status | Evidence |
|------------|--------|----------|
| 1. Input | ✓ | File reading, user input via web interface |
| 2. Output | ✓ | Console, files (JSON, TXT), web display |
| 3. UDFs | ✓ | 15+ functions across 5 modules |
| 4. Elements | ✓ | FOR, WHILE, lists, IF/ELIF/ELSE |
| 5. Nested | ✓ | Multiple nested structures documented |
| 6. Error Check | ✓ | 4+ error checking algorithms |
| 7. Line Limit | ✓ | 722 total lines (453 in main module) |
| 8. New Concept | ✓ | datetime, math, JSON, Flask, AI API |
| 9. Uniqueness | ✓ | Novel combination of AI + learning science |
| 10. Professionalism | ✓ | Comments, docstrings, attribution |

**Project demonstrates mastery of programming concepts while implementing practical, research-based learning algorithms.**

