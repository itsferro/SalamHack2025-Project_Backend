from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os

app = FastAPI()

# Set your OpenAI API key as an environment variable.
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define the data model for the recipe request.
class RecipeRequest(BaseModel):
    meal_type: str
    cuisine_type: str
    ingredients: str
    servings: int
    dietary_restrictions: str
    allergies: str
    nutritional_preferences: str

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

@app.post("/generate_recipe")
async def generate_recipe(recipe_request: RecipeRequest):
    # Build the prompt by formatting the template with the user inputs.
    prompt = PREMADE_PROMPT_TEMPLATE.format(
        meal_type=recipe_request.meal_type,
        cuisine_type=recipe_request.cuisine_type,
        ingredients=recipe_request.ingredients,
        servings=recipe_request.servings,
        dietary_restrictions=recipe_request.dietary_restrictions,
        allergies=recipe_request.allergies,
        nutritional_preferences=recipe_request.nutritional_preferences
    )

    try:
        # Send the prompt to ChatGPT API using the "ChatGPT 4o" model.
        response = openai.ChatCompletion.create(
            model="ChatGPT 4o",  # Using the requested model.
            messages=[{"role": "user", "content": prompt}]
        )
        # Extract the response text.
        response_text = response['choices'][0]['message']['content']

        # Retrieve token usage details.
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        # Calculate the cost.
        # Hypothetical pricing: $0.03 per 1K prompt tokens and $0.06 per 1K completion tokens.
        cost = (prompt_tokens * 0.03 / 1000) + (completion_tokens * 0.06 / 1000)

        # Print the cost to STDOUT.
        print(f"Operation cost: ${cost:.4f} "
              f"(Prompt tokens: {prompt_tokens}, Completion tokens: {completion_tokens})")

        return {"response": response_text}
    except Exception as e:
        # Return an HTTP error if the API call fails.
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
