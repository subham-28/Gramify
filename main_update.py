from difflib import get_close_matches
import nltk
import spacy
# from word2number import w2n # Not directly used in main, but common for NLP projects
# import re # Not directly used in main, but common for NLP projects
# from fractions import Fraction # Not directly used in main, but common for NLP projects
import pandas as pd
from typing import Optional, Tuple, Set, List, Dict, Union

# Import RecipeMeasurementExtractor and RecipeConverter from your extraction.py
from extraction import RecipeMeasurementExtractor, RecipeConverter

# Import functions from your prediction modules
from predict_missing_densities_updated import predict_densities, add_prediction_to_db
from predict_category_update import get_ingredient_category

# Import database functions
from database import get_mongo_collection, get_ingredients_dataframe, load_ingredients_dataframe

# Import config for SPACY_MODEL
from config import SPACY_MODEL

# Ensure nltk data is downloaded (run once, or include in Dockerfile if deployed)
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

def get_suggestion(ingredient: str, known_ingredients: list) -> Optional[str]:
    """
    Finds a close match for an ingredient in a list of known ingredients.
    """
    if not ingredient:
        print("Warning: get_suggestion received None or empty ingredient.")
        return None
    lower_known = [name.lower() for name in known_ingredients]
    suggestion = get_close_matches(ingredient.lower(), lower_known, n=1, cutoff=0.75)
    return suggestion[0] if suggestion else None


# --- Main processing function ---

