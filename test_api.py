# # import pytest
# # from fastapi.testclient import TestClient
# # from mongomock import MongoClient as MockMongoClient
# # import app
# # from unittest.mock import patch

# # client = TestClient(app.app)

# # # Replace actual DB client with mock one
# # app.mongodb_client = MockMongoClient()
# # db = app.mongodb_client["test_baking_ai"]
# # collection = db["ingredients"]

# # @pytest.fixture(autouse=True)
# # def reset_cache_and_db():
# #     """
# #     Resets the cached ingredient names and mock MongoDB collection
# #     before each test to ensure test isolation and fresh state.
# #     """
# #     from app import cached_ingredient_names
# #     globals()["cached_ingredient_names"] = None

# #     collection.delete_many({})
# #     collection.insert_many([
# #         {"name": "coconut flour", "type": "Solid"},
# #         {"name": "almond milk", "type": "Liquid"}
# #     ])

# # @pytest.mark.parametrize("recipe_text, expected_in_msg, expected_type", [
# #     ("2 cups of coconut flour", "weighs approximately", "Solid"),
# #     ("1 cup of almond milk", "is approximately", "Liquid")
# # ])
# # def test_successful_conversion_returns_correct_message(recipe_text, expected_in_msg, expected_type):
# #     """
# #     Verifies that known ingredients return a success message indicating
# #     approximate weight or volume with confirmation.
# #     """
# #     response = client.post("/convert/", json={"recipe_text": recipe_text})
# #     assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
# #     data = response.json()
# #     assert data["confirm_conversion"] is True, "Expected conversion to be confirmed"
# #     assert expected_in_msg in data["message"], f"Expected '{expected_in_msg}' in message"
# #     assert any(unit in data["message"] for unit in ["grams", "milliliters"]), "Expected units in response"

# # def test_fuzzy_match_suggestion_for_typo():
# #     """
# #     Tests that the API suggests a corrected ingredient name when the user input
# #     contains a typo and confirms the suggestion without conversion.
# #     """
# #     response = client.post("/convert/", json={"recipe_text": "2 cups of coconot flour"})
# #     assert response.status_code == 200

# #     data = response.json()
# #     assert data["confirm_conversion"] is False, "Expected suggestion instead of conversion"
# #     assert "Did you mean 'coconut flour'?" in data["message"]
# #     assert data["suggestion"] == "coconut flour"

# # def test_invalid_ingredient_when_conversion_fails():
# #     """
# #     Tests that when 'convert_to_grams' fails (returns None),
# #     the API returns the 'Could not convert the ingredient.' message
# #     and confirms the conversion status for consistency.
# #     """
# #     with patch("main.convert_to_grams", return_value=None):
# #         response = client.post("/convert/", json={"recipe_text": "3 cups of unknown_ingredient"})
# #         assert response.status_code == 200

# #         data = response.json()
# #         assert data["confirm_conversion"] is True
# #         assert data["message"] == "Could not convert the ingredient."

# import pytest
# from fastapi.testclient import TestClient
# from unittest.mock import patch
# from main import app

# client = TestClient(app)


# def test_valid_conversion():
#     """
#     Tests that the API correctly converts a valid ingredient to grams.
#     """
#     response = client.post("/convert/", json={"recipe_text": "2 cups of sugar"})
#     assert response.status_code == 200
#     data = response.json()
#     assert data["confirm_conversion"] is True
#     assert "weighs approximately" in data["message"]


# # def test_fuzzy_match_suggestion_for_typo():
# #     response = client.post("/convert/", json={"recipe_text": "2 cups of coconot flour"})
# #     assert response.status_code == 200
# #     data = response.json()
# #     assert data["confirm_conversion"] is False
# #     assert "suggestion" in data
# #     assert "Did you mean" in data["message"]


# def test_suggestion_returned_for_typo():
#     response = client.post("/convert/", json={"recipe_text": "2 cups of coconot flour"})
#     data = response.json()
#     assert data["confirm_conversion"] is False
#     assert "Did you mean" in data["message"]

# def test_conversion_after_confirmation():
#     response = client.post("/convert/", json={
#         "recipe_text": "2 cups of coconot flour",
#         "confirm": True,
#         "confirmed_ingredient": "coconut flour"
#     })
#     data = response.json()
#     assert data["confirm_conversion"] is True
#     assert "weighs approximately" in data["message"]

# def test_invalid_ingredient_when_conversion_fails():
#     """
#     Tests that when conversion fails, the API returns an appropriate failure message.
#     """
#     with patch("main.convert_to_grams", return_value=None):
#         response = client.post("/convert/", json={"recipe_text": "3 cups of unknowningredient"})
#         assert response.status_code == 200
#         data = response.json()
#         assert data["confirm_conversion"] is True
#         assert data["message"] == "Could not convert the ingredient."

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd

# Import the main FastAPI app instance
from app_updated import app

# Create a TestClient instance to test your FastAPI app
client = TestClient(app)

