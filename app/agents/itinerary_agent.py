import json
from google import genai
from google.genai.errors import APIError

class ItineraryPlannerAgent:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        
    def create_itinerary(self, destination, best_month, hotel, duration):
        
        prompt = f"""
        You are an expert travel planner. Generate a travel plan for the following request.
        
        Destination: {destination}
        Month: {best_month}
        Duration: {duration} days
        Hotel: {hotel['name']}
        
        ---
        RULES FOR YOUR RESPONSE:
        1.  Your ENTIRE response must be a single, valid JSON object.
        2.  Do NOT include any text before or after the JSON object.
        3.  The JSON must have two keys: "itinerary_text" and "locations".
        4.  "itinerary_text": A string of the full itinerary in Markdown. Descriptions must be **brief (1-2 sentences)**.
        5.  "locations": A list of objects. Each object must have "day" (int), "name" (string), and "description" (string).
        
         IMPORTANT RULE FOR 'name' :
        The 'name' value MUST be geocodable. Format it as 'Landmark Name, City, Country'.
        Use the user's destination as the city. For example, if the destination is 'Mumbai', a location name should be 'Gateway of India, Mumbai, India'.
        
        EXAMPLE JSON OUTPUT:
        {{
          "itinerary_text": "## Day 1\n* (9:00 AM) --> Morning: Visit the Gateway of India. A brief tour.\n* (1:00 PM) Lunch: Eat at 'Leopold Cafe'.",
          "locations": [
            {{"day": 1, "name": "Gateway of India, Mumbai, India", "description": "Morning tour"}},
            {{"day": 1, "name": "Leopold Cafe, Mumbai, India", "description": "Lunch"}}
          ]
        }}
        ---
        
        Now, generate the JSON for the user's request.
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[prompt],
                config={
                    "max_output_tokens": 4096,
                    "response_mime_type": "application/json"
                }
            )
            return json.loads(response.text)

        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from Gemini response.")
            return {"itinerary_text": "Error: Could not parse the itinerary.", "locations": []}
        except Exception as e:
            print(f"Error in ItineraryAgent: {e}")
            return {"itinerary_text": f"Error: {e}", "locations": []}