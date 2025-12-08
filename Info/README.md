# Learning App - Adaptive Quiz System

**Author:** Veer Sanyal  
**Date:** December 3, 2025

## Academic Integrity Statement
This project is my original work. I have not used source code obtained from any unauthorized source. All algorithms are implemented based on documented educational theories (spaced repetition, forgetting curves) and are properly attributed in code comments.

## Project Overview
An intelligent learning application that uses AI (Google Gemini) to extract topics from study materials and generate adaptive quiz questions. The system implements advanced learning algorithms including spaced repetition, forgetting curves, and adaptive difficulty adjustment.

## Features

### Core Functionality
1. **Document Upload**: Upload PDFs, images, or text files to extract topics
2. **AI Topic Extraction**: Uses Gemini API to identify testable concepts
3. **Adaptive Quizzes**: Questions adapt to user performance
4. **Math Rendering**: Beautiful LaTeX math rendering with MathJax
5. **Progress Tracking**: Comprehensive statistics and analytics

### Advanced Learning Algorithms
- **Spaced Repetition (SM-2)**: Optimizes review timing based on memory research
- **Forgetting Curve**: Models memory decay over time (Ebbinghaus)
- **Adaptive Difficulty**: Adjusts question difficulty based on mastery and streaks
- **Priority Scoring**: Intelligently selects next topic using multi-factor analysis
- **Learning Velocity**: Tracks improvement rate over time

## File Structure

### Core Modules
- **`app.py`** - Flask web server and API endpoints
- **`main.py`** - Command-line interface and testing
- **`topic_map.py`** - Topic storage and management
- **`user_state.py`** - Advanced user state tracking with spaced repetition
- **`question_picker.py`** - Intelligent topic selection algorithm
- **`learning_analytics.py`** - Analytics and reporting functions

### Frontend
- **`templates/index.html`** - Web interface with MathJax support
- **`static/style.css`** - Styling and animations

### Data Files
- **`example.json`** - Sample topic data
- **`requirements.txt`** - Python dependencies

## Installation

```bash
cd "/Users/veersanyal/Learning App"
/Users/veersanyal/miniconda3/bin/pip install -r requirements.txt
```

## Usage

### Start the Web Application
```bash
/Users/veersanyal/miniconda3/bin/python app.py
```
Then open http://127.0.0.1:5000 in your browser.

### Use Command Line Interface
```python
from main import main
main()
```

## Assignment Requirements Checklist

### ✅ Input
- Reads topic data from uploaded files (PDF, images, text)
- Loads saved progress from JSON file

### ✅ Output
- Displays questions and feedback in web interface
- Writes progress to `user_progress.json`
- Exports analytics report to `learning_analytics.txt`
- Prints progress reports to console

### ✅ UDFs (User Defined Functions)
Main program (`app.py`) calls 15+ functions across 5 modules:
- `topic_map.py`: `load_topics_from_json()`, `get_all_topics()`
- `user_state.py`: `init_user_state()`, `record_answer()`, `get_target_difficulty()`, `calculate_forgetting_factor()`, `calculate_sm2_interval()`, `save_user_state_to_file()`, `generate_progress_report()`
- `question_picker.py`: `pick_next_topic()`, `get_recommended_study_order()`
- `learning_analytics.py`: `calculate_study_streak()`, `identify_weak_topics()`, `export_analytics_report()`

### ✅ Elements
- **For loops**: Multiple instances (topic iteration, history processing, priority calculation)
- **While loops**: In `calculate_study_streak()` and `get_learning_velocity()`
- **Lists/arrays**: `attempt_history`, `priority_list`, `all_dates`, `topics`
- **If/elif/else**: Throughout (difficulty selection, priority scoring, validation)

### ✅ Nested Structures
- Nested FOR loops in `calculate_time_distribution()`
- FOR with nested IF statements in `calculate_review_priority()`
- WHILE with nested IF-ELSE in `calculate_study_streak()`
- Multiple other instances

### ✅ Error Checking
1. Input validation in `calculate_forgetting_factor()` (mastery range check)
2. Quality score validation in `calculate_sm2_interval()` (0-5 range)
3. Empty topics check in `init_user_state()`
4. File I/O error handling in save/load functions
5. JSON parsing error handling

### ✅ Line Limit
- `user_state.py`: 180+ lines ✓
- `learning_analytics.py`: 150+ lines ✓
- Total active code well exceeds 130 lines

### ✅ New Concepts
- **datetime module**: Timestamp tracking, date arithmetic
- **math module**: Exponential functions for forgetting curve
- **JSON file persistence**: Save/load progress
- **Flask web framework**: RESTful API endpoints
- **Google Generative AI**: Advanced API integration
- **MathJax**: LaTeX rendering

### ✅ Uniqueness
Custom implementation combining:
- Gemini AI for content analysis
- Spaced repetition (SM-2) algorithm
- Forgetting curve (Ebbinghaus)
- Adaptive difficulty system
- Modern web interface

### ✅ Code Professionalism
- Academic integrity statements in all modules
- Author name and date
- Comprehensive docstrings for all functions
- Descriptive variable names (`easiness_factor`, `retention`, `priority_score`)
- Inline comments explaining algorithms
- Type hints where appropriate

## Key Algorithms

### 1. Spaced Repetition (SM-2)
Based on SuperMemo's research, determines optimal review intervals:
- Tracks "easiness factor" (1.3-2.5) for each topic
- Increases intervals exponentially: 1 day → 6 days → EF * previous interval
- Resets on incorrect answers

### 2. Forgetting Curve (Ebbinghaus)
Models memory retention over time:
```
retention = e^(-t/S)
```
Where:
- t = time elapsed since last review (hours)
- S = memory strength (24-720 hours based on mastery)

### 3. Priority Scoring
Multi-factor algorithm considering:
- Current mastery level (40% weight)
- Review urgency/scheduling (30% weight)
- Forgetting curve prediction (30% weight)

### 4. Adaptive Difficulty
Dynamically adjusts question difficulty based on:
- Current mastery score
- Recent streak (consecutive correct/incorrect)
- Historical performance trends

## API Endpoints

### Core Endpoints
- `POST /upload` - Upload and extract topics from documents
- `POST /generate-question` - Generate question (auto or specific topic)
- `POST /submit-answer` - Submit answer and update mastery
- `GET /stats` - Get current statistics

### Advanced Features
- `POST /save-progress` - Save user progress to file
- `POST /load-progress` - Load saved progress
- `GET /analytics` - Get detailed analytics (streaks, weak/strong topics)
- `POST /export-report` - Export comprehensive report to text file

## Credits

### Algorithms Based On:
- SM-2 Algorithm (SuperMemo, Piotr Woźniak, 1987)
- Forgetting Curve (Hermann Ebbinghaus, 1885)
- Laplace Smoothing for probability estimation

### Technologies Used:
- Python 3.12
- Flask 3.1.2
- Google Generative AI (Gemini)
- MathJax 3 for math rendering
- HTML5/CSS3/JavaScript

