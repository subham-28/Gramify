import pandas as pd
import pymongo
from pymongo.errors import ConnectionFailure
from config import MONGO_URI

# Global client and database instance
_client = None
_db = None
_collection = None
_df = None # Global DataFrame for ingredients

def get_mongo_collection():
    """Establishes and returns the MongoDB collection."""
    global _client, _db, _collection
    if _collection is None:
        try:
            _client = pymongo.MongoClient(MONGO_URI)
            _client.admin.command('ping') # Test connection
            _db = _client["baking_ai"] # Use the database name specified in your main.py
            _collection = _db["ingredients"]
            print("Successfully connected to MongoDB!")
        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            # In a real app, you might want to raise an exception or log more verbosely
            raise ConnectionFailure(f"Could not connect to MongoDB: {e}")
    return _collection

def load_ingredients_dataframe():
    """Loads and returns the ingredients DataFrame from MongoDB.
    This function will be called on app startup or when data needs to be refreshed.
    """
    global _df
    try:
        collection = get_mongo_collection()
        _df = pd.DataFrame(list(collection.find()))
        if not _df.empty:
            _df['name'] = _df['name'].str.lower()
        print("Ingredients DataFrame loaded/reloaded.")
    except ConnectionFailure:
        print("Failed to load ingredients DataFrame due to MongoDB connection issue.")
        _df = pd.DataFrame(columns=['name', 'type', 'grams_per_cup', 'density_g_per_ml', 'category']) # Return empty DF
    return _df

def get_ingredients_dataframe():
    """Returns the cached ingredients DataFrame.
    If not loaded, attempts to load it.
    """
    global _df
    if _df is None or _df.empty: # Check if dataframe is empty, potentially from failed load or first run
        _df = load_ingredients_dataframe()
    return _df

# Initial load when this module is imported
# This ensures the DataFrame is available as soon as database.py is imported
# However, for a FastAPI app, often you'd do this in an `on_startup` event
# For now, it's fine for simple global access.
_ = get_mongo_collection() # Ensure connection is established on import
_ = load_ingredients_dataframe() # Load the dataframe on import