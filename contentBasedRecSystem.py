import numpy as np
from bson.objectid import ObjectId
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import re
from datetime import datetime

def preprocess_text(text, is_category=False):
    """Clean and preprocess text data"""
    if not isinstance(text, str):
        return ""
    
    # For categories, only convert to lowercase and strip whitespace
    if is_category:
        return text.lower().strip()
    
    # For other text (title, description), apply full preprocessing
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_event_features(event):
    """Extract and normalize event features"""
    features = {}
    
    # Text features only
    features['title'] = preprocess_text(event.get('title', ''))
    features['description'] = preprocess_text(event.get('description', ''))
    features['category'] = preprocess_text(event.get('category', ''), is_category=True)
    
    return features

def get_recommended_event_ids(user_id, db, top_n=10):
    """
    Returns a list of recommended event IDs based on content analysis and user preferences.
    Uses a sophisticated feature engineering approach focusing on category, title, and description.
    Strictly recommends only events from user's preferred categories.
    """
    user_obj_id = ObjectId(user_id)
    
    # Dynamic weights based on user interaction frequency
    weights = {'orders': 0.7, 'likes': 0.3}
    
    # Collect user interactions
    event_weights = {}
    category_weights = {}  # Track category preferences
    
    # Process orders
    for doc in db.orders.find({"buyer": user_obj_id}, {"event": 1}):
        event_weights[doc["event"]] = event_weights.get(doc["event"], 0) + weights['orders']
    
    # Process likes
    for doc in db.likes.find({"liker": user_obj_id}, {"event": 1}):
        event_weights[doc["event"]] = event_weights.get(doc["event"], 0) + weights['likes']

    if not event_weights:
        return []

    # Fetch all events
    events = list(db.events.find({}))
    if not events:
        return []

    # Debug: Print raw event data for user interactions
    print("\nUser Interaction Events:")
    for event_id, weight in event_weights.items():
        event = next((e for e in events if e["_id"] == event_id), None)
        if event:
            print(f"Event ID: {event_id}")
            print(f"Title: {event.get('title', 'N/A')}")
            print(f"Category: {event.get('category', 'N/A')}")
            print(f"Weight: {weight}")
            print("---")

    # Build category preferences from user interactions
    for event_id, weight in event_weights.items():
        event = next((e for e in events if e["_id"] == event_id), None)
        if event and 'category' in event:
            # Use raw category without preprocessing for now
            category = event['category']
            category_weights[category] = category_weights.get(category, 0) + weight

    # Get top preferred categories (categories with highest weights)
    preferred_categories = sorted(category_weights.items(), key=lambda x: x[1], reverse=True)
    preferred_categories = [cat for cat, _ in preferred_categories[:3]]  # Keep top 3 categories

    if not preferred_categories:
        return []

    # Prepare features for all events
    event_features = []
    event_ids = []
    event_categories = []  # Store categories separately
    
    for event in events:
        features = get_event_features(event)
        # Combine title and description for content analysis
        event_features.append(f"{features['title']} {features['description']}")
        event_ids.append(event["_id"])
        # Use raw category without preprocessing
        event_categories.append(event.get('category', ''))

    # Create TF-IDF vectors for text features
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),
        max_features=1000
    )
    text_matrix = vectorizer.fit_transform(event_features)

    # Build user profile
    indices = []
    weights_list = []
    for i, eid in enumerate(event_ids):
        if eid in event_weights:
            indices.append(i)
            weights_list.append(event_weights[eid])

    if not indices:
        return []

    # Convert sparse matrix to dense array for user profile calculation
    text_array = text_matrix.toarray()
    user_vectors = text_array[indices]
    weight_array = np.array(weights_list).reshape(-1, 1)
    weighted_sum = (user_vectors * weight_array).sum(axis=0)
    total_weight = weight_array.sum()
    user_profile = weighted_sum / total_weight

    # Get candidate events from preferred categories only
    candidate_indices = []
    candidate_categories = []  # Track categories of candidates
    for i, (eid, category) in enumerate(zip(event_ids, event_categories)):
        if eid not in event_weights and category in preferred_categories:
            candidate_indices.append(i)
            candidate_categories.append(category)

    if not candidate_indices:
        return []

    # Calculate content-based similarities only for preferred category events
    candidate_vectors = text_array[candidate_indices]
    content_similarities = cosine_similarity(candidate_vectors, user_profile.reshape(1, -1)).flatten()

    # Sort and return recommendations based on content similarity
    sorted_indices = np.argsort(content_similarities)[::-1]
    recommended_ids = []
    recommended_categories = []  # Track categories of recommendations

    for idx in sorted_indices[:top_n]:
        original_index = candidate_indices[idx]
        recommended_ids.append(str(event_ids[original_index]))
        recommended_categories.append(candidate_categories[idx])

    # Debug logging
    print("\nDebug Information:")
    print(f"User's preferred categories: {preferred_categories}")
    print(f"Category weights: {category_weights}")
    print(f"Recommended categories: {recommended_categories}")
    
    # Verify all recommendations are from preferred categories
    for cat in recommended_categories:
        if cat not in preferred_categories:
            print(f"\nWARNING: Found recommendation from non-preferred category: {cat}")
            print(f"Preferred categories: {preferred_categories}")
            print(f"User's category weights: {category_weights}")
            return []  # Return empty list if we find any non-preferred categories

    return recommended_ids
