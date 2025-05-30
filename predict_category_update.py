# fastText + RandomForest version of get_ingredient_category with pipeline and cached model

from gensim.models import KeyedVectors
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline, FunctionTransformer
from sklearn.metrics import classification_report
import pandas as pd
import numpy as np
import pymongo
from pymongo.errors import ConnectionFailure
import os
from config import MONGO_URI

_ft_model = None  # private global cache

def get_fasttext_model():
    global _ft_model
    if _ft_model is None:
        print("🔄 Loading fastText model...")
        ft_path = os.path.join(r"C:\100 Days of ML\Gramify\new\crawl-300d-2M.vec")
        _ft_model = KeyedVectors.load_word2vec_format(ft_path, binary=False)
        print("✅ fastText model loaded.")
    return _ft_model

# Connect to MongoDB
def get_mongo_collection_for_category_prediction():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        client.admin.command('ping')
        return client["baking_ai"]["ingredients"]
    except ConnectionFailure as e:
        print(f"MongoDB connection failed in predict_category: {e}")
        raise ConnectionFailure(f"Could not connect to MongoDB for category prediction: {e}")

# Get vector representation using fastText
def get_fasttext_vector_batch(names):
    ft_model = get_fasttext_model()
    def single_vector(name):
        words = name.lower().split()
        word_vecs = [ft_model[w] for w in words if w in ft_model]
        if not word_vecs:
            return np.zeros(ft_model.vector_size)
        return np.mean(word_vecs, axis=0)
    return np.vstack([single_vector(name) for name in names])

# Main prediction function using pipeline
def get_ingredient_category(ingredient_name: str, collection=None) -> str:
    if collection is None:
        collection = get_mongo_collection_for_category_prediction()

    df = pd.DataFrame(list(collection.find({"category": {"$exists": True}}, {"_id": 0, "name": 1, "category": 1})))

    if df.empty:
        print("No category data found in the database. Cannot predict category.")
        return "unknown"

    df['name'] = df['name'].str.lower()
    ingredient_name = ingredient_name.lower()

    if len(set(df['category'])) < 2:
        print("Not enough category variety to train model.")
        return "unknown"

    # Define pipeline with custom transformer for fastText vectorization
    pipeline = make_pipeline(
        FunctionTransformer(get_fasttext_vector_batch, validate=False),
        RandomForestClassifier(n_estimators=100, random_state=42)
    )

    pipeline.fit(df['name'], df['category'])

    predicted_category = pipeline.predict([ingredient_name])[0]
    print(f"Predicted category for '{ingredient_name}': {predicted_category}")
    return predicted_category
