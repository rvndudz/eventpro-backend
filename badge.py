from pymongo import MongoClient
from bson.objectid import ObjectId
import config

# Connect to MongoDB
mongodb_uri = config.MONGODB_URI
client = MongoClient(mongodb_uri)
db = client.get_database()

def update_top_rated_badges():
    """ Updates the 'top_rated' badge for the top 10% most liked events. """
    
    # Get all events and their like counts
    event_likes = db.likes.aggregate([
        {"$group": {"_id": "$event", "total_likes": {"$sum": 1}}},
        {"$sort": {"total_likes": -1}}  # Sort in descending order
    ])

    # Convert to a list
    event_likes = list(event_likes)
    total_events = len(event_likes)

    if total_events == 0:
        print("No events found with likes.")
        return

    # Calculate the top 10% threshold
    top_10_percent_count = max(1, total_events // 10)  # Ensure at least 1 event qualifies
    top_events = event_likes[:top_10_percent_count]  # Get the top N events

    # Extract top event IDs
    top_event_ids = {event["_id"] for event in top_events}

    # Process all events to update their badges
    all_events = db.events.find({}, {"_id": 1, "badges": 1})

    for event in all_events:
        event_id = event["_id"]
        badges = event.get("badges", [])

        if event_id in top_event_ids:
            # Add "top_rated" if not already present
            if "top_rated" not in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$addToSet": {"badges": "top_rated"}}
                )
                print(f"Added 'top_rated' to Event {event_id}")
        else:
            # Remove "top_rated" if the event no longer qualifies
            if "top_rated" in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$pull": {"badges": "top_rated"}}
                )
                print(f"Removed 'top_rated' from Event {event_id}")

    print("Top Rated badge update completed.")

def update_popular_choice_badges():
    """ Updates the 'popular_choice' badge for the top 10% most clicked events. """
    
    # Get all events and their click counts
    event_clicks = db.clicks.aggregate([
        {"$group": {"_id": "$event", "total_clicks": {"$sum": 1}}},
        {"$sort": {"total_clicks": -1}}  # Sort in descending order
    ])

    # Convert to a list
    event_clicks = list(event_clicks)
    total_events = len(event_clicks)

    if total_events == 0:
        print("No events found with clicks.")
        return

    # Calculate the top 10% threshold
    top_10_percent_count = max(1, total_events // 10)  # Ensure at least 1 event qualifies
    top_events = event_clicks[:top_10_percent_count]  # Get the top N events

    # Extract top event IDs
    top_event_ids = {event["_id"] for event in top_events}

    # Process all events to update their badges
    all_events = db.events.find({}, {"_id": 1, "badges": 1})

    for event in all_events:
        event_id = event["_id"]
        badges = event.get("badges", [])

        if event_id in top_event_ids:
            # Add "popular_choice" if not already present
            if "popular_choice" not in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$addToSet": {"badges": "popular_choice"}}
                )
                print(f"Added 'popular_choice' to Event {event_id}")
        else:
            # Remove "popular_choice" if the event no longer qualifies
            if "popular_choice" in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$pull": {"badges": "popular_choice"}}
                )
                print(f"Removed 'popular_choice' from Event {event_id}")

    print("Popular Choice badge update completed.")

# Run the function
if __name__ == "__main__":
    update_top_rated_badges()
    update_popular_choice_badges()
