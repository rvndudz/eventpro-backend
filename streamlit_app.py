import streamlit as st
import io
import sys
import uuid
from datetime import datetime
from functools import partial

# APScheduler for background scheduling
from apscheduler.schedulers.background import BackgroundScheduler

# MongoDB
from pymongo import MongoClient
import config

from streamlit_rec import main as recommended_events_main

from email_recommendation import main as email_recommendation_main

# Connect to MongoDB
mongodb_uri = config.MONGODB_URI
client = MongoClient(mongodb_uri)
db = client.get_database()

# Import your badge update functions
from badge_functions import (
    update_top_rated_badges,
    update_popular_choice_badges,
    update_just_announced_badges,
    update_limited_seats_badges,
    update_fast_selling_badges,
)

# Import your recommendation function
from contentBasedRecSystem import get_recommended_event_ids
from bson.objectid import ObjectId

# ----------------------------------------------------------------------------- 
# 1. APScheduler Initialization in Session State 
# -----------------------------------------------------------------------------
if "scheduler" not in st.session_state:
    st.session_state.scheduler = BackgroundScheduler()
    st.session_state.scheduler.start()

if "jobs" not in st.session_state:
    st.session_state.jobs = {}

# ----------------------------------------------------------------------------- 
# 2. Define Badge Update Checkbox Keys and Their Defaults 
# -----------------------------------------------------------------------------
checkbox_keys = ["top_rated", "popular_choice", "just_announced", "limited_seats", "fast_selling"]
for key in checkbox_keys:
    if key not in st.session_state:
        st.session_state[key] = False

# ----------------------------------------------------------------------------- 
# 3. Functions for Badge Updates 
# -----------------------------------------------------------------------------
def run_selected_badges(top_rated, popular_choice, just_announced, limited_seats, fast_selling):
    """Runs whichever badge-update functions correspond to the user’s selections."""
    if top_rated:
        update_top_rated_badges()
    if popular_choice:
        update_popular_choice_badges()
    if just_announced:
        update_just_announced_badges()
    if limited_seats:
        update_limited_seats_badges()
    if fast_selling:
        update_fast_selling_badges()

def run_and_capture_output():
    """Captures console output from running selected badge updates."""
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer
    try:
        run_selected_badges(
            st.session_state["top_rated"],
            st.session_state["popular_choice"],
            st.session_state["just_announced"],
            st.session_state["limited_seats"],
            st.session_state["fast_selling"],
        )
    except Exception as e:
        print("Error during update:", e)
    sys.stdout = old_stdout
    return buffer.getvalue()

def clear_checkboxes():
    """Clears the badge update checkboxes in session state."""
    for key in checkbox_keys:
        st.session_state[key] = False

# ----------------------------------------------------------------------------- 
# 4. Scheduling Helpers 
# -----------------------------------------------------------------------------
interval_options = {
    "Every 5 minutes": 5,
    "Every 10 minutes": 10,
    "Every 15 minutes": 15,
    "Every 30 minutes": 30,
    "Every 1 hour": 60,
    "Every 3 hours": 180,
    "Every 5 hours": 300,
    "Every 10 hours": 600,
    "Every 24 hours": 1440,
    "Every 48 hours": 2880,
}

def schedule_job(selected_interval):
    """Schedules a new job using APScheduler, based on the selected checkboxes."""
    interval_minutes = interval_options[selected_interval]
    job_func = partial(
        run_selected_badges,
        st.session_state["top_rated"],
        st.session_state["popular_choice"],
        st.session_state["just_announced"],
        st.session_state["limited_seats"],
        st.session_state["fast_selling"],
    )

    job_id = str(uuid.uuid4())
    st.session_state.scheduler.add_job(
        func=job_func,
        trigger='interval',
        minutes=interval_minutes,
        id=job_id,
    )

    st.session_state.jobs[job_id] = {
        "interval": selected_interval,
        "top_rated": st.session_state["top_rated"],
        "popular_choice": st.session_state["popular_choice"],
        "just_announced": st.session_state["just_announced"],
        "limited_seats": st.session_state["limited_seats"],
        "fast_selling": st.session_state["fast_selling"],
        "created_at": datetime.utcnow().isoformat(),
    }
    st.success(f"Scheduled new job (ID: {job_id[:8]}) to run every {interval_minutes} minute(s).")

# ----------------------------------------------------------------------------- 
# 5. Sidebar for Switching Panels via Buttons 
# -----------------------------------------------------------------------------
if "selected_panel" not in st.session_state:
    st.session_state.selected_panel = "Badge Updates"

with st.sidebar:
    st.markdown("## Switch Panel")
    if st.button("Badge Updates"):
        st.session_state.selected_panel = "Badge Updates"
    if st.button("Recommended Events"):
        st.session_state.selected_panel = "Recommended Events"
    if st.button("Database Management"):
        st.session_state.selected_panel = "Database Management"
    if st.button("Send Email Recommendations"):
        st.session_state.selected_panel = "Send Email Recommendations"


# ----------------------------------------------------------------------------- 
# 6. Helper: Fetch Events by IDs 
# -----------------------------------------------------------------------------
def get_events_by_ids(event_ids):
    """
    Given a list of event ID strings, fetch the corresponding event documents from the database.
    """
    valid_ids = [ObjectId(id_str) for id_str in event_ids if ObjectId.is_valid(id_str)]
    events = list(db.events.find({"_id": {"$in": valid_ids}}))
    return events

