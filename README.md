# AI Travel Planner

This is an intelligent travel planning application built with Streamlit and a multi-agent RAG (Retrieval-Augmented Generation) pipeline. This tool generates personalized, multi-day travel itineraries for destinations in India, recommends real hotels from a database, and visualizes the entire plan on an interactive 3D map.

## Features

* **AI-Powered Itinerary:** Generates detailed, day-by-day travel plans using the Google Gemini API.
* **RAG-Powered Hotel Recommendations:** Uses a persistent ChromaDB vector database to perform semantic search on a real dataset of 8,000+ Indian hotels.
* **Dynamic Filtering:** Recommends hotels based on both user preferences (e.g., "luxury with a spa") and the chosen destination city.
* **Interactive 3D Map:** Geocodes all itinerary locations and displays them as colorful, daily waypoints on a `pydeck` map.
* **Custom Map Styles:** Includes a theme switcher for MapTiler (Streets, Satellite, Dark, etc.) powered by a `MapTiler` API key.

## Architecture

This project is built on a multi-agent architecture where different components handle specific tasks:

* **Frontend:** `streamlit` is used for the user interface and interactivity.

* **Generative AI:** `google-genai` (Gemini Pro) is used by the `ItineraryPlannerAgent` to generate structured JSON-based itineraries. This agent's generation is "grounded" by the context provided from the retrieval agents.

* **Retrieval (RAG):**
    * `hotel_agent.py`: The primary RAG agent. It uses `sentence-transformers` to find semantically relevant hotels for a user's query.
    * `chromadb`: The persistent vector database used to store and efficiently query hotel data embeddings. It filters queries by `destination_city` to ensure relevance.

* **Data & Geocoding:**
    * `hotel_details.csv`: The raw data source of Indian hotels.
    * `geopy`: Used to geocode location names from the itinerary into coordinates. This process is parallelized using `concurrent.futures.ThreadPoolExecutor` for speed.
    * `pydeck`: Renders the interactive 3D map in Streamlit.
    * `MapTiler`: Provides the map basemap tiles.

## Getting Started

### 1. Prerequisites

* Python 3.9+
* A Google Gemini API Key
* A MapTiler API Key 

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

```text
streamlit
pandas
numpy
python-dotenv
google-genai
pydeck
geopy
sentence-transformers
chromadb
```

### 4. API Keys 
Create a file named `.env`. Inside this file, the following API Keys must be present.
```GEMINI_API_KEY="your-google-gemini-api-key"
MAPTILER_API_KEY="your-maptiler-api-key"
```
The application code (main.py) is already set up to read these keys using  `load_env()` from `python-dotenv`.


### 5. Hotel Database Setup (ChromaDB)
This project relies on a CSV file of Indian hotel data to build its vector database downloaded from the dataset:Go to: https://www.kaggle.com/datasets/aakashshinde1507/hotels-in-indiaDownload ,  the hotel_details.csv file.

First Run (Database Ingestion):The first time you run the app, the hotel_agent will:
a. Read hotel_details.csv.
b. Process and clean the 9,000+ entries.
c. Ingest them into a new ChromaDB database in batches.
d. Create a persistent database in a new folder named ./chroma_db.

This initial process will be slow (it may take 1-2 minutes). Every subsequent run will be fast, as the agent will load the data directly from the persistent chroma_db.

### 6. Running the Application
Once all the steps above are complete, run the Streamlit app from your terminal:
`streamlit run main.py`
