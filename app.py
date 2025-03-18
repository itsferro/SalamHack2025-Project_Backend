import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os


load_dotenv()


client = OpenAI(os.getenv("API_KEY"))

app = FastAPI()

def parse_api_response(raw_response: str):
    # Remove the "json" prefix if it exists
    if raw_response.startswith("json"):
        raw_response = raw_response[len("json"):].strip()
    
    try:
        # Try parsing directly
        return json.loads(raw_response)
    except json.JSONDecodeError:
        # Handle escaped characters if necessary
        try:
            cleaned = raw_response.encode('utf-8').decode('unicode_escape')
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

# Define the data model for the recipe request.
class RecipeRequest(BaseModel):
    meal_type: str
    cuisine_type: str
    ingredients_available: str
    ingredients_to_avoid: str
    servings: int
    dietary_restrictions: str
    allergies: str
    nutritional_preferences: str
"""
# Pre-made prompt template with placeholders for the inputs.
PREMADE_PROMPT_TEMPLATE = (
    "I need a recipe suggestion based on the following details:\n"
    "- Meal Type: {meal_type}\n"
    "- Cuisine Type: {cuisine_type}\n"
    "- Ingredients Available: {ingredients}\n"
    "- Servings: {servings}\n"
    "- Dietary Restrictions: {dietary_restrictions}\n"
    "- Allergies: {allergies}\n"
    "- Nutritional Preferences: {nutritional_preferences}\n"
)
"""

def generate_recipes(
        meal_type=None,
        cuisine_type=None,
        ingredients_available=None,
        ingredients_to_avoid=None,
        servings=None,
        dietary_restrictions=None, 
        allergies=None,
        nutritional_preferences=None,
        num_meals=1
        ) -> None:
    
    # Convert list parameters to strings if needed
    if isinstance(ingredients_available, list):
        ingredients_available = ", ".join(ingredients_available)
    if isinstance(ingredients_to_avoid, list):
        ingredients_to_avoid = ", ".join(ingredients_to_avoid)
    if isinstance(dietary_restrictions, list):
        dietary_restrictions = ", ".join(dietary_restrictions)
    if isinstance(allergies, list):
        allergies = ", ".join(allergies)
    if isinstance(nutritional_preferences, list):
        nutritional_preferences = ", ".join(nutritional_preferences)
    
    # Define dietary restrictions dictionary
    dietary_definitions = {
        "halal": "Halal: No pork or pork products, no alcohol or ingredients containing alcohol, meat must be from animals slaughtered according to Islamic law. Ingredients like gelatin, rennet, and certain food additives must be from halal sources.",
        "kosher": "Kosher: Follows Jewish dietary laws including separation of meat and dairy, no pork, no shellfish, and meat from animals slaughtered according to Jewish law.",
        "vegetarian": "Vegetarian: No meat, poultry, or seafood. May include eggs and dairy.",
        "vegan": "Vegan: No animal products whatsoever, including meat, dairy, eggs, honey, and other animal-derived ingredients.",
        "gluten-free": "Gluten-Free: No wheat, barley, rye, or other gluten-containing grains.",
        "dairy-free": "Dairy-Free: No milk, cheese, butter, or other dairy products.",
        "keto": "Keto: Very low carbohydrate, high fat diet. Avoid grains, sugar, most fruits, and starchy vegetables.",
        "paleo": "Paleo: Foods that could be obtained by hunting and gathering - meats, fish, nuts, seeds, fruits, vegetables. No dairy, grains, processed foods.",
        "low-carb": "Low-Carb: Reduced intake of carbohydrates, particularly from grains, starchy vegetables, and sugar."
    }
    
    # Build custom dietary definitions section based on user selections
    custom_definitions = []
    if dietary_restrictions:
        restrictions_list = [r.strip().lower() for r in dietary_restrictions.split(',')]
        for restriction in restrictions_list:
            if restriction in dietary_definitions:
                custom_definitions.append(dietary_definitions[restriction])
    
    dietary_section = ""
    if custom_definitions:
        dietary_section = "Dietary Definitions:\n- " + "\n- ".join(custom_definitions)
    
    # Customize rule blocks based on what's provided
    ingredient_rules = ""
    if ingredients_available and not ingredients_to_avoid:
        ingredient_rules = "a. Generate meals using primarily the available ingredients."
    elif ingredients_to_avoid and not ingredients_available:
        ingredient_rules = "b. Generate appropriate meals that don't use the avoided ingredients."
    elif ingredients_available and ingredients_to_avoid:
        ingredient_rules = "c. Generate meals using primarily the available ingredients while avoiding the specified ingredients to avoid."
    else:
        ingredient_rules = "d. Generate appropriate meals based on the other criteria."
    
    # Base prompt template
    prompt = f"""
You are a meal generator that creates detailed meal cards. Your output MUST be a valid JSON array of meal objects with the following structure:

[
  {{
    "meal_name": "",
    "original_language_name": "",
    "country_origin": "",
    "country_flag": "",
    "prep_time_minutes": 0,
    "cook_time_minutes": 0,
    "servings": 0,
    "nutritional_information": {{
      "calories_per_serving": 0,
      "protein_g": 0,
      "carbs_g": 0,
      "fat_g": 0,
      "fiber_g": 0,
      "sugar_g": 0,
      "other": ""
    }},
    "ingredients": [
      {{
        "name": "",
        "quantity": "",
        "unit": "",
        "note": ""
      }}
    ],
    "instructions": [
      ""
    ],
    "extra_ingredients_count": 0,
    "difficulty_level": "",
    "tips": [
      ""
    ],
    "tags": [""]
  }}
]

User Input:
- Meal Type: {meal_type or ""}
- Cuisine Type: {cuisine_type or ""}
- Ingredients Available: {ingredients_available or ""} 
- Ingredients to Avoid: {ingredients_to_avoid or ""}
- Servings: {servings or ""}
- Dietary Restrictions: {dietary_restrictions or ""}
- Allergies: {allergies or ""}
- Nutritional Preferences: {nutritional_preferences or ""}

{dietary_section}

Rules:
1. Generate up to {num_meals} different meal options that meet the criteria. If you cannot create that many unique and appropriate meals, provide as many as possible.
1. The recipe must strictly adhere to all dietary restrictions specified by the user.
2. The recipe should fully respect the user's allergies and nutritional preferences.
3. Handle ingredient specifications as follows:
   {ingredient_rules}
"""

    # Add conditional rules based on what was provided
    if ingredients_available:
        prompt += """
4. For each meal, count how many ingredients are NOT in the user's "Ingredients Available" list and store this number in "extra_ingredients_count".
5. Sort the meal array by "extra_ingredients_count" in ascending order (meals with fewer extra ingredients should appear first).
6. For any ingredient not in the user's "Ingredients Available" list, add a note field with text: "This ingredient was not in your original list."
"""
    else:
        prompt += """
4. Set "extra_ingredients_count" to 0 for all recipes.
"""

    # Add common rules for all scenarios
    prompt += """
7. Search for well-known meals that match the criteria. If a well-known meal exists, use its recognized name; otherwise, generate a new, creative meal name.
8. Ensure that the step-by-step instructions are clear and easy to follow.
9. Include useful cooking tips specific to the recipe.
10. Add relevant tags like "quick," "budget-friendly," or "one-pot" to categorize the meal.
11. For the "country_origin" field, provide the specific country or region within the country (e.g., "Lebanon (South)" or "Northern Italy").
12. For the "original_language_name" field, provide the meal name in the original language of its country of origin.
13. For the "country_flag" field, provide an appropriate emoji flag representing the country of origin.
14. Only return the JSON array—no additional text or explanations.

Output ONLY the completed JSON array without any additional text, prefixes, or labels. The response should start directly with the JSON array, like this: []. Do not include the word "json" or any other string before the array.
"""
    return prompt


