"""
Intelligent Question Picker Module
Uses spaced repetition and priority scoring to select optimal questions

Author: Veer Sanyal
Collaborators: None
"""

import random
from topic_map import get_all_topics
from user_state import get_user_state, calculate_review_priority, get_topics_needing_review


def pick_next_topic(user_id):
    """
    Choose the next topic to test using advanced priority algorithm.
    Combines spaced repetition, mastery levels, and forgetting curves.
    """
    user_state = get_user_state(user_id)
    
    # Error checking
    if not user_state or len(user_state) == 0:
        raise ValueError("user_state is empty; call init_user_state() first")
    
    # First priority: Topics that are overdue for review
    overdue_topics = get_topics_needing_review(user_id)
    
    # IF-ELSE structure
    if overdue_topics and len(overdue_topics) > 0:
        # Pick from overdue topics randomly
        return random.choice(overdue_topics)
    else:
        # Use priority scoring algorithm
        priority_list = calculate_review_priority(user_id)
        
        # Get top 3 highest priority topics
        top_priorities = priority_list[:min(3, len(priority_list))]
        
        # Randomly select from top priorities to add variety
        if top_priorities:
            topic_id, score = random.choice(top_priorities)
            return topic_id
        else:
            # Fallback: random selection
            all_topic_ids = list(user_state.keys())
            return random.choice(all_topic_ids)


def get_recommended_study_order(user_id):
    """
    Get recommended order for studying all topics.
    Returns list of topic_ids sorted by learning priority.
    """
    priority_list = calculate_review_priority(user_id)
    return [topic_id for topic_id, score in priority_list]
