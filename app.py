from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import json_util
from bson.objectid import ObjectId
import json
import config
from datetime import datetime, timedelta

app = Flask(__name__)

# MongoDB Atlas connection string
mongodb_uri = config.MONGODB_URI
client = MongoClient(mongodb_uri)
db = client.get_database()

@app.route("/")
def hello_world():
    return "Hello, World! This is EventPro Flask Backend"

# Users Collection
@app.route("/users", methods=["GET"])
def get_users():
    users = list(db.users.find())
    return json.loads(json_util.dumps(users))

# Orders Collection
@app.route("/orders", methods=["GET"])
def get_orders():
    orders = list(db.orders.find())
    return json.loads(json_util.dumps(orders))

# Likes Collection
@app.route("/likes", methods=["GET"])
def get_likes():
    likes = list(db.likes.find())
    return json.loads(json_util.dumps(likes))

# Events Collection
@app.route("/events", methods=["GET"])
def get_events():
    events = list(db.events.find())
    return json.loads(json_util.dumps(events))

# Clicks Collection
@app.route("/clicks", methods=["GET"])
def get_clicks():
    clicks = list(db.clicks.find())
    return json.loads(json_util.dumps(clicks))

# Categories Collection
@app.route("/categories", methods=["GET"])
def get_categories():
    categories = list(db.categories.find())
    return json.loads(json_util.dumps(categories))

@app.route("/event_insights/<event_id>", methods=["GET"])
def get_event_insights(event_id):
    # Fetch the event document by its ObjectId.
    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return {"error": "Event not found."}

    now = datetime.utcnow()

    # ------------------------------
    # Get Event Name
    event_name = event.get("title", "Untitled Event")

    # ------------------------------
    # Insight 1: Total Likes
    likes_list = list(db.likes.find({"event": ObjectId(event_id)}))
    total_likes = len(likes_list)

    # Compute lastLikeDaysAgo: days since the most recent like
    if total_likes > 0:
        # Determine the most recent like time from the list
        latest_like_time = max(like["createdAt"] for like in likes_list)
        last_like_days_ago = (now - latest_like_time).days
    else:
        last_like_days_ago = 0

    # ------------------------------
    # Insight 2: Weekly Growth in Likes
    event_created = event.get("createdAt")
    if event_created and (now - event_created).days >= 14:
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)
        this_week_likes = db.likes.count_documents({
            "event": ObjectId(event_id),
            "createdAt": {"$gte": this_week_start}
        })
        last_week_likes = db.likes.count_documents({
            "event": ObjectId(event_id),
            "createdAt": {"$gte": last_week_start, "$lt": this_week_start}
        })
        if last_week_likes == 0:
            # If there were no likes in the previous week, treat any likes this week as a 100% increase.
            weekly_growth = 100 if this_week_likes > 0 else 0
        else:
            weekly_growth = round(((this_week_likes - last_week_likes) / last_week_likes) * 100)
    else:
        weekly_growth = 0

    # ------------------------------
    # Insight 3: Peak Engagement
    # Calculate which day had the highest number of likes.
    if total_likes > 0:
        daily_counts = {}
        for like in likes_list:
            # Extract the date portion from the like's createdAt timestamp.
            like_date = like["createdAt"].date()
            daily_counts[like_date] = daily_counts.get(like_date, 0) + 1

        max_likes = max(daily_counts.values())
        # In case of a tie, select the most recent day.
        peak_days = [d for d, count in daily_counts.items() if count == max_likes]
        peak_day = max(peak_days)
        peak_engagement_days_ago = (now.date() - peak_day).days
        peak_engagement_likes = max_likes
    else:
        peak_engagement_days_ago = 0
        peak_engagement_likes = 0

    # ------------------------------
    # Insight 4: Percentage Rank Among All Events
    all_events = list(db.events.find({}, {"likeCount": 1}))
    total_events = len(all_events)
    if total_events > 0:
        # Use our computed total_likes for the current event.
        def get_like_count(e):
            if e["_id"] == event["_id"]:
                return total_likes
            else:
                return e.get("likeCount", 0)

        sorted_events = sorted(all_events, key=get_like_count, reverse=True)
        rank = None
        for i, e in enumerate(sorted_events):
            if e["_id"] == event["_id"]:
                rank = i + 1  # 1-indexed rank
                break
        if rank is None:
            rank = total_events
        percentage_rank = round((rank / total_events) * 100)
    else:
        percentage_rank = 0

    # ------------------------------
    # Return all insights as numbers in a dictionary.
    return {
        "eventName": event_name,
        "totalLikes": total_likes,
        "lastLikeDaysAgo": last_like_days_ago,
        "weeklyGrowth": weekly_growth,
        "peakEngagementDaysAgo": peak_engagement_days_ago,
        "peakEngagementLikes": peak_engagement_likes,
        "percentageRank": percentage_rank
    }

if __name__ == "__main__":
    app.run() 
