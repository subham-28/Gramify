from pymongo import MongoClient

client = MongoClient("mongodb+srv://aditya:gradientgang@cluster0.d11je.mongodb.net/")
db = client["baking_ai"]
collection = db["ingredients"]

# Delete typo entry
result = collection.delete_one({"name": "bttr"})

if result.deleted_count > 0:
    print("✅ 'flur' removed from the database.")
else:
    print("⚠️ 'flur' was not found in the database.")
