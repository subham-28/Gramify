import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- MongoDB Configuration ---

# MONGO_URI="mongodb+srv://aditya:gradientgang@cluster0.d11je.mongodb.net/your_database_name?retryWrites=true&w=majority"
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://aditya:gradientgang@cluster0.d11je.mongodb.net/") # Fallback to localhost for development

SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_lg")