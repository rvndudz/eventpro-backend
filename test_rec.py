import time
import uuid
import matplotlib.pyplot as plt
from pymongo import MongoClient
from bson.objectid import ObjectId
from contentBasedRecSystem import get_recommended_event_ids  # Adjust this import as needed
import config

# --- MongoDB Setup (hardcoded) ---
mongodb_uri = config.MONGODB_URI
client = MongoClient(mongodb_uri)
db = client.get_database()

# Test user
user_id = '67d6addee62e8f20f5a9cbae'
user_obj = ObjectId(user_id)

# --- Warm-Up Phase (for handshake, cache, etc.) ---
print("Warming up MongoDB connection and TF-IDF setup...")
get_recommended_event_ids(user_id, db)
print("✅ Warm-up complete.\n")


# --- Stress Test Function ---
def simulate_interactions_and_measure(interaction_type, max_interactions=100, step=10):
    x_vals = []
    y_vals = []

    for count in range(0, max_interactions + 1, step):
        # Clear interactions before test
        db.orders.delete_many({"buyer": user_obj})
        db.likes.delete_many({"liker": user_obj})

        # Insert dummy interactions
        collection = db.orders if interaction_type == "orders" else db.likes
        for _ in range(count):
            sample_event = db.events.aggregate([{"$sample": {"size": 1}}]).next()
            if interaction_type == "orders":
                collection.insert_one({
                    "buyer": user_obj,
                    "event": sample_event["_id"],
                    "stripeId": str(uuid.uuid4())
                })
            else:
                collection.insert_one({
                    "liker": user_obj,
                    "event": sample_event["_id"]
                })

        # Measure recommendation time
        start = time.time()
        get_recommended_event_ids(user_id, db)
        elapsed = time.time() - start

        print(f"{interaction_type.title():<6} = {count:>3} → Time = {elapsed:.4f} sec")
        x_vals.append(count)
        y_vals.append(elapsed)

    return x_vals, y_vals


# --- Run Stress Tests ---
orders_x, orders_y = simulate_interactions_and_measure("orders")
likes_x, likes_y = simulate_interactions_and_measure("likes")

# --- Plotting ---
plt.figure(figsize=(10, 5))
plt.plot(orders_x, orders_y, marker='o')
plt.title("Time vs Number of Orders")
plt.xlabel("Number of Orders")
plt.ylabel("Time to Recommend (seconds)")
plt.grid(True)
plt.savefig("graph_orders_vs_time.png")
plt.show()

plt.figure(figsize=(10, 5))
plt.plot(likes_x, likes_y, marker='o', color='orange')
plt.title("Time vs Number of Likes")
plt.xlabel("Number of Likes")
plt.ylabel("Time to Recommend (seconds)")
plt.grid(True)
plt.savefig("graph_likes_vs_time.png")
plt.show()
