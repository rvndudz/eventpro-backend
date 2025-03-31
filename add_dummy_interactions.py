# add_dummy_interactions.py
import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId
import random
from datetime import datetime, timedelta
import uuid
import config

# MongoDB setup
client = MongoClient(config.MONGODB_URI)
db = client.get_database()

def get_random_date_within_last_days(days_range=(1, 30)):
    days_ago = random.randint(*days_range)
    return datetime.utcnow() - timedelta(days=days_ago)

def get_all_users():
    return list(db.users.find())

def add_dummy_order(event_id, user_id):
    db.orders.insert_one({
        "event": ObjectId(event_id),
        "buyer": ObjectId(user_id),
        "createdAt": get_random_date_within_last_days(),
        "stripeId": "cs_test_" + uuid.uuid4().hex[:32],
        "totalAmount": str(random.randint(0, 1000)),
        "__v": 0
    })

def add_dummy_like(event_id, user_id):
    db.likes.insert_one({
        "event": ObjectId(event_id),
        "liker": ObjectId(user_id),
        "createdAt": get_random_date_within_last_days(),
        "__v": 0
    })

def add_dummy_click(event_id, user_id):
    db.clicks.insert_one({
        "event": ObjectId(event_id),
        "clicker": ObjectId(user_id),
        "createdAt": get_random_date_within_last_days(),
        "__v": 0
    })

def main():
    st.title("🧪 Add Dummy Event Interactions")

    st.markdown("Enter multiple event IDs (comma-separated or new line):")
    raw_input = st.text_area("Event IDs", height=150, key="event_input")
    cleaned_ids = list({e.strip() for e in raw_input.replace(",", "\n").splitlines() if e.strip()})

    num_interactions = st.slider("How many interactions per event?", 1, 50, 5)

    if st.button("Generate Dummy Data"):
        if not cleaned_ids:
            st.warning("Please provide at least one event ID.")
            return

        users = get_all_users()
        if not users:
            st.error("No users found in the database.")
            return

        user_ids = [str(user["_id"]) for user in users]
        total_added = 0

        for eid in cleaned_ids:
            for _ in range(num_interactions):
                user_id = random.choice(user_ids)
                add_dummy_order(eid, user_id)
                add_dummy_like(eid, user_id)
                add_dummy_click(eid, user_id)
                total_added += 3

        st.success(f"✅ Inserted {total_added} dummy records across {len(cleaned_ids)} event(s).")

if __name__ == "__main__":
    main()
