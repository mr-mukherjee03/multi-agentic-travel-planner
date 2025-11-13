import streamlit as st
import pandas as pd
import os
import asyncio
import httpx
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from logging import getLogger

logger = getLogger(__name__)


from agents.hotel_agent import HotelRecommenderAgent
from agents.weather_agent import WeatherAnalysisAgent
from agents.itinerary_agent import ItineraryPlannerAgent

# SETUP & CONFIGURATION 
load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"

#API KEY & AGENT INITIALIZATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MAP_ID = os.getenv("MAP_ID")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEOCODE_MAPS_CO_API_KEY = os.getenv("GEOCODE_MAPS_CO_API_KEY")

try:
    hotel_agent = HotelRecommenderAgent()
    weather_agent = WeatherAnalysisAgent()
    itinerary_agent = ItineraryPlannerAgent(gemini_api_key=GEMINI_API_KEY)
    
except Exception as e:
    st.error(f"Error initializing agents: {e}")
    st.stop()

#HELPER FUNCTIONS ---

@st.cache_data(ttl=3600) 
def get_geocode(address):
    """
    Synchronously geocodes an address using geocode.maps.co. This function IS cacheable.
    """
    logger.info(f"Geocoding (Sync) with geocode.maps.co: {address}")
    
    if not GEOCODE_MAPS_CO_API_KEY:
        logger.error("Missing GEOCODE_MAPS_CO_API_KEY.")
        return None

    
    url = f"https://geocode.maps.co/search?q={address}&api_key={GEOCODE_MAPS_CO_API_KEY}"
    
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        
        if data and isinstance(data, list) and len(data) > 0:
            location = data[0]
            
            return {"lat": float(location['lat']), "lng": float(location['lon'])}
        else:
            logger.warning(f"Geocoding returned no results for: {address}")
            return None
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Geocoding HTTP Error: {e}")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        logger.error(f"Geocoding Parse Error: {e}")
    except Exception as e:
        logger.error(f"Geocoding Error: {e}")
    return None

def get_google_directions(waypoints_list):
    """
    Synchronously gets a route polyline.
    """
    logger.info("Fetching route (Sync)...")
    
    if len(waypoints_list) < 2:
        return None
    origin = f"{waypoints_list[0]['lat']},{waypoints_list[0]['lng']}"
    destination = f"{waypoints_list[-1]['lat']},{waypoints_list[-1]['lng']}"
    intermediate_waypoints = []
    if len(waypoints_list) > 2:
        for wp in waypoints_list[1:-1]:
            intermediate_waypoints.append(f"{wp['lat']},{wp['lng']}")
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&waypoints=optimize:true|{'|'.join(intermediate_waypoints)}&key={GOOGLE_MAPS_API_KEY}"
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'OK' and data['routes']:
            return data['routes'][0]['overview_polyline']['points']
        else:
            logger.warning("Directions API returned OK but no routes found.")
            return None
    except Exception as e:
        logger.error(f"Directions API Error: {e}")
    return None

def get_day_color(day):
    """
    Assigns a unique color to each day.
    """
    colors = ["#FF0000", "#0000FF", "#008000", "#FFFF00", "#00FFFF", "#FF00FF", "#FFA500"]
    return colors[(day - 1) % len(colors)]

