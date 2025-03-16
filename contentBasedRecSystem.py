# contentBasedRecSystem.py

import numpy as np
from bson.objectid import ObjectId
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def get_recommended_event_ids(user_id, db, top_n=10):
    """
    Returns a list of recommended event IDs (as strings) for the given user_id.
    """
    user_obj_id = ObjectId(user_id)
    weights = {'orders': 0.6, 'likes': 0.3, 'clicks': 0.1}
    event_weights = {}

    # Collect user interactions (orders, likes, clicks)
    for doc in db.orders.find({"buyer": user_obj_id}, {"event": 1}):
        event_weights[doc["event"]] = event_weights.get(doc["event"], 0) + weights['orders']
    for doc in db.likes.find({"liker": user_obj_id}, {"event": 1}):
        event_weights[doc["event"]] = event_weights.get(doc["event"], 0) + weights['likes']
    for doc in db.clicks.find({"clicker": user_obj_id}, {"event": 1}):
        event_weights[doc["event"]] = event_weights.get(doc["event"], 0) + weights['clicks']

    # If user has no interactions, return empty
    if not event_weights:
        return []

    # Fetch all events
    events = list(db.events.find({}))
    if not events:
        return []

    # Build TF-IDF corpus
    corpus = []
    event_ids = []
    for event in events:
        title = event.get("title", "")
        description = event.get("description", "")
        text = f"{title} {description}"
        corpus.append(text)
        event_ids.append(event["_id"])

    vectorizer = TfidfVectorizer(stop_words='english')
    event_matrix = vectorizer.fit_transform(corpus)

    # Build user profile (weighted average)
    indices = []
    weights_list = []
    for i, eid in enumerate(event_ids):
        if eid in event_weights:
            indices.append(i)
            weights_list.append(event_weights[eid])

    if not indices:
        return []

    user_vectors = event_matrix[indices].toarray()
    weight_array = np.array(weights_list).reshape(-1, 1)
    weighted_sum = (user_vectors * weight_array).sum(axis=0)
    total_weight = weight_array.sum()
    user_profile = weighted_sum / total_weight

    # Candidate events (not interacted with)
    candidate_indices = [i for i, eid in enumerate(event_ids) if eid not in event_weights]
    if not candidate_indices:
        return []

    candidate_vectors = event_matrix[candidate_indices].toarray()
    similarities = cosine_similarity(candidate_vectors, user_profile.reshape(1, -1)).flatten()

    # Sort by descending similarity
    sorted_indices = np.argsort(similarities)[::-1]
    recommended_ids = []
    for idx in sorted_indices[:top_n]:
        original_index = candidate_indices[idx]
        recommended_ids.append(str(event_ids[original_index]))

    return recommended_ids
