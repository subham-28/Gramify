from fastapi import FastAPI, HTTPException, Request, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import pandas as pd
from typing import Optional
import traceback
import logging
from contextlib import asynccontextmanager
import spacy
import os
from PIL import Image
import google.generativeai as genai
import io

# --- Import project modules ---
from main_update import process_ingredient
from config import SPACY_MODEL
from database import get_mongo_collection, get_ingredients_dataframe, load_ingredients_dataframe
from predict_category_update import get_ingredient_category, get_fasttext_model
from extraction import RecipeMeasurementExtractor, RecipeConverter
from google_voice import voice_to_text
from fastapi.middleware.cors import CORSMiddleware

# --- FastAPI Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Global state ---
nlp_model = None
ft_model = None
recipe_extractor = None
recipe_converter = None
mongo_collection = None
current_ingredients_df = pd.DataFrame()

# ✅ Configure Gemini API
genai.configure(api_key="AIzaSyCElD6bbZyjc-a8evE4R-QMG2Vn_vA-JFk")
gemini_model = genai.GenerativeModel("gemini-1.5-pro")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global nlp_model, ft_model, recipe_extractor, recipe_converter
    global mongo_collection, current_ingredients_df

    logger.info("🚀 Starting up Recipe Converter API...")

    try:
        nlp_model = spacy.load(SPACY_MODEL)
        logger.info(f"✅ SpaCy model '{SPACY_MODEL}' loaded.")
    except Exception as e:
        logger.error(f"❌ Failed to load SpaCy model: {e}")
        raise RuntimeError(f"Could not load SpaCy model: {e}")

    try:
        ft_model = get_fasttext_model()
        logger.info("✅ fastText model loaded.")
    except Exception as e:
        logger.error(f"❌ Failed to load fastText model: {e}")

    recipe_extractor = RecipeMeasurementExtractor(nlp_model=nlp_model)
    recipe_converter = RecipeConverter()

    try:
        mongo_collection = get_mongo_collection()
        current_ingredients_df = load_ingredients_dataframe()
        logger.info(f"✅ Loaded {len(current_ingredients_df)} ingredients from database.")
    except Exception as e:
        logger.error(f"❌ Database load failed: {e}")

    yield
    logger.info("👋 API shutdown complete.")

app = FastAPI(
    title="Recipe Converter API",
    description="API for converting recipe ingredient measurements to grams.",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify frontend URL e.g. ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConvertRequest(BaseModel):
    recipe_text: str = Field(..., example="2 cups flour")
    confirm: bool = Field(False)
    confirmed_ingredient: Optional[str] = None

class NewIngredient(BaseModel):
    name: str
    type: str
    grams_per_cup: Optional[float] = None
    density_g_per_ml: Optional[float] = None
    category: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Welcome to the Recipe Converter API! Use /docs for API documentation."}

@app.post("/convert/")
async def convert_recipe_ingredient(request: ConvertRequest):
    try:
        result = process_ingredient(
            recipe_text=request.recipe_text,
            collection=mongo_collection,
            df=current_ingredients_df,
            extractor=recipe_extractor,
            converter=recipe_converter,
            confirm=request.confirm,
            confirmed_ingredient=request.confirmed_ingredient
        )

        if result.get("confirm_conversion") and "weighs approximately" in result.get("message", ""):
            load_ingredients_dataframe()

        return result
    except Exception as e:
        logger.error(f"Exception in /convert/: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.post("/refresh-data/")
async def refresh_data():
    global current_ingredients_df
    try:
        current_ingredients_df = load_ingredients_dataframe()
        return {"message": f"Reloaded data. {len(current_ingredients_df)} ingredients available."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh data: {str(e)}")

@app.get("/ingredients/")
async def get_all_ingredients():
    global current_ingredients_df
    if current_ingredients_df.empty:
        current_ingredients_df = load_ingredients_dataframe()
    return current_ingredients_df.to_dict(orient="records")

@app.get("/ingredients/{ingredient_name}")
async def get_ingredient_details(ingredient_name: str):
    global current_ingredients_df
    if current_ingredients_df.empty:
        current_ingredients_df = load_ingredients_dataframe()

    row = current_ingredients_df[current_ingredients_df['name'] == ingredient_name.lower()]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Ingredient '{ingredient_name}' not found.")
    return row.iloc[0].to_dict()

@app.post("/ingredients/")
async def add_ingredient(ingredient: NewIngredient):
    global mongo_collection, current_ingredients_df
    try:
        data = ingredient.model_dump(exclude_unset=True)
        data['name'] = data['name'].lower()

        if mongo_collection.find_one({"name": data['name']}):
            raise HTTPException(status_code=409, detail=f"Ingredient '{data['name']}' already exists.")

        mongo_collection.insert_one(data)
        current_ingredients_df = load_ingredients_dataframe()
        return {"message": f"Ingredient '{data['name']}' added successfully."}
    except Exception as e:
        logger.error(f"Error adding ingredient: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add ingredient: {e}")

@app.post("/extract-ingredients/")
async def extract_and_convert_ingredients(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        prompt = "Extract the text from the image."
        response = gemini_model.generate_content([prompt, image])
        extracted_text = response.text.strip()

        if not extracted_text:
            raise ValueError("No text extracted from image.")

        logger.info(f"📷 Extracted Recipe Text:\n{extracted_text}")

        # ✅ Call process_ingredient on the full extracted recipe text
        result = process_ingredient(
            recipe_text=extracted_text,
            collection=mongo_collection,
            df=current_ingredients_df,
            extractor=recipe_extractor,
            converter=recipe_converter,
            confirm=False,
            confirmed_ingredient=None
        )

        return JSONResponse(content={
            "extracted_text": extracted_text,
            "conversion_result": result
        })

    except Exception as e:
        logger.error(f"❌ Error in extract-and-convert: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.post("/voice-input/")
async def voice_input(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        # Save contents to a temp WAV file
        temp_wav = "temp_audio.wav"
        with open(temp_wav, "wb") as f:
            f.write(contents)

        # Now pass this file path to your transcription logic
        transcript = voice_to_text(temp_wav)

        if not transcript:
            raise HTTPException(status_code=400, detail="Could not transcribe any speech.")

        result = process_ingredient(
            recipe_text=transcript,
            collection=mongo_collection,
            df=current_ingredients_df,
            extractor=recipe_extractor,
            converter=recipe_converter,
            confirm=False,
            confirmed_ingredient=None
        )

        return {
            "transcript": transcript,
            "conversion_result": result
        }
    except Exception as e:
        logger.error(f"❌ Error in /voice-input/: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_updated:app", host="0.0.0.0", port=8080, reload=True)
