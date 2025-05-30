# from sklearn.ensemble import RandomForestRegressor # No longer needed for simple averaging
import pandas as pd
import pymongo
from sklearn.ensemble import RandomForestRegressor
from pymongo.errors import ConnectionFailure
from typing import Tuple
from config import MONGO_URI
from predict_category_update import get_ingredient_category

# Step 1: Connect to MongoDB (handled via get_mongo_collection now)
# client = pymongo.MongoClient(MONGO_URI) # Removed global client
# db = client["baking_ai"] # Removed global db
# collection = db["ingredients"] # Removed global collection

# Helper to get collection (re-using database.py's logic)
def get_mongo_collection_for_prediction():
    # This helper function ensures predict_missing_densities.py
    # also gets its collection via the centralized method, avoiding direct client creation.
    # It avoids a circular import with database.py if database.py imports this file,
    # by defining a local client.
    # A better approach would be to pass the collection as an argument.
    # For now, let's make it get its own connection if it's called standalone.
    # If called via app.py, collection is passed, so this might be redundant.
    try:
        client = pymongo.MongoClient(MONGO_URI)
        client.admin.command('ping')
        return client["baking_ai"]["ingredients"]
    except ConnectionFailure as e:
        print(f"MongoDB connection failed in predict_missing_densities: {e}")
        raise ConnectionFailure(f"Could not connect to MongoDB for prediction: {e}")


# Function to get similar ingredients (now accepting collection)
def get_similar_ingredients(category: str, collection) -> pd.DataFrame:
    """Retrieve ingredients of the same category from MongoDB."""
    similar_items = list(collection.find({"category": category}, {"_id": 0}))
    return pd.DataFrame(similar_items)

# Function to detect solid or liquid by density
def predict_type_by_density(density: float) -> str:
    """Predicts if an ingredient is 'Liquid' or 'Solid' based on its density."""
    return "Liquid" if density >= 0.9 else "Solid" # Common threshold, 0.9 g/ml approx. for water

# Function to predict missing densities (now directly estimating averages)
def predict_densities(ingredient_name: str) -> Tuple[str, float, float, str, str]:
    """
    Predict density and grams per cup for a new ingredient based on its predicted category
    and the average values within that category.
    """
    # 1. Get the ingredient's category
    # Ensure get_ingredient_category has access to its collection
    # For now, it gets its own, but ideally should be passed.
    category = get_ingredient_category(ingredient_name)

    if not category:
        # Fallback if category prediction fails
        # You might want to assign a 'default' category or raise an error
        print(f"Warning: Could not predict category for '{ingredient_name}'. Using 'unknown'.")
        category = "unknown" # Fallback category

    # Get the MongoDB collection
    collection = get_mongo_collection_for_prediction()

    # 2. Get all known ingredients in that category
    df_category = get_similar_ingredients(category, collection)

    if df_category.empty:
        # Fallback if no known data for this category
        print(f"No existing data for category '{category}'. Assigning default values.")
        # Provide sensible defaults or raise an error
        predicted_density_ml = 1.0 # Default density for liquids (like water)
        predicted_grams_per_cup = 240.0 # Default grams per cup for liquid (like water)
        predicted_type = "Liquid" # Assume liquid if no category data
    else:
        # 3. Calculate the average grams_per_cup and density for this category
        # Filter out rows where essential values might be missing before calculating mean
        df_valid_data = df_category.dropna(subset=['grams_per_cup', 'density_g_per_ml'])

        if df_valid_data.empty:
            print(f"No valid 'grams_per_cup' or 'density_g_per_ml' data in category '{category}'. Assigning default values.")
            predicted_density_ml = 1.0
            predicted_grams_per_cup = 240.0
            predicted_type = "Liquid"
        if len(df_valid_data)>=10:
            X = df_valid_data[["density_g_per_ml"]]
            y = df_valid_data["grams_per_cup"]
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            avg_density = df_valid_data["density_g_per_ml"].mean()
            predicted_grams_per_cup = model.predict([[avg_density]])[0]
            predicted_density_ml=avg_density
            predicted_type = predict_type_by_density(predicted_density_ml)
        else:
            predicted_grams_per_cup = df_valid_data["grams_per_cup"].mean()
            predicted_density_ml = df_valid_data["density_g_per_ml"].mean()
            # 4. Identify if the ingredient is solid or liquid based on the predicted density
            predicted_type = predict_type_by_density(predicted_density_ml)

    print(f"Predicted properties for '{ingredient_name}': Density={predicted_density_ml:.3f} g/ml, Grams/Cup={predicted_grams_per_cup:.2f}g, Type={predicted_type}, Category={category}")
    return ingredient_name, predicted_density_ml, predicted_grams_per_cup, category, predicted_type
    
# Step 7: Store Prediction in Database (now accepting collection as arg)
def add_prediction_to_db(ingredient_name: str, predicted_density: float, predicted_grams_per_cup: float, predicted_type: str, cate: str, collection) -> None:
    """
    Adds a predicted ingredient's properties to the database.
    """
    new_ingredient = {
        "name": ingredient_name.lower(), # Ensure consistency
        "density_g_per_ml": predicted_density,
        "grams_per_cup": predicted_grams_per_cup,
        "category": cate,
        "type": predicted_type
    }
    try:
        collection.insert_one(new_ingredient)
        print(f"Inserted predicted ingredient '{ingredient_name}' into database.")
    except pymongo.errors.PyMongoError as e:
        print(f"Error inserting predicted ingredient '{ingredient_name}' into DB: {e}")