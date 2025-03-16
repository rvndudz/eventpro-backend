import numpy as np
from pymongo import MongoClient
from bson.objectid import ObjectId
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import config

def get_user_interacted_event_weights(user_id, db, weights=None):
    """
    Retrieves a dictionary mapping event IDs to aggregated interaction weights for the user.
    Interaction types:
        orders: weight 0.6,
        likes: weight 0.3,
        clicks: weight 0.1.
    """
    if weights is None:
        weights = {'orders': 0.6, 'likes': 0.3, 'clicks': 0.1}
    
    # Ensure user_id is an ObjectId
    if not isinstance(user_id, ObjectId):
        user_id = ObjectId(user_id)
        
    aggregated = {}
    
    # Process orders
    orders_cursor = db.orders.find({"buyer": user_id}, {"event": 1})
    for doc in orders_cursor:
        event = doc["event"]
        aggregated[event] = aggregated.get(event, 0) + weights['orders']
    
    # Process likes
    likes_cursor = db.likes.find({"liker": user_id}, {"event": 1})
    for doc in likes_cursor:
        event = doc["event"]
        aggregated[event] = aggregated.get(event, 0) + weights['likes']
    
    # Process clicks
    clicks_cursor = db.clicks.find({"clicker": user_id}, {"event": 1})
    for doc in clicks_cursor:
        event = doc["event"]
        aggregated[event] = aggregated.get(event, 0) + weights['clicks']
    
    return aggregated

def get_all_events(db):
    """
    Retrieves all events from the events collection.
    """
    events_cursor = db.events.find({})
    events = list(events_cursor)
    return events

def build_event_corpus(events):
    """
    Builds a text corpus from events by concatenating the title and description.
    Returns the corpus (list of texts) and a list of event IDs in the same order.
    """
    corpus = []
    event_ids = []
    for event in events:
        title = event.get("title", "")
        description = event.get("description", "")
        text = f"{title} {description}"
        corpus.append(text)
        event_ids.append(event["_id"])
    return corpus, event_ids

def build_user_profile(interacted_event_weights, event_matrix, event_ids):
    """
    Computes the user profile as the weighted average of event vectors.
    'interacted_event_weights' is a dictionary mapping event ID to its aggregated weight.
    """
    indices = []
    weight_list = []
    
    # Identify indices of events that the user interacted with
    for i, eid in enumerate(event_ids):
        if eid in interacted_event_weights:
            indices.append(i)
            weight_list.append(interacted_event_weights[eid])
    
    if not indices:
        return None
    
    # Retrieve vectors for the interacted events
    vectors = event_matrix[indices]
    # Convert vectors to a dense array (since number of interactions is small)
    vectors_dense = vectors.toarray()
    weight_array = np.array(weight_list).reshape(-1, 1)
    
    # Compute the weighted sum and then normalize
    weighted_vectors = vectors_dense * weight_array
    weighted_sum = weighted_vectors.sum(axis=0)
    total_weight = weight_array.sum()
    user_profile = weighted_sum / total_weight
    
    return user_profile

def get_recommendations(user_profile, candidate_indices, event_matrix, top_n=5):
    """
    Computes cosine similarities between the user profile vector and candidate event vectors.
    Returns the relative indices and similarity scores for the top recommended events.
    """
    # Convert candidate vectors to dense array
    candidate_vectors = event_matrix[candidate_indices].toarray()
    similarities = cosine_similarity(candidate_vectors, user_profile.reshape(1, -1)).flatten()
    
    # Sort candidates by similarity in descending order and pick top_n indices
    top_candidate_relative_idx = similarities.argsort()[::-1][:top_n]
    top_similarities = similarities[top_candidate_relative_idx]
    return top_candidate_relative_idx, top_similarities

def main(user_id_str):
    # Connect to MongoDB
    mongodb_uri = config.MONGODB_URI
    client = MongoClient(mongodb_uri)
    db = client.get_database()
    
    # Retrieve the aggregated weights for all events the user has interacted with
    interacted_event_weights = get_user_interacted_event_weights(user_id_str, db)
    print(f"User {user_id_str} interaction weights for {len(interacted_event_weights)} events:")
    for eid, weight in interacted_event_weights.items():
        print(f"  Event ID: {eid} -> Weight: {weight}")
    
    # Retrieve all events from the DB
    events = get_all_events(db)
    print(f"Total events retrieved: {len(events)}")
    
    # Build the corpus and list of event IDs
    corpus, event_ids = build_event_corpus(events)
    
    # Vectorize the event text using TF-IDF
    vectorizer = TfidfVectorizer(stop_words='english')
    event_matrix = vectorizer.fit_transform(corpus)
    
    # Identify indices for user-interacted events and candidate events
    user_event_indices = [i for i, eid in enumerate(event_ids) if eid in interacted_event_weights]
    candidate_indices = [i for i, eid in enumerate(event_ids) if eid not in interacted_event_weights]
    
    if not user_event_indices:
        print("No interactions found for user. Unable to build user profile.")
        return
    
    # Build the user profile using a weighted average of event vectors
    user_profile = build_user_profile(interacted_event_weights, event_matrix, event_ids)
    
    # Compute recommendations from candidate events
    top_relative_indices, similarity_scores = get_recommendations(user_profile, candidate_indices, event_matrix, top_n=5)
    
    print("\nTop recommended events:")
    for rank, rel_idx in enumerate(top_relative_indices, start=1):
        # Map the candidate relative index back to the original index in the events list
        original_idx = candidate_indices[rel_idx]
        event = events[original_idx]
        sim_score = similarity_scores[rank - 1]
        print(f"{rank}. Event ID: {event['_id']}, Title: {event.get('title','')}, Similarity Score: {sim_score:.4f}")

if __name__ == "__main__":
    # Replace with a valid user ID from your database (as a string)
    sample_user_id = "67d6addee62e8f20f5a9cbae"
    main(sample_user_id)
