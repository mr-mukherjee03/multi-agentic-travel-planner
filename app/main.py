import streamlit as st
from hotel_agent import HotelRecommenderAgent
from weather_agent import WeatherAnalysisAgent
from itinerary_agent import ItineraryPlannerAgent
import pandas as pd
import numpy as np
import os
import pydeck as pdk
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from dotenv import load_dotenv

load_dotenv()
os.environ["TOKENIZERS_PARALLELISM"] = "false"


historical_weather_data = [
    {'month': i, 'latitude': 41.9028, 'longitude': 12.4964, 'weather_score': np.random.rand()} for i in range(1, 13)
]

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    st.error("GEMINI_API_KEY not found. Please set it in your .env file.")
    st.stop()


weather_agent = WeatherAnalysisAgent()
hotel_agent = HotelRecommenderAgent() 
itinerary_agent = ItineraryPlannerAgent(api_key=gemini_api_key)


weather_agent.train(historical_weather_data)




@st.cache_data(ttl=3600)
def get_coordinates(place_name):
    """
    Gets lat/lon for a place name using Nominatim and caches the result.
    """
    try:
        geolocator = Nominatim(user_agent="ai_travel_planner_v1", timeout=10)
        
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        
        print(f"Geocoding: '{place_name}'") 
        location = geocode(place_name)
        
        if location:
            print("...Success!") 
            return location.latitude, location.longitude
        else:
            print("...Failed to geocode.") 
            return None, None
            
    except Exception as e:
        print(f"Geocoding error for {place_name}: {e}")
        return None, None

def get_day_color(day):
    """Assigns a unique color to each day."""
    colors = [
        [255, 0, 0],    # Day 1 (Red)
        [0, 0, 255],    # Day 2 (Blue)
        [0, 255, 0],    # Day 3 (Green)
        [255, 255, 0],  # Day 4 (Yellow)
        [0, 255, 255],  # Day 5 (Cyan)
        [255, 0, 255],  # Day 6 (Magenta)
        [255, 165, 0],  # Day 7 (Orange)
        [128, 0, 128],  # Day 8 (Purple)
        [0, 128, 0],    # Day 9 (Dark Green)
        [255, 192, 203] # Day 10 (Pink)
    ]

    return colors[(day - 1) % len(colors)]


#Streamlit UI
st.title("AI Travel Planner ✈️")
st.write("Create a personalized travel plan for any city in India!")

#user inputs
destination = st.text_input("Enter your destination (e.g., Mumbai):", "Mumbai")
preferences = st.text_area("Describe your ideal hotel:", "A luxury hotel in Mumbai with a spa and city views.")
duration = st.slider("Trip duration (days):", 1, 10, 4) 

if st.button("Generate Travel Plan ✨"):
    with st.spinner("Generating your personalized travel plan... This may take a moment."):
        
        
        weather_results = weather_agent.predict_best_time({'latitude': 41.9028, 'longitude': 12.4964})
        best_months_list = weather_results.get('best_months', [])
        best_month = best_months_list[0]['month'] if best_months_list else 1
        
        recommended_hotels = hotel_agent.find_hotels(preferences, destination, top_k=3)
        
        if not recommended_hotels:
            st.error("Could not find a matching hotel. Please broaden your preferences.")
            st.stop()
            
      
        top_hotel = recommended_hotels[0]

     
        response_data = itinerary_agent.create_itinerary(destination, best_month, top_hotel, duration)
        itinerary_text = response_data.get("itinerary_text", "Failed to generate itinerary.")
        locations = response_data.get("locations", [])

        st.subheader("📆 Best Months to Visit")
        st.caption(f"(Note: Weather data is currently static for this demo)")
        for m in best_months_list:
            st.write(f"Month {m['month']}: Score {m['score']:.2f}")
            
        st.subheader("🏨 Recommended Hotels ( from real Indian database! )")
        for hotel in recommended_hotels:
            
            st.write(f"**{hotel['name']}** (Rating: {hotel.get('rating', 'N/A')})")
            st.caption(f"{hotel['description']} - *{hotel['address']}*")

        st.subheader(f"📜 Your {duration}-Day Itinerary")
        st.markdown(itinerary_text)
        
      
        st.subheader("🗺 Itinerary Map")
        
        map_locations = []
        if locations:
            progress_bar = st.progress(0, text="Geocoding locations...")
            for i, loc in enumerate(locations):
                # Geocode each location name from the itinerary
                lat, lon = get_coordinates(loc['name'])
                if lat and lon:
                    loc['lat'] = lat
                    loc['lon'] = lon
                    loc['day_label'] = f"Day {loc['day']}"
                    loc['color'] = get_day_color(loc['day'])
                    map_locations.append(loc)
                progress_bar.progress((i + 1) / len(locations))
            progress_bar.empty()

        if map_locations:
            df = pd.DataFrame(map_locations)
            
            try:
                MAPTILER_KEY = os.getenv("MAPTILER_API_KEY")
            except KeyError:
                st.error("MAPTILER_API_KEY not found. Please add it to .streamlit/secrets.toml")
                st.stop()

            map_styles = {
                "Streets": f"https://api.maptiler.com/maps/streets-v2/style.json?key={MAPTILER_KEY}",
                "Satellite": f"https://api.maptiler.com/maps/satellite/style.json?key={MAPTILER_KEY}",
                "Basic (Light)": f"https://api.maptiler.com/maps/basic-v2/style.json?key={MAPTILER_KEY}",
                "Basic (Dark)": f"https://api.maptiler.com/maps/basic-v2-dark/style.json?key={MAPTILER_KEY}",
                "Outdoor": f"https://api.maptiler.com/maps/outdoor-v2/style.json?key={MAPTILER_KEY}",
            }
            
            selected_style_name = st.selectbox("Select Map Style:", options=list(map_styles.keys()))


            view_state = pdk.ViewState(
                latitude=df['lat'].mean(),
                longitude=df['lon'].mean(),
                zoom=12,
                pitch=50,
            )
            
            scatterplot_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df,
                get_position=["lon", "lat"],
                get_fill_color="color",
                get_radius=100,
                pickable=True,
            )

           
            text_layer = pdk.Layer(
                "TextLayer",
                data=df,
                get_position=["lon", "lat"],
                get_text="day_label",
                get_color=[0, 0, 0, 200],  # Default Black text
                get_size=16,
                get_alignment_baseline="'bottom'",
            )
            

            if selected_style_name in ["Basic (Dark)", "Satellite"]:
                text_layer.get_color = [255, 255, 255, 200] # White text

            # Tooltip
            tooltip = {
                "html": "<b>{day_label}: {name}</b><br/>{description}",
                "style": {"backgroundColor": "steelblue", "color": "white"}
            }

            # Create and render the deck
            st.pydeck_chart(pdk.Deck(
                map_style=map_styles[selected_style_name], # Use the selected MapTiler style
                initial_view_state=view_state,
                layers=[scatterplot_layer, text_layer],
                tooltip=tooltip,
            ))
        else:
            st.warning("Could not geocode locations for the map. The itinerary may be too vague.")