from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import json_util
import json
import config

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

if __name__ == "__main__":
    app.run()  # Modify host/port as needed
