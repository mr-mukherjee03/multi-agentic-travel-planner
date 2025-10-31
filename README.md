# AI Travel Planner

This is an intelligent travel planning application built with Streamlit and a multi-agent RAG (Retrieval-Augmented Generation) pipeline. This tool generates personalized, multi-day travel itineraries for destinations in India, recommends real hotels from a database, and visualizes the entire plan on an interactive 3D map.

## Features

* **AI-Powered Itinerary:** Generates detailed, day-by-day travel plans using the `Google Gemini API`.
* **RAG-Powered Hotel Recommendations:** Uses a persistent ChromaDB vector database to perform semantic search on a real dataset of 9,000+ Indian hotels.
* **Dynamic Filtering:** Recommends hotels based on both user preferences (e.g., "luxury with a spa") and the chosen destination city.
* **Async-First:** Uses asyncio and httpx to run all major network calls (Geocoding, Hotel Search, Itinerary Generation, Weather) in parallel for a fast user experience.
* **Live Weather Forecast:** Fetches a 7-day forecast from `Open-Meteo` and displays it in a custom, clean HTML/CSS widget.
* **Interactive 3D Map:** Uses the `Google Maps Platform` to render 3D map tiles, custom-colored markers for each day, and route polylines connecting the waypoints.

## Architecture

This project is built on a multi-agent architecture where different components handle specific tasks:

* **Frontend:** `streamlit` is used for the user interface and interactivity.

* **Generative AI:** `google-genai` (Gemini 2.5 Pro) is used by the `ItineraryPlannerAgent` to generate structured JSON-based itineraries. This agent's generation is "grounded" by the context provided from the retrieval agents.

* **Retrieval (RAG):**
    * `hotel_agent.py`: The primary RAG agent. It uses `sentence-transformers` to find semantically relevant hotels for a user's query.
    * `chromadb`: The persistent vector database used to store and efficiently query hotel data embeddings. It filters queries by `destination_city` to ensure relevance.

* **Data & Geocoding:**
    * `hotel_details.csv`: The raw data source of Indian hotels.
    * `geopy`: Used to geocode location names from the itinerary into coordinates. This process is parallelized using `concurrent.futures.ThreadPoolExecutor` for speed.
    * `Google Maps`: Provides the map basemap tiles.

## Getting Started

### 1. Prerequisites

* Python 3.9+
* A Google Gemini API Key
* A Google Maps API Key & a map ID


### 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/mr-mukherjee03/multi-agentic-travel-planner.git)
    cd multi-agentic-travel-planner
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

### 3. `requirements.txt`

Your `requirements.txt` file should contain the following:

```
streamlit
pandas
numpy
python-dotenv
google-genai
sentence-transformers
chromadb
```

### 4. API Keys 
Create a file named `.env`. Inside this file, the following API Keys must be present. <br>
```
GEMINI_API_KEY="your-google-gemini-api-key"
GOOGLE_MAP_API_KEY="your-google-maps-api-key"
MAP_ID = "your-created-google-map-id"
```
The application code (main.py) is already set up to read these keys using  `load_env()` from `python-dotenv`.


### 5. Hotel Database Setup (ChromaDB)
This project relies on a CSV file of Indian hotel data to build its vector database downloaded from the dataset: https://www.kaggle.com/datasets/aakashshinde1507/hotels-in-indiaDownload ,  the hotel_details.csv file.

First Run (Database Ingestion):The first time you run the app, the hotel_agent will:<br>
a. Read hotel_details.csv. <br>
b. Process and clean the 9,000+ entries. <br>
c. Ingest them into a new ChromaDB database in batches. <br>
d. Create a persistent database in a new folder named ./chroma_db.<br>

This initial process will be slow (it may take 1-2 minutes). Every subsequent run will be fast, as the agent will load the data directly from the persistent chroma_db.

### 6. Running the Application
Once all the steps above are complete, run the Streamlit app from your terminal:
`streamlit run main.py`


