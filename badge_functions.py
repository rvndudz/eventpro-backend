from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta

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

def update_just_announced_badges():
    """ Updates the 'just_announced' badge for events created in the last 3 days. """

    # Define the time threshold (3 days ago)
    three_days_ago = datetime.utcnow() - timedelta(days=3)

    # Fetch all events
    all_events = db.events.find({}, {"_id": 1, "createdAt": 1, "badges": 1})

    for event in all_events:
        event_id = event["_id"]
        created_at = event.get("createdAt", None)
        badges = event.get("badges", [])

        if created_at and created_at >= three_days_ago:
            # Add "just_announced" if not already present
            if "just_announced" not in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$addToSet": {"badges": "just_announced"}}
                )
                print(f"Added 'just_announced' to Event {event_id}")
        else:
            # Remove "just_announced" if event is older than 3 days
            if "just_announced" in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$pull": {"badges": "just_announced"}}
                )
                print(f"Removed 'just_announced' from Event {event_id}")

    print("Just Announced badge update completed.")

def update_limited_seats_badges():
    """ Updates the 'limited_seats' badge for events with 10% or fewer seats remaining. """

    # Fetch all events with tickets data
    all_events = db.events.find({}, {"_id": 1, "maximumTickets": 1, "ticketsSoldCount": 1, "badges": 1})

    for event in all_events:
        event_id = event["_id"]
        max_tickets = event.get("maximumTickets", "0")
        tickets_sold = event.get("ticketsSoldCount", "0")
        badges = event.get("badges", [])

        try:
            max_tickets = int(max_tickets)
            tickets_sold = int(tickets_sold)
        except ValueError:
            continue  # Skip if invalid ticket data

        # Calculate remaining seat percentage
        remaining_seats = max_tickets - tickets_sold
        remaining_percentage = (remaining_seats / max_tickets) * 100 if max_tickets > 0 else 100

        if remaining_percentage <= 10:
            # Add "limited_seats" if not already present
            if "limited_seats" not in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$addToSet": {"badges": "limited_seats"}}
                )
                print(f"Added 'limited_seats' to Event {event_id}")
        else:
            # Remove "limited_seats" if event has more than 10% seats remaining
            if "limited_seats" in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$pull": {"badges": "limited_seats"}}
                )
                print(f"Removed 'limited_seats' from Event {event_id}")

    print("Limited Seats badge update completed.")

def update_fast_selling_badges():
    """ Updates the 'fast_selling' badge for the top 10% of events with the highest sales percentage in the last 3 days. """

    # Define the time range (last 3 days)
    three_days_ago = datetime.utcnow() - timedelta(days=3)

    # Get ticket sales from the last 3 days
    recent_sales = db.orders.aggregate([
        {"$match": {"createdAt": {"$gte": three_days_ago}}},
        {"$group": {"_id": "$event", "tickets_sold": {"$sum": 1}}}
    ])

    # Convert to a list
    recent_sales = list(recent_sales)
    total_events = len(recent_sales)

    if total_events == 0:
        print("No recent ticket sales found.")
        return

    # Fetch event data (maximumTickets) for all recent sales
    event_data = {}
    for sale in recent_sales:
        event = db.events.find_one({"_id": sale["_id"]}, {"maximumTickets": 1, "badges": 1})
        if event:
            try:
                max_tickets = int(event.get("maximumTickets", "0"))
                if max_tickets > 0:
                    sales_percentage = (sale["tickets_sold"] / max_tickets) * 100
                    event_data[sale["_id"]] = {
                        "sales_percentage": sales_percentage,
                        "badges": event.get("badges", [])
                    }
            except ValueError:
                continue  # Skip invalid data

    # Sort events by sales percentage (descending order)
    sorted_events = sorted(event_data.items(), key=lambda x: x[1]["sales_percentage"], reverse=True)

    # Get the top 10% of events
    top_10_percent_count = max(1, total_events // 10)
    top_events = sorted_events[:top_10_percent_count]

    # Extract top event IDs
    top_event_ids = {event[0] for event in top_events}

    # Process all recent sales events to update their badges
    for event_id, data in event_data.items():
        badges = data["badges"]

        if event_id in top_event_ids:
            # Add "fast_selling" if not already present
            if "fast_selling" not in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$addToSet": {"badges": "fast_selling"}}
                )
                print(f"Added 'fast_selling' to Event {event_id}")
        else:
            # Remove "fast_selling" if event is no longer in the top 10%
            if "fast_selling" in badges:
                db.events.update_one(
                    {"_id": event_id},
                    {"$pull": {"badges": "fast_selling"}}
                )
                print(f"Removed 'fast_selling' from Event {event_id}")

    print("Fast Selling badge update completed.")

# Run the functions
if __name__ == "__main__":
    update_top_rated_badges()
    update_popular_choice_badges()
    update_just_announced_badges()
    update_limited_seats_badges()
    update_fast_selling_badges()
