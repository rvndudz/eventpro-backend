# email_recommendation.py
import streamlit as st
import json
from bson.objectid import ObjectId
from contentBasedRecSystem import get_recommended_event_ids
import config
import pymongo

# MongoDB connection
mongodb_uri = config.MONGODB_URI
client = pymongo.MongoClient(mongodb_uri)
db = client.get_database()

EVENT_BASE_URL = "http://localhost:3000/events"

def get_user_name_email(user_doc):
    first_name = user_doc.get("firstName", "Unknown User")
    last_name = user_doc.get("lastName", "")
    email = user_doc.get("email", "unknown@example.com")
    return first_name, last_name, email

def get_event_details(event_ids):
    event_details = []
    for eid in event_ids:
        try:
            event = db.events.find_one({"_id": ObjectId(eid)})
            if event:
                title = event.get("title", "Untitled Event")
                link = f"{EVENT_BASE_URL}/{eid}"
                event_details.append({"title": title, "link": link})
        except Exception:
            continue
    return event_details

def main():
    st.title("Send Email Recommendations")
    st.markdown("This tool prepares personalized emails with recommended events for all users in the system.")

    if st.button("Generate Email Recommendations"):
        users = list(db.users.find())
        if not users:
            st.warning("No users found.")
            return

        email_data = []

        for user in users:
            user_id = str(user["_id"])
            first_name, last_name, email = get_user_name_email(user)
            recommended_ids = get_recommended_event_ids(user_id, db, top_n=5)
            recommended_events = get_event_details(recommended_ids)

            if not recommended_events:
                continue

            email_content = {
                "first_name": first_name,
                "last_name": last_name,
                "user_email": email,
                "recommended_events": recommended_events
            }
            email_data.append(email_content)

        if not email_data:
            st.info("No recommendations found.")
            return

        st.success("Emails prepared!")
        st.json(email_data)

        st.download_button(
            label="📥 Download Email JSON",
            data=json.dumps(email_data, indent=2),
            file_name="email_recommendations.json",
            mime="application/json"
        )