# --- Mock Data ---
# This data simulates what would be in your MongoDB collection
MOCK_DB_INGREDIENTS = [
    {"_id": "id1", "name": "coconut flour", "type": "solid", "grams_per_cup": 120.0, "density_g_per_ml": 0.5, "category": "Flour"},
    {"_id": "id2", "name": "almond milk", "type": "liquid", "grams_per_cup": 240.0, "density_g_per_ml": 0.98, "category": "Liquid"},
    {"_id": "id3", "name": "sugar", "type": "solid", "grams_per_cup": 200.0, "density_g_per_ml": 0.85, "category": "Sweetener"},
    {"_id": "id4", "name": "salt", "type": "solid", "grams_per_cup": 280.0, "density_g_per_ml": 1.2, "category": "Spice"},
    # Add some data for the 'fruit' category for prediction test
    {"_id": "id5", "name": "apple", "type": "solid", "grams_per_cup": 110.0, "density_g_per_ml": 0.46, "category": "fruit"},
    {"_id": "id6", "name": "banana", "type": "solid", "grams_per_cup": 150.0, "density_g_per_ml": 0.63, "category": "fruit"},
]

# --- Fixtures for Mocking Dependencies ---

@pytest.fixture(autouse=True)
def mock_dependencies():
    """
    This fixture runs before every test and mocks key external dependencies.
    It replaces real MongoDB calls and NLP/ML functions with controlled mock objects.
    """
    # 1. Mock MongoDB Collection and DataFrame
    mock_collection = MagicMock()
    # Configure what mock_collection.find() returns
    mock_collection.find.return_value = (item for item in MOCK_DB_INGREDIENTS)
    mock_collection.insert_one.return_value = None # Mocking insert_one

    mock_df = pd.DataFrame(MOCK_DB_INGREDIENTS)
    mock_df['name'] = mock_df['name'].str.lower() # Ensure consistency with app's DataFrame prep

    # Use patch to replace the actual functions in the database module
    with patch('database.get_mongo_collection', return_value=mock_collection), \
         patch('database.get_ingredients_dataframe', return_value=mock_df), \
         patch('database.load_ingredients_dataframe', return_value=mock_df): # Mock reloading too

        # 2. Mock Core NLP Functions from main.py
        # We'll control what `extract_measurements` returns for each test
        with patch('main_update.text_preprocessing', side_effect=lambda x: x.lower()), \
             patch('main_update.extract_measurements') as mock_extract_measurements:

            # 3. Mock ML Prediction and DB Addition Functions
            with patch('predict_missing_densities_updated.predict_densities') as mock_predict_densities, \
                 patch('predict_missing_densities_updated.add_prediction_to_db') as mock_add_prediction_to_db, \
                 patch('predict_category_update.get_ingredient_category') as mock_get_ingredient_category:

                # Yield control to the test function, passing the mocked objects
                yield mock_extract_measurements, mock_predict_densities, \
                      mock_add_prediction_to_db, mock_get_ingredient_category, mock_collection

# --- Helper Function for Mocks ---

def setup_extract_measurements_mock(mock_obj, quantity, unit, ingredient):
    """Convenience function to configure the mock for extract_measurements."""
    mock_obj.return_value = (quantity, unit, ingredient)

# --- Test Cases ---

def test_valid_conversion_solid(mock_dependencies):
    """Tests a valid conversion for a solid ingredient."""
    mock_extract_measurements, _, _, _, _ = mock_dependencies
    setup_extract_measurements_mock(mock_extract_measurements, 2.0, "cup", "sugar")

    response = client.post("/convert/", json={"recipe_text": "2 cups of sugar"})
    assert response.status_code == 200
    data = response.json()
    assert data["confirm_conversion"] is True
    # 2 cups * 200 g/cup (from MOCK_DB_INGREDIENTS)
    assert "weighs approximately 400.00 grams." in data["message"]

def test_valid_conversion_liquid(mock_dependencies):
    """Tests a valid conversion for a liquid ingredient."""
    mock_extract_measurements, _, _, _, _ = mock_dependencies
    setup_extract_measurements_mock(mock_extract_measurements, 1.0, "cup", "almond milk")

    response = client.post("/convert/", json={"recipe_text": "1 cup of almond milk"})
    assert response.status_code == 200
    data = response.json()
    assert data["confirm_conversion"] is True
    # 1 cup * 240 g/cup (standard liquid conversion in main.py)
    assert "weighs approximately 240.00 grams." in data["message"]

def test_fuzzy_match_suggestion_for_typo(mock_dependencies):
    """
    Tests that a typo triggers a fuzzy match suggestion and prompts for confirmation.
    """
    mock_extract_measurements, _, _, _, _ = mock_dependencies
    # Simulate extracting a misspelled ingredient
    setup_extract_measurements_mock(mock_extract_measurements, 2.0, "cup", "coconot flour")

    response = client.post("/convert/", json={"recipe_text": "2 cups of coconot flour"})
    assert response.status_code == 200
    data = response.json()
    assert data["confirm_conversion"] is False
    assert "Did you mean 'coconut flour'?" in data["message"]
    assert data["suggested_ingredient"] == "coconut flour"