@app.get("/")
def root():
    return {
        "message": "the API is running ..."
    }


@app.post("/generate_recipe")
async def generate_recipe(recipe_request: RecipeRequest):
    # Build the prompt by formatting the template with the user inputs.
    prompt = generate_recipes(
        meal_type=recipe_request.meal_type,
        cuisine_type=recipe_request.cuisine_type,
        ingredients_available=recipe_request.ingredients_available,
        ingredients_to_avoid=recipe_request.ingredients_to_avoid,
        servings=recipe_request.servings,
        dietary_restrictions=recipe_request.dietary_restrictions, 
        allergies=recipe_request.allergies,
        nutritional_preferences=recipe_request.nutritional_preferences
        )
    """
    prompt = PREMADE_PROMPT_TEMPLATE.format(
        meal_type=recipe_request.meal_type,
        cuisine_type=recipe_request.cuisine_type,
        ingredients=recipe_request.ingredients,
        servings=recipe_request.servings,
        dietary_restrictions=recipe_request.dietary_restrictions,
        allergies=recipe_request.allergies,
        nutritional_preferences=recipe_request.nutritional_preferences
    )"""

    try:
        # Send the prompt to ChatGPT API using the "ChatGPT 4o" model.
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
            )
        # Extract the response text.
        response_text = response.choices[0].message.content
        print(response_text)
        recipe_in_json = parse_api_response(response_text)

        
        # Retrieve token usage details.
        usage = response.usage

        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens

        # Calculate the cost.
        # Hypothetical pricing: $0.03 per 1K prompt tokens and $0.06 per 1K completion tokens.
        cost = (prompt_tokens * 1.10  / 1000000) + (completion_tokens * 4.40 / 1000000)

        # Print the cost to STDOUT.
        print(f"Operation cost: ${cost:.4f} "
              f"(Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens})")
        
        return {"response": recipe_in_json}
    except Exception as e:
        # Return an HTTP error if the API call fails.
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
