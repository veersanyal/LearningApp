import json

# This will hold all topics
topics = []  # list of topic dicts


def load_topics_from_json(json_data):
    """
    json_data is a Python dict that looks like:
    {
      "topics": [
        {
          "topic_id": "...",
          "name": "...",
          "coverage": "practiced",
          "frequency_estimate": 4,
          "difficulty_profile": { "easy": 1, "medium": 3, "hard": 0 }
        }
      ]
    }
    """
    global topics
    topics.extend(json_data.get("topics", []))


def load_topics_from_file(filepath):
    """Load topics from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    load_topics_from_json(data)


def print_topics():
    """Print all stored topics in a simple way."""
    for t in topics:
        dp = t.get("difficulty_profile", {})
        print(f"- {t.get('topic_id')} ({t.get('name')}): "
              f"coverage={t.get('coverage')}, "
              f"freq={t.get('frequency_estimate')}, "
              f"difficulty_profile={dp}")


def get_all_topics():
    """Return the list of all topics."""
    return topics