def test_conversion_after_confirmation(mock_dependencies):
    """
    Tests that conversion proceeds when a suggested ingredient is explicitly confirmed.
    """
    mock_extract_measurements, _, _, _, _ = mock_dependencies
    # Simulate extracting the original typo, but the API receives a confirmed ingredient
    setup_extract_measurements_mock(mock_extract_measurements, 2.0, "cup", "coconot flour")

    response = client.post("/convert/", json={
        "recipe_text": "2 cups of coconot flour",
        "confirm": True, # User confirms
        "confirmed_ingredient": "coconut flour" # This is the corrected name
    })
    data = response.json()
    assert response.status_code == 200
    assert data["confirm_conversion"] is True
    # 2 cups * 120 g/cup for coconut flour (from MOCK_DB_INGREDIENTS)
    assert "weighs approximately 240.00 grams." in data["message"]

def test_unknown_ingredient_triggers_prediction_on_confirm(mock_dependencies):
    """
    Tests the full flow for a new ingredient: not found in DB -> prediction triggered ->
    added to (mock) DB -> conversion.
    """
    mock_extract_measurements, mock_predict_densities, mock_add_prediction_to_db, \
    mock_get_ingredient_category, mock_collection = mock_dependencies

    # Simulate extraction of a brand new, unknown ingredient
    setup_extract_measurements_mock(mock_extract_measurements, 1.0, "cup", "acai berry")

    # Mock the ML prediction functions:
    mock_get_ingredient_category.return_value = "fruit"
    # Predict density and grams_per_cup based on average of 'apple' and 'banana' from MOCK_DB_INGREDIENTS
    # Avg grams_per_cup = (110+150)/2 = 130.0
    # Avg density_g_per_ml = (0.46+0.63)/2 = 0.545
    mock_predict_densities.return_value = ("acai berry", 0.545, 130.0, "fruit", "solid")
    mock_add_prediction_to_db.return_value = None # No specific return needed

    response = client.post("/convert/", json={
        "recipe_text": "1 cup of acai berry",
        "confirm": True # Crucial: user confirms they want to proceed with prediction
    })
    data = response.json()

    assert response.status_code == 200
    assert data["confirm_conversion"] is True
    assert "weighs approximately 130.00 grams." in data["message"] # Based on predicted grams/cup
    
    # Verify that the prediction functions were called as expected
    mock_predict_densities.assert_called_once_with("acai berry")
    mock_add_prediction_to_db.assert_called_once_with("acai berry", 0.545, 130.0, "solid", "fruit", mock_collection)


def test_no_ingredient_extracted(mock_dependencies):
    """Tests the case where NLP cannot identify any ingredient, quantity, or unit."""
    mock_extract_measurements, _, _, _, _ = mock_dependencies
    # Simulate extraction failure
    setup_extract_measurements_mock(mock_extract_measurements, None, None, None)

    response = client.post("/convert/", json={"recipe_text": "just some random text here"})
    assert response.status_code == 200
    data = response.json()
    assert data["confirm_conversion"] is False
    assert "Could not identify ingredient, quantity, or unit. Please rephrase." in data["message"]

def test_conversion_fails_after_identification(mock_dependencies):
    """
    Tests when ingredient is identified but cannot be converted
    (e.g., unit doesn't match type, or prediction path not confirmed).
    """
    mock_extract_measurements, _, _, _, _ = mock_dependencies
    # Simulate extracting an ingredient and quantity/unit
    setup_extract_measurements_mock(mock_extract_measurements, 1.0, "gallon", "sugar") # Gallon is liquid unit for a solid
    
    response = client.post("/convert/", json={"recipe_text": "1 gallon of sugar"})
    assert response.status_code == 200
    data = response.json()
    assert data["confirm_conversion"] is True # It failed after identification, so it's a "confirm" state
    assert "Could not convert the ingredient. Ensure quantity and unit are clear or ingredient is known." in data["message"]

def test_prediction_service_fails(mock_dependencies):
    """Tests graceful handling when the prediction service itself throws an error."""
    mock_extract_measurements, mock_predict_densities, _, _, _ = mock_dependencies
    setup_extract_measurements_mock(mock_extract_measurements, 1.0, "cup", "problematic ingredient")
    
    # Make mock_predict_densities raise an exception to simulate failure
    mock_predict_densities.side_effect = Exception("Internal Prediction Service Error")

    response = client.post("/convert/", json={
        "recipe_text": "1 cup of problematic ingredient",
        "confirm": True # Trigger prediction
    })
    data = response.json()

    assert response.status_code == 200
    assert data["confirm_conversion"] is False
    assert "Could not predict properties for 'problematic ingredient'. Error: Internal Prediction Service Error" in data["message"]