def process_ingredient(
    recipe_text: str,
    collection, # MongoDB collection
    df: pd.DataFrame, # Ingredient DataFrame
    extractor: RecipeMeasurementExtractor, # The extractor instance
    converter: RecipeConverter, # The converter instance
    confirm: bool = False,
    confirmed_ingredient: Optional[str] = None
) -> dict:
    
    results = extractor.extract_measurements(recipe_text)

    # print(f"Extractor results for '{recipe_text}': {results}") # Debugging line - keep this on for now!

    if not results or results[0]['quantity'] is None or results[0]['unit'] is None:
        return {
            "message": "Could not identify quantity or unit. Please rephrase.",
            "confirm_conversion": False
        }
    
    quantity = results[0]['quantity']
    unit = results[0]['unit']
    extracted_ingredient = results[0]['ingredient']
    target_unit = results[0]['target_unit'] # This is the target unit extracted directly from user input

    final_ingredient_name = extracted_ingredient # Start with extracted ingredient


    # If ingredient could not be extracted by NLP but quantity and unit were, treat as unknown for now
    if extracted_ingredient is None:
        if not confirm:
            return {
                "message": f"Could not identify the ingredient for '{recipe_text}'. Please specify it more clearly or confirm to predict.",
                "confirm_conversion": False
            }
        else:
            if confirmed_ingredient is None:
                return {
                    "message": "Cannot predict properties for an unknown ingredient without a specified ingredient name (e.g., 'confirmed_ingredient' parameter).",
                    "confirm_conversion": False
                }
            final_ingredient_name = confirmed_ingredient.lower() # Use confirmed_ingredient as the ingredient to process

    # --- Handle confirmed_ingredient first ---
    if confirmed_ingredient:
        final_ingredient_name = confirmed_ingredient.lower()
        ingredient_exists_in_df = final_ingredient_name in df['name'].values

        if not ingredient_exists_in_df and confirm:
            pass
        elif ingredient_exists_in_df:
            row = df[df['name'] == final_ingredient_name]
            if row.empty:
                return {
                    "message": f"Confirmed ingredient '{final_ingredient_name}' found in DB but row could not be retrieved.",
                    "confirm_conversion": False
                }
            
            row = row.iloc[0]
            typ = row['type'].lower() if 'type' in row and not pd.isna(row['type']) else None
            grams_per_cup = row['grams_per_cup'] if 'grams_per_cup' in row and not pd.isna(row['grams_per_cup']) else None
            density_g_per_ml = row['density_g_per_ml'] if 'density_g_per_ml' in row and not pd.isna(row['density_g_per_ml']) else None

            # Use effective_target_unit here
            if unit in ["grams","gm","gms","gram","grms","grm","ml","mililitre","mlitre","cc","milliliter","millil","l","litre","liter","quart", "quarts", "qt","quart", "quarts", "qt","pint", "pints", "pt","fl oz", "fluid ounce", "fluid ounces","kilogram","ounce","pound"]:
                converted_qty, converted_unit_name = converter.convert_to_vague_units(
                    quantity, unit, typ, grams_per_cup, density_g_per_ml, target_unit
                )
                if converted_qty is None:
                    return {
                        "message": f"Could not convert {quantity} {unit} of {final_ingredient_name} to {target_unit} after confirmation. Ensure quantity and unit are clear and ingredient properties are available.",
                        "confirm_conversion": True
                    }
                return {
                    "message": f"{quantity} {unit} of {final_ingredient_name} is approximately {converted_qty:.2f} {converted_unit_name}.",
                    "confirm_conversion": True
                }
            else: # Fallback if no effective_target_unit (should ideally be handled above or explicitly converted to grams)
                grams = converter.convert_to_grams(quantity, unit, final_ingredient_name, df)
                if grams is None:
                    return {
                        "message": "Could not convert the ingredient after confirmation. Ensure quantity and unit are clear.",
                        "confirm_conversion": True
                    }
                elif typ in ["Solid","solid"]:
                    return {
                        "message": f"{quantity} {unit} of {final_ingredient_name} weighs approximately {grams:.2f} grams.",
                        "confirm_conversion": True
                    }
                elif typ in ["Liquid","liquid"]:
                    return {
                        "message": f"{quantity} {unit} of {final_ingredient_name} weighs approximately {grams:.2f} mililitre.",
                        "confirm_conversion": True
                    }
    
    # --- Handle fuzzy matching and unknown ingredients for the first pass or unconfirmed attempts ---
    ingredient_exists_in_df = final_ingredient_name in df['name'].values

    if not ingredient_exists_in_df:
        suggestion = get_suggestion(final_ingredient_name, df['name'].tolist())

        if suggestion and not confirm:
            return {
                "message": f"Ingredient '{final_ingredient_name}' not found. Did you mean '{suggestion}'?",
                "suggested_ingredient": suggestion,
                "confirm_conversion": False
            }
        else:
            if confirm:
                try:
                    predicted_name, density, grams_per_cup_pred, cate, typ_pred = predict_densities(final_ingredient_name)
                    add_prediction_to_db(predicted_name, density, grams_per_cup_pred, typ_pred, cate, collection)
                    
                    global ingredients_df
                    ingredients_df = load_ingredients_dataframe()

                    row = ingredients_df[ingredients_df['name'] == predicted_name]
                    if row.empty:
                        raise ValueError(f"Predicted ingredient '{predicted_name}' not found in reloaded DataFrame.")

                    row = row.iloc[0]
                    typ_reloaded = row['type'].lower() if 'type' in row and not pd.isna(row['type']) else None
                    grams_per_cup_reloaded = row['grams_per_cup'] if 'grams_per_cup' in row and not pd.isna(row['grams_per_cup']) else None
                    density_g_per_ml_reloaded = row['density_g_per_ml'] if 'density_g_per_ml' in row and not pd.isna(row['density_g_per_ml']) else None

                    # Use effective_target_unit here as well
                    if unit in ["grams","gm","gms","gram","grms","grm","ml","mililitre","mlitre","cc","milliliter","millil","l","litre","liter","quart", "quarts", "qt","quart", "quarts", "qt","pint", "pints", "pt","fl oz", "fluid ounce", "fluid ounces","kilogram","ounce","pound"]:
                        converted_qty, converted_unit_name = converter.convert_to_vague_units(
                            quantity, unit, typ_reloaded, grams_per_cup_reloaded, density_g_per_ml_reloaded, target_unit
                        )
                        if converted_qty is None:
                            return {
                                "message": "Successfully predicted properties, but could not convert to target unit. Ensure quantity and unit are clear.",
                                "confirm_conversion": True
                            }
                        return {
                            "message": f"{quantity} {unit} of {predicted_name} is approximately {converted_qty:.2f} {converted_unit_name}.",
                            "confirm_conversion": True
                        }
                    else: # Fallback if no effective_target_unit
                        grams = converter.convert_to_grams(quantity, unit, predicted_name, ingredients_df)
                        if grams is None:
                            return {
                                "message": "Successfully predicted properties, but could not convert. Ensure quantity and unit are clear.",
                                "confirm_conversion": True
                            }
                        elif typ in ["Solid","solid"]:
                            return {
                                "message": f"{quantity} {unit} of {final_ingredient_name} weighs approximately {grams:.2f} grams.",
                                "confirm_conversion": True
                            }
                        elif typ in ["Liquid","liquid"]:
                            return {
                                "message": f"{quantity} {unit} of {final_ingredient_name} weighs approximately {grams:.2f} mililitre.",
                                "confirm_conversion": True
                            }
                except Exception as e:
                    return {
                        "message": f"Could not predict properties for '{final_ingredient_name}'. Error: {str(e)}",
                        "confirm_conversion": False
                    }
            else:
                return {
                    "message": f"Ingredient '{final_ingredient_name}' not found. Please provide exact name or confirm to predict.",
                    "confirm_conversion": False
                }
    
   
    row = df[df['name'] == final_ingredient_name]
    if row.empty:
        return {
            "message": f"Ingredient '{final_ingredient_name}' unexpectedly not found in DataFrame.",
            "confirm_conversion": False
        }

    row = row.iloc[0]
    typ = row['type'].lower() if 'type' in row and not pd.isna(row['type']) else None
    grams_per_cup = row['grams_per_cup'] if 'grams_per_cup' in row and not pd.isna(row['grams_per_cup']) else None
    density_g_per_ml = row['density_g_per_ml'] if 'density_g_per_ml' in row and not pd.isna(row['density_g_per_ml']) else None

    # Use effective_target_unit in the final conversion step
    if unit in ["grams","gm","gms","gram","grms","grm","ml","mililitre","mlitre","cc","milliliter","millil","l","litre","liter","quart", "quarts", "qt","quart", "quarts", "qt","pint", "pints", "pt","fl oz", "fluid ounce", "fluid ounces","kilogram","ounce","pound"]:
        converted_qty, converted_unit_name = converter.convert_to_vague_units(
            quantity, unit, typ, grams_per_cup, density_g_per_ml, target_unit
        )
    
        if converted_qty is None:
            return {
                "message": f"Could not convert {quantity} {unit} of {final_ingredient_name} to {target_unit}. Ensure quantity and unit are clear and ingredient properties are available.",
                "confirm_conversion": True
            }
        return {
            "message": f"{quantity} {unit} of {final_ingredient_name} is approximately {converted_qty:.2f} {converted_unit_name}.",
            "confirm_conversion": True
        }
    else: # Fallback for cases where no effective_target_unit is set (e.g., input is 'cup' and no target unit)
        grams = converter.convert_to_grams(quantity, unit, final_ingredient_name, df)
        if grams is None:
            return {
                "message": "Could not convert the ingredient. Ensure quantity and unit are clear or ingredient is known.",
                "confirm_conversion": True
            }

        elif typ in ["Solid","solid"]:
            return {
                "message": f"{quantity} {unit} of {final_ingredient_name} weighs approximately {grams:.2f} grams.",
                "confirm_conversion": True
            }
        elif typ in ["Liquid","liquid"]:
            return {
                "message": f"{quantity} {unit} of {final_ingredient_name} weighs approximately {grams:.2f} mililitre.",
                "confirm_conversion": True
            }

