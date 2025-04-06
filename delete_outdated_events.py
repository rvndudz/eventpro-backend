# delete_outdated_events.py
import streamlit as st
from datetime import datetime, timezone
import config
from pymongo import MongoClient

# MongoDB setup
mongodb_uri = config.MONGODB_URI
client = MongoClient(mongodb_uri)
db = client.get_database()

def delete_outdated_events():
    """Deletes all outdated events from the DB."""
    now = datetime.now(timezone.utc)
    result = db.events.delete_many({
        "endDateTime": {"$lt": now}
    })
    return result.deleted_count

def get_outdated_events():
    """Fetch events whose endDateTime is in the past."""
    now = datetime.now(timezone.utc)
    return list(db.events.find({
        "endDateTime": {"$lt": now}
    }))

def main():
    st.title("🗑️ Delete Outdated Events")
    st.markdown("Clean up events that have already ended based on their `endDateTime` field.")

    outdated_events = get_outdated_events()
    count = len(outdated_events)

    if count == 0:
        st.success("No outdated events found! 🎉")
        return

    st.warning(f"Found {count} outdated event(s) in the database.")

    if st.checkbox("Show outdated event titles", key="show_outdated_titles"):
        for event in outdated_events:
            st.markdown(f"- **{event.get('title', 'Untitled Event')}** (Ends: `{event.get('endDateTime')}`)")

    if st.button("Delete Outdated Events", key="trigger_delete_btn"):
        st.session_state.confirm_delete = True

    if st.session_state.get("confirm_delete", False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Yes, Delete", key="confirm_delete_btn"):
                deleted_count = delete_outdated_events()
                st.success(f"Deleted {deleted_count} outdated event(s).")
                st.session_state.confirm_delete = False
        with col2:
            if st.button("❌ Cancel", key="cancel_delete_btn"):
                st.info("Deletion cancelled.")
                st.session_state.confirm_delete = False

