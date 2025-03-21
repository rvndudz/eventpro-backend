import streamlit as st
import pymongo
from bson.objectid import ObjectId
from contentBasedRecSystem import get_recommended_event_ids  # Importing the recommendation system
import config
import uuid

# MongoDB Atlas connection string
mongodb_uri = config.MONGODB_URI
client = pymongo.MongoClient(mongodb_uri)
db = client.get_database()

# Hardcoded user ID
USER_ID = "67d70380dfb519abd0a2da92"

def get_events_by_category(category_id, skip=0, limit=5):
    return list(db.events.find({"category": ObjectId(category_id)}).skip(skip).limit(limit))

def get_all_categories():
    return list(db.categories.find({}))

def get_category_name(category_id):
    category = db.categories.find_one({"_id": ObjectId(category_id)})
    return category["name"] if category else "Unknown Category"

def get_liked_events():
    liked_events = db.likes.find({"liker": ObjectId(USER_ID)})
    return [db.events.find_one({"_id": event["event"]}) for event in liked_events]

def get_purchased_events():
    purchased_events = db.orders.find({"buyer": ObjectId(USER_ID)})
    return [db.events.find_one({"_id": event["event"]}) for event in purchased_events]

def like_event(event_id):
    db.likes.insert_one({"liker": ObjectId(USER_ID), "event": ObjectId(event_id)})

def make_order(event_id, total_amount="0"):  # Default amount set to 0 for free events
    stripe_id = str(uuid.uuid4())  # Generate a unique stripeId
    db.orders.insert_one({
        "buyer": ObjectId(USER_ID),
        "event": ObjectId(event_id),
        "totalAmount": total_amount,
        "stripeId": stripe_id  # Ensure uniqueness
    })

def truncate_description(description, word_limit=20):
    if isinstance(description, str):
        words = description.split()
        return " ".join(words[:word_limit]) + ("..." if len(words) > word_limit else "")
    return "No description available"

def main():
    st.title("EventPro - Event Recommendation System")

    # Filtering by category with Pagination
    st.header("Filter Events by Category")
    categories = get_all_categories()
    category_map = {category["name"]: str(category["_id"]) for category in categories}
    selected_category = st.selectbox("Choose a category", list(category_map.keys()))
    category_page_number = st.number_input("Category Page Number", min_value=1, step=1, value=1, key="category_page")
    events_per_page = 5
    category_skip = (category_page_number - 1) * events_per_page
    
    if selected_category:
        category_events = get_events_by_category(category_map[selected_category], skip=category_skip, limit=events_per_page)
        for event in category_events:
            st.subheader(event["title"])
            if "imageUrl" in event and isinstance(event["imageUrl"], str) and event["imageUrl"]:
                st.image(event["imageUrl"], caption=event["title"], use_column_width=True)
            else:
                st.write("No image available")
            st.write(truncate_description(event.get("description", "")))
            st.write(f"Price: {'Free' if event.get('isFree', False) else event.get('price', 'N/A')} - Category: {get_category_name(event.get('category'))}")
            if st.button(f"Like {event['title']}", key=f"like_{event['_id']}"):
                like_event(event["_id"])
                st.success(f"Liked {event['title']}")
            if st.button(f"Order {event['title']}", key=f"order_{event['_id']}"):
                make_order(event["_id"], event.get("price", "0"))
                st.success(f"Ordered {event['title']}")
    
    # Recommended Events
    st.header("Recommended Events")
    if st.button("Show Recommended Events"):
        recommended_event_ids = get_recommended_event_ids(USER_ID, db)
        if recommended_event_ids:
            for event_id in recommended_event_ids:
                event = db.events.find_one({"_id": ObjectId(event_id)})
                if event:
                    category_name = get_category_name(event.get("category"))
                    st.subheader(event["title"])
                    st.write(f"Category: {category_name}")
                    if "imageUrl" in event and isinstance(event["imageUrl"], str) and event["imageUrl"]:
                        st.image(event["imageUrl"], caption=event["title"], use_column_width=True)
                    else:
                        st.write("No image available")
                    st.write(truncate_description(event.get("description", "")))
        else:
            st.write("No recommendations available yet.")
    
    # Liked Events
    st.header("Liked Events")
    if st.button("Show Liked Events"):
        liked_events = get_liked_events()
        if liked_events:
            for event in liked_events:
                st.subheader(event["title"])
                st.write(f"Category: {get_category_name(event.get('category'))}")
                st.write(truncate_description(event.get("description", "")))
        else:
            st.write("No liked events yet.")
    
    # Purchased Events
    st.header("Purchased Events")
    if st.button("Show Purchased Events"):
        purchased_events = get_purchased_events()
        if purchased_events:
            for event in purchased_events:
                st.subheader(event["title"])
                st.write(f"Category: {get_category_name(event.get('category'))}")
                st.write(truncate_description(event.get("description", "")))
        else:
            st.write("No purchased events yet.")

if __name__ == "__main__":
    main()