# # --- Example Usage (How you would run this) ---
# if __name__ == "__main__":
#     # Initialize spaCy model, extractor, and converter once
#     print("Loading spaCy model...")
#     # Use SPACY_MODEL from config
#     # To handle the 'en_core_web_lg' model, make sure it's downloaded:
#     # python -m spacy download en_core_web_lg
#     try:
#         nlp = spacy.load(SPACY_MODEL) 
#     except OSError:
#         print(f"SpaCy model '{SPACY_MODEL}' not found. Attempting to download...")
#         spacy.cli.download(SPACY_MODEL)
#         nlp = spacy.load(SPACY_MODEL)

#     extractor = RecipeMeasurementExtractor(nlp_model=nlp)
#     converter = RecipeConverter()

#     # Get MongoDB collection and initial DataFrame
#     print("Connecting to MongoDB and loading ingredients...")
#     mongo_collection = get_mongo_collection()
#     ingredients_df = get_ingredients_dataframe() 

#     print("\n--- Test Cases ---")

#     # Test 1: Simple gram conversion of a known ingredient
#     print("\nTest 1: 2 cups flour to grams")
#     result1 = process_ingredient(
#         recipe_text="2 cups flour",
#         collection=mongo_collection,
#         df=ingredients_df,
#         extractor=extractor,
#         converter=converter,
#         confirm=False
#     )
#     print(result1)

