from venv import logger
import httpx
import json
import re
import os
from logging import getLogger

logger = getLogger(__name__)

class ItineraryPlannerAgent:
    def __init__(self, gemini_api_key):
        """
        Initializes the agent with the Gemini API Key.
        """
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required.")
        self.api_key = gemini_api_key
        
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={self.api_key}"
        logger.info("Initialized new ItineraryPlannerAgent (async httpx, Gemini).")

    def _clean_json_response(self, text):
        """
        Helper function to strip markdown and other text from a JSON response.
        """
        
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        
        text = text.strip().lstrip("```json").rstrip("```")
        return text

    async def create_itinerary(self, client, destination, hotel, duration):
        """
        Generates the itinerary asynchronously using httpx.
        The 'client' (httpx.AsyncClient) is passed in from main.py.
        """
        print(f"Generating {duration}-day itinerary for {destination}...")
        
        prompt = f"""
        You are an expert travel planner. Generate a travel plan for the following request.

        Destination: {destination}
        Duration: {duration} days
        Hotel: {hotel['name']}
        
        ---
        RULES FOR YOUR RESPONSE:
        1.  Your ENTIRE response must be a single, valid JSON object.
        2.  Do NOT include any text before or after the JSON object.
        3.  The JSON must have two keys: "itinerary_text" and "locations".
        4.  "itinerary_text": A string of the full itinerary in Markdown.
        5.  "locations": A list of objects. Each 'name' MUST be a geocodable name
            (e.g., "Gateway of India, Mumbai, India").
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        }
        
        raw_response_text = None
        try:
            
            response = await client.post(self.gemini_url, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            
            if "candidates" not in data:
                logger.error("Error: Gemini response was empty or blocked.")
                logger.debug(f"Full Response: {data}")
                
                return {"itinerary_text": "Error: The AI's response was blocked or empty.", "locations": []}
                
            raw_response_text = data['candidates'][0]['content']['parts'][0]['text']
            
            return json.loads(raw_response_text)

        except json.JSONDecodeError:
            logger.error("Error: Failed to decode JSON from Gemini response.")
            logger.debug(f"--- The bad response from Gemini was: ---\n{raw_response_text}\n------------------------------------------")
            cleaned_text = self._clean_json_response(raw_response_text)
            try:
                # Try parsing the cleaned text
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                logger.error("Error: Still could not parse cleaned JSON.")
                return {"itinerary_text": "Error: The AI returned an invalid itinerary format.", "locations": []}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API HTTP Error: {e.response.text}")
            return {"itinerary_text": f"Error: Gemini API request failed: {e.response.text}", "locations": []}
        except Exception as e:
            logger.error(f"Error in ItineraryAgent ({type(e)}): {e}")
            return {"itinerary_text": f"Error: {e}", "locations": []}

