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

@app.route("/event_like_insights/<event_id>", methods=["GET"])
def get_event_like_insights(event_id):
    # Fetch the event document by its ObjectId
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
            # If there were no likes last week, treat any likes this week as a 100% increase
            weekly_growth = 100 if this_week_likes > 0 else 0
        else:
            weekly_growth = round(((this_week_likes - last_week_likes) / last_week_likes) * 100)
    else:
        weekly_growth = 0

    # ------------------------------
    # Insight 3: Peak Engagement
    if total_likes > 0:
        daily_counts = {}
        for like in likes_list:
            like_date = like["createdAt"].date()
            daily_counts[like_date] = daily_counts.get(like_date, 0) + 1

        max_likes = max(daily_counts.values())
        # In case of a tie, select the most recent day
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
        # Use our computed total_likes for the current event
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
    # Group likes by day for dailyLikes
    daily_likes = {}
    for like in likes_list:
        like_date_str = like["createdAt"].strftime("%Y-%m-%d")  # e.g., "YYYY-MM-DD"
        daily_likes[like_date_str] = daily_likes.get(like_date_str, 0) + 1

    # Convert to a sorted list of dicts
    daily_likes_sorted = [
        {"date": date_str, "likes": count}
        for date_str, count in sorted(daily_likes.items())
    ]

    # ------------------------------
    # Return all insights using the computed values
    return {
        "dailyLikes": daily_likes_sorted,
        "eventName": event_name,
        "lastLikeDaysAgo": last_like_days_ago,
        "peakEngagementDaysAgo": peak_engagement_days_ago,
        "peakEngagementLikes": peak_engagement_likes,
        "percentageRank": percentage_rank,
        "totalLikes": total_likes,
        "weeklyGrowth": weekly_growth
    }


@app.route("/event_click_insights/<event_id>", methods=["GET"])
def get_event_clicks_insights(event_id):
    # Fetch the event document by its ObjectId
    event = db.events.find_one({"_id": ObjectId(event_id)})
    if not event:
        return jsonify({"error": "Event not found."}), 404

    now = datetime.utcnow()

    # ------------------------------
    # Get Event Name
    event_name = event.get("title", "Untitled Event")

    # ------------------------------
    # Insight 1: Total Clicks
    clicks_list = list(db.clicks.find({"event": ObjectId(event_id)}))
    total_clicks = len(clicks_list)

    # Compute lastClickDaysAgo: days since the most recent click
    if total_clicks > 0:
        latest_click_time = max(click["createdAt"] for click in clicks_list)
        last_click_days_ago = (now - latest_click_time).days
    else:
        last_click_days_ago = 0

    # ------------------------------
    # Insight 2: Weekly Growth in Clicks
    event_created = event.get("createdAt")
    if event_created and (now - event_created).days >= 14:
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)
        this_week_clicks = db.clicks.count_documents({
            "event": ObjectId(event_id),
            "createdAt": {"$gte": this_week_start}
        })
        last_week_clicks = db.clicks.count_documents({
            "event": ObjectId(event_id),
            "createdAt": {"$gte": last_week_start, "$lt": this_week_start}
        })
        if last_week_clicks == 0:
            weekly_growth = 100 if this_week_clicks > 0 else 0
        else:
            weekly_growth = round(((this_week_clicks - last_week_clicks) / last_week_clicks) * 100)
    else:
        weekly_growth = 0

    # ------------------------------
    # Insight 3: Peak Engagement for Clicks
    if total_clicks > 0:
        daily_counts = {}
        for click in clicks_list:
            click_date = click["createdAt"].date()
            daily_counts[click_date] = daily_counts.get(click_date, 0) + 1

        max_clicks = max(daily_counts.values())
        peak_days = [d for d, count in daily_counts.items() if count == max_clicks]
        peak_day = max(peak_days)
        peak_engagement_days_ago = (now.date() - peak_day).days
        peak_engagement_clicks = max_clicks
    else:
        peak_engagement_days_ago = 0
        peak_engagement_clicks = 0

    # ------------------------------
    # Insight 4: Percentage Rank Among All Events for Clicks
    all_events = list(db.events.find({}, {"clickCount": 1}))
    total_events = len(all_events)
    if total_events > 0:
        def get_click_count(e):
            if e["_id"] == event["_id"]:
                return total_clicks
            else:
                return e.get("clickCount", 0)

        sorted_events = sorted(all_events, key=get_click_count, reverse=True)
        rank = None
        for i, e in enumerate(sorted_events):
            if e["_id"] == event["_id"]:
                rank = i + 1
                break
        if rank is None:
            rank = total_events
        percentage_rank = round((rank / total_events) * 100)
    else:
        percentage_rank = 0

    # ------------------------------
    # Group clicks by day
    daily_clicks = {}
    for click in clicks_list:
        click_date = click["createdAt"].strftime("%Y-%m-%d")
        daily_clicks[click_date] = daily_clicks.get(click_date, 0) + 1

    # Convert to sorted list
    daily_clicks_sorted = [{"date": date, "clicks": count} for date, count in sorted(daily_clicks.items())]

    # ------------------------------
    # Return all insights as numbers in a dictionary
    return jsonify({
        "dailyClicks": daily_clicks_sorted,
        "eventName": event_name,
        "lastClickDaysAgo": last_click_days_ago,
        "peakEngagementDaysAgo": peak_engagement_days_ago,
        "peakEngagementClicks": peak_engagement_clicks,
        "percentageRank": percentage_rank,
        "totalClicks": total_clicks,
        "weeklyGrowth": weekly_growth
    })


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