#     # Test 2: Vague unit conversion of a known ingredient
#     print("\nTest 2: 100 grams butter to tablespoons")
#     result2 = process_ingredient(
#         recipe_text="100 grams butter to tablespoons",
#         collection=mongo_collection,
#         df=ingredients_df,
#         extractor=extractor,
#         converter=converter,
#         confirm=False
#     )
#     print(result2)

#     # Test 3: Unknown ingredient, expecting a suggestion
#     print("\nTest 3: 1 cup all-purpose floour")
#     result3 = process_ingredient(
#         recipe_text="1 cup all-purpose floour",
#         collection=mongo_collection,
#         df=ingredients_df,
#         extractor=extractor,
#         converter=converter,
#         confirm=False
#     )
#     print(result3)

#     # Test 4: 1 cup quinoa (confirm prediction)
#     # NOTE: This will add to your DB. Ensure your DB is set up correctly.
#     print("\nTest 4: 1 cup quinoa (confirm prediction)")
#     result4 = process_ingredient(
#         recipe_text="1 cup quinoa",
#         collection=mongo_collection,
#         df=ingredients_df, # Pass the current df, prediction logic will reload if successful
#         extractor=extractor,
#         converter=converter,
#         confirm=True,
#         confirmed_ingredient="quinoa" 
#     )
#     print(result4)
#     # After this, the global ingredients_df is reloaded within process_ingredient if prediction is successful.

#     # Test 5: Conversion of a confirmed/predicted ingredient (quinoa)
#     print("\nTest 5: 200 grams quinoa to cups")
#     result5 = process_ingredient(
#         recipe_text="200 grams quinoa to cups",
#         collection=mongo_collection,
#         df=ingredients_df, # Use the global df, which is now reloaded
#         extractor=extractor,
#         converter=converter,
#         confirm=False
#     )
#     print(result5)

#     # Test 6: Just some random text
#     print("\nTest 6: Just some random text")
#     result6 = process_ingredient(
#         recipe_text="Just some random text",
#         collection=mongo_collection,
#         df=ingredients_df,
#         extractor=extractor,
#         converter=converter,
#         confirm=False
#     )
#     print(result6)

   
#     print("\nTest 7: flour (no quantity/unit)")
#     result7 = process_ingredient(
#         recipe_text="flour",
#         collection=mongo_collection,
#         df=ingredients_df,
#         extractor=extractor,
#         converter=converter,
#         confirm=False
#     )
#     print(result7)