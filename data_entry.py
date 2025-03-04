from pymongo import MongoClient
import config 

# MongoDB Atlas connection string
mongodb_uri = config.MONGODB_URI
client = MongoClient(mongodb_uri)
db = client.get_database()

# List of original category slugs.
category_slugs = [
    "home-and-lifestyle",
    "performing-and-visual-arts",
    "community",
    "music",
    "food-and-drink",
    "sports-and-fitness",
    "science-and-tech",
    "charity-and-causes",
    "travel-and-outdoor",
    "film-and-media"
]

# Function to convert a slug into a display name.
# It replaces hyphens with spaces and capitalizes the first letter of each word.
def slug_to_display(slug):
    # List of words to keep in lowercase unless they are the first word.
    exceptions = {"and", "or", "the", "of", "in", "for", "with"}
    words = slug.split("-")
    display_words = [words[0].capitalize()]  # Always capitalize the first word.
    for word in words[1:]:
        display_words.append(word if word in exceptions else word.capitalize())
    return " ".join(display_words)

# Create documents with the transformed names.
categories = [{"name": slug_to_display(slug)} for slug in category_slugs]

# Insert the documents into the "categories" collection.
result = db.categories.insert_many(categories)
print("Inserted category ids:", result.inserted_ids)