# ----------------------------------------------------------------------------- 
# 7. Main Panel Content Based on the Active Panel 
# -----------------------------------------------------------------------------
if st.session_state.selected_panel == "Badge Updates":
    # --------------------------
    # BADGE UPDATER PANEL
    # --------------------------
    st.title("EventPro Badge Updater")

    st.markdown("### Select the badge updates you want to perform:")
    st.checkbox("Top Rated Badges", key="top_rated")
    st.checkbox("Popular Choice Badges", key="popular_choice")
    st.checkbox("Just Announced Badges", key="just_announced")
    st.checkbox("Limited Seats Badges", key="limited_seats")
    st.checkbox("Fast Selling Badges", key="fast_selling")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Instant Update"):
            if not any(st.session_state[key] for key in checkbox_keys):
                st.warning("No badge update selected. Please check at least one box.")
            else:
                output = run_and_capture_output()
                st.info("Instant Update completed. Details below:")
                st.code(output, language="bash")
    with col2:
        st.button("Clear", on_click=clear_checkboxes)

    st.write("---")
    st.markdown("### Schedule Recurring Updates")

    if "selected_interval" not in st.session_state:
        st.session_state["selected_interval"] = "Every 5 minutes"

    selected_interval = st.selectbox(
        "Choose how often to run the updates:",
        list(interval_options.keys()),
        index=0,
        key="selected_interval"
    )

    if st.button("Schedule Recurring Update"):
        if not any(st.session_state[key] for key in checkbox_keys):
            st.warning("No badge update selected. Please check at least one box.")
        else:
            schedule_job(selected_interval)

    st.write("---")
    st.subheader("Scheduled Jobs")

    if len(st.session_state.jobs) == 0:
        st.info("No jobs currently scheduled.")
    else:
        for job_id, info in list(st.session_state.jobs.items()):
            display_id = job_id[:8]
            interval_label = info["interval"]
            created_at = info["created_at"]

            tasks = []
            if info["top_rated"]:
                tasks.append("Top Rated")
            if info["popular_choice"]:
                tasks.append("Popular Choice")
            if info["just_announced"]:
                tasks.append("Just Announced")
            if info["limited_seats"]:
                tasks.append("Limited Seats")
            if info["fast_selling"]:
                tasks.append("Fast Selling")
            tasks_str = ", ".join(tasks)

            colA, colB, colC = st.columns([2, 3, 1])
            with colA:
                st.markdown(f"**Job ID:** `{display_id}`")
                st.markdown(f"**Interval:** {interval_label}")
                st.markdown(f"**Created:** {created_at}")
            with colB:
                st.markdown(f"**Badge Updates:** {tasks_str}")
            with colC:
                if st.button("Cancel", key=f"cancel_{job_id}"):
                    try:
                        st.session_state.scheduler.remove_job(job_id)
                    except Exception as e:
                        st.error(f"Error cancelling job: {e}")
                    del st.session_state.jobs[job_id]
                    st.warning(f"Cancelled job: {display_id}")

    st.write("---")
    st.info("Scheduled jobs run in the background as long as this app is active.")

elif st.session_state.selected_panel == "Recommended Events":
    # Use the main function from streamlit_rec.py
    recommended_events_main()

elif st.session_state.selected_panel == "Send Email Recommendations":
    email_recommendation_main()

else:
    # --------------------------
    # DATABASE MANAGEMENT PANEL
    # --------------------------
    st.title("Database Management")
    st.markdown("Select collections to clear all documents from. **Warning**: This is irreversible!")

    # List your collections here
    collections = ["categories", "clicks", "events", "likes", "orders", "users"]

    if "collections_to_clear" not in st.session_state:
        st.session_state.collections_to_clear = {c: False for c in collections}

    if "confirmation_pending" not in st.session_state:
        st.session_state.confirmation_pending = False

    if "selected_collections_for_deletion" not in st.session_state:
        st.session_state.selected_collections_for_deletion = []

    for c in collections:
        st.session_state.collections_to_clear[c] = st.checkbox(
            c,
            value=st.session_state.collections_to_clear[c],
            key=f"clear_{c}"
        )

    if st.button("Clear Selected"):
        selected = [c for c, val in st.session_state.collections_to_clear.items() if val]
        if not selected:
            st.warning("No collections selected.")
        else:
            st.session_state.selected_collections_for_deletion = selected
            st.session_state.confirmation_pending = True

    if st.session_state.confirmation_pending:
        st.error("You are about to clear the following collections. This action is irreversible!")
        st.write(st.session_state.selected_collections_for_deletion)

        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("Yes, I'm sure"):
                for c in st.session_state.selected_collections_for_deletion:
                    db[c].delete_many({})
                    st.warning(f"Cleared all documents from `{c}` collection.")
                st.session_state.confirmation_pending = False
                st.session_state.selected_collections_for_deletion = []
        with col_cancel:
            if st.button("Cancel"):
                st.session_state.confirmation_pending = False
                st.session_state.selected_collections_for_deletion = []
                st.info("Deletion cancelled.")

    st.write("---")
    st.markdown("## Database Management")