#GOOGLE MAPS HTML/JS COMPONENT ---
def create_google_map_html(api_key, center_lat, center_lng, markers, route_polylines):
    """
    Generates the HTML/JS for the Google Map component.
    """
    marker_data = json.dumps(markers)
    polylines_data = json.dumps(route_polylines)
    

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Map</title>
        <style>
            #map {{ height: 500px; width: 100%; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            let map;
            const markersData = {marker_data};
            const polylinesData = {polylines_data};

            async function initMap() {{
                const {{ Map }} = await google.maps.importLibrary("maps");
                const {{ AdvancedMarkerView, PinElement }} = await google.maps.importLibrary("marker");
                
                map = new Map(document.getElementById("map"), {{
                    center: {{ lat: {center_lat}, lng: {center_lng} }},
                    zoom: 12,
                    mapId: "{MAP_ID}",
                    tilt: 45 
                }});

                markersData.forEach(marker => {{
                    const markerPin = new PinElement({{
                        background: marker.color,
                        borderColor: "#000",
                        glyphColor: "#000",
                    }});
                    const advMarker = new AdvancedMarkerView({{
                        map: map,
                        position: {{ lat: marker.lat, lng: marker.lng }},
                        title: `Day ${{marker.day}}: ${{marker.name}}`,
                        content: markerPin.element,
                    }});
                }});

                polylinesData.forEach(route => {{
                    if (route.polyline) {{
                        const decodedPath = google.maps.geometry.encoding.decodePath(route.polyline);
                        const routeLine = new google.maps.Polyline({{
                            path: decodedPath,
                            geodesic: true,
                            strokeColor: route.color,
                            strokeOpacity: 0.8,
                            strokeWeight: 5,
                        }});
                        routeLine.setMap(map);
                    }}
                }});
            }}
        </script>
        <script async
            src="https://maps.googleapis.com/maps/api/js?key={api_key}&v=beta&libraries=maps,marker,geometry&callback=initMap">
        </script>
    </body>
    </html>
    """

# CUSTOM WEATHER WIDGET FUNCTIONS 

# WMO Weather interpretation codes
WEATHER_CODES = {
    0: ("☀️", "Clear sky"),
    1: ("🌤️", "Mainly clear"),
    2: ("🌥️", "Partly cloudy"),
    3: ("☁️", "Overcast"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Depositing rime fog"),
    51: ("🌧️", "Light drizzle"),
    53: ("🌧️", "Moderate drizzle"),
    55: ("🌧️", "Dense drizzle"),
    56: ("🌧️", "Light freezing drizzle"),
    57: ("🌧️", "Dense freezing drizzle"),
    61: ("🌧️", "Slight rain"),
    63: ("🌧️", "Moderate rain"),
    65: ("🌧️", "Heavy rain"),
    66: ("🌧️", "Light freezing rain"),
    67: ("🌧️", "Heavy freezing rain"),
    71: ("❄️", "Slight snow fall"),
    73: ("❄️", "Moderate snow fall"),
    75: ("❄️", "Heavy snow fall"),
    77: ("❄️", "Snow grains"),
    80: ("🌧️", "Slight rain showers"),
    81: ("🌧️", "Moderate rain showers"),
    82: ("🌧️", "Violent rain showers"),
    85: ("❄️", "Slight snow showers"),
    86: ("❄️", "Heavy snow showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm (hail)"),
    99: ("⛈️", "Thunderstorm (hail)"),
}

def get_weather_display(weather_code):
    """
    Maps Open-Meteo weather codes to an icon and a caption.
    """
    return WEATHER_CODES.get(weather_code, ("☁️", "Cloudy"))

def create_weather_widget_html(df):
    """
    Generates custom HTML/CSS for the weather forecast.
    """
    if df.empty:
        return "<p>Could not retrieve weather forecast.</p>"

    html = """
    <style>
        .weather-widget-container {
            display: flex;
            flex-direction: row;
            overflow-x: auto;
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 10px;
            -webkit-overflow-scrolling: touch; /* Smooth scrolling on mobile */
        }
        .weather-day-card {
            min-width: 120px;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 15px;
            margin-right: 10px;
            text-align: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .weather-day {
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }
        .weather-icon {
            font-size: 2.5em;
            margin: 5px 0;
        }
        .weather-desc { /* <-- NEW HUMAN CAPTION */
            font-size: 0.9em;
            color: #666;
            height: 2.5em; /* Reserve space for 2 lines */
            line-height: 1.2em;
        }
        .weather-temp-high {
            font-size: 1.2em;
            font-weight: bold;
            color: #111;
            margin-top: 5px;
        }
        .weather-temp-low {
            font-size: 1em;
            color: #555;
        }
        .weather-precip {
            font-size: 0.9em;
            color: #007bff;
            margin-top: 8px;
        }
    </style>
    <div class="weather-widget-container">
    """

    # Loop through the DataFrame rows
    for index, row in df.iterrows():
        day_name = index.strftime('%a') # e.g., "Mon"
        icon, description = get_weather_display(row['Weather Code'])
        temp_max = row['Temp Max (°C)']
        temp_min = row['Temp Min (°C)']
        precip = row['Precip. (mm)']
        
        html += f"""
        <div class="weather-day-card">
            <div class="weather-day">{day_name}</div>
            <div class="weather-icon">{icon}</div>
            <div class="weather-desc">{description}</div>
            <div class="weather-temp-high">{temp_max:.0f}°</div>
            <div class="weather-temp-low">{temp_min:.0f}°</div>
            <div class="weather-precip">🌧️ {precip:.1f} mm</div>
        </div>
        """
    
    html += "</div>"
    return html

# MAIN ASYNC ORCHESTRATOR 
async def main_task(destination, preferences, duration, start_date):
    """
    Runs all async tasks in parallel.
    """
    async with httpx.AsyncClient() as client:
        
        
        st_geocode.write(f"...Analyzing destination: {destination}...")
        dest_loc = await asyncio.to_thread(get_geocode, destination)
        
        if dest_loc is None:
            st.error(f"Could not find coordinates for {destination}. Please check spelling or Google API key permissions.")
            return

        dest_lat, dest_lon = dest_loc['lat'], dest_loc['lng']
        st_geocode.success(f"Location found: ({dest_lat:.4f}, {dest_lon:.4f})")
        
        st_parallel.write("...Running tasks in parallel...")
        
        st.write("...Finding best hotel...")
        recommended_hotels = await hotel_agent.find_hotels(preferences, destination, top_k=3)
        
        if not recommended_hotels:
            st.warning("No matching hotels found in your destination. Using a generic hotel.")
            top_hotel = { "name": f"Hotel in {destination}" }
        else:
            top_hotel = recommended_hotels[0]

        
        tasks = {
            "weather": asyncio.create_task(
                weather_agent.get_daily_forecast(client, dest_lat, dest_lon, start_date, duration)
            ),
            "itinerary": asyncio.create_task(
                itinerary_agent.create_itinerary(client, destination, top_hotel, duration)
            )
        }
        await asyncio.gather(*tasks.values())
        st_parallel.success("...All tasks complete!")

        
        weather_df = tasks['weather'].result()
        itinerary_data = tasks['itinerary'].result()
        itinerary_text = itinerary_data.get("itinerary_text", "Error")
        locations = itinerary_data.get("locations", [])
        
       
        st_geocode_locs.write("...Geocoding itinerary locations...")
        map_markers = []
        if locations:
            day_groups = {}
            for loc in locations:
                day = loc.get('day', 1)
                if day not in day_groups: day_groups[day] = []
                day_groups[day].append(loc)

            geocode_tasks = []
            for day, locs in day_groups.items():
                for loc in locs:
                    geocode_tasks.append(
                        (day, loc['name'], asyncio.to_thread(get_geocode, loc['name']))
                    )
            geocode_results = await asyncio.gather(*[task for day, name, task in geocode_tasks])
            
            for i, (lat_lng) in enumerate(geocode_results):
                if lat_lng:
                    day, name = geocode_tasks[i][0], geocode_tasks[i][1]
                    map_markers.append({
                        "lat": lat_lng['lat'], "lng": lat_lng['lng'],
                        "name": name, "day": day, "color": get_day_color(day)
                    })
        st_geocode_locs.success(f"...Found {len(map_markers)} locations!")

        
        route_polylines = []
        if map_markers:
            day_routes = pd.DataFrame(map_markers).groupby('day')
            route_tasks = []
            for day, group in day_routes:
                day_waypoints = group[['lat', 'lng']].to_dict('records')
                route_tasks.append(
                    (day, asyncio.to_thread(get_google_directions, day_waypoints))
                )
            route_results = await asyncio.gather(*[task for day, task in route_tasks])

            for i, polyline in enumerate(route_results):
                if polyline:
                    day = route_tasks[i][0]
                    route_polylines.append({
                        "day": day, "polyline": polyline, "color": get_day_color(day)
                    })

        return {
            "weather_df": weather_df,
            "recommended_hotels": recommended_hotels,
            "itinerary_text": itinerary_text,
            "map_markers": map_markers,
            "center_lat": dest_lat,
            "center_lon": dest_lon,
            "route_polylines": route_polylines
        }


st.set_page_config(layout="wide")
st.title("Async AI Travel Planner ✈️")
st.write("Plan your trip using live Google data.")

destination = st.text_input("Enter your destination (e.g., Mumbai):", "Mumbai")
preferences = st.text_area("Describe your ideal hotel:", "A luxury hotel with a spa.")

today = datetime.now().date()
start_date_obj = st.date_input(
    "Select your trip start date",
    value=today,
    min_value=today,
    max_value=today + timedelta(days=90) 
)
start_date_str = start_date_obj.strftime("%Y-%m-%d") 
duration = st.slider("Trip duration (days):", 1, 10, 4)

if st.button("Generate Travel Plan ✨"):
    
    st_geocode = st.empty()
    st_parallel = st.empty()
    st_geocode_locs = st.empty()

    try:
        results = asyncio.run(main_task(destination, preferences, duration, start_date_str))
        
        if results:
            col1, col2 = st.columns([1, 1])

            with col1:
                st.subheader("🏨 Recommended Hotels")
                if not results['recommended_hotels']:
                    st.warning("No matching hotels found in your destination.")
                for hotel in results['recommended_hotels']:
                    st.write(f"**{hotel['name']}** (Rating: {hotel.get('rating', 'N/A')})")
                    st.caption(f"{hotel['description']} - *{hotel['address']}*")

                
                st.subheader(f"Weather Forecast for {destination.title()}")
                weather_html = create_weather_widget_html(results['weather_df'])
                st.components.v1.html(weather_html, height=280)
                

                st.subheader(f"📜 Your {duration}-Day Itinerary")
                st.markdown(results['itinerary_text'])
                
                st.subheader("Behind the Scenes: Project Architecture")
                st.image("travel_planner.png",caption="The architecture of the AI Travel Planner", use_container_width=True)

            with col2:
                st.subheader("🗺 Itinerary Map")
                
                map_html = create_google_map_html(
                    GOOGLE_MAPS_API_KEY,
                    results['center_lat'],
                    results['center_lon'],
                    results['map_markers'],
                    results['route_polylines']
                )
                st.components.v1.html(map_html, height=500)

    except Exception as e:
        st.error(f"An error occurred: {e}")
        #st.code(traceback.format_exc())