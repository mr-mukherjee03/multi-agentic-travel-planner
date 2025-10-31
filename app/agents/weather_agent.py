import httpx
import pandas as pd
import asyncio
from datetime import datetime, timedelta
import traceback
from logging import getLogger

logger = getLogger(__name__)

class WeatherAnalysisAgent:
    def __init__(self):
        """
        Initializes the agent with the Open-Meteo Forecast API URL.
        """
        self.api_url = "https://api.open-meteo.com/v1/forecast"
        logger.info("Initialized Open-Meteo WeatherAnalysisAgent (async httpx).")

    async def get_daily_forecast(self, client, lat, lon, start_date, duration):
        """
        Fetches the daily weather forecast from Open-Meteo asynchronously.
        """
        logger.info(f"Fetching {duration}-day forecast for ({lat}, {lon}) from {start_date}...")
        
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = start_date_obj + timedelta(days=min(duration - 1, 15))
        end_date_str = end_date_obj.strftime("%Y-%m-%d")

        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max", 
                "temperature_2m_min", 
                "precipitation_sum", 
                "wind_speed_10m_max",
                "weather_code"  # <-- ADDED THIS
            ],
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date_str
        }
        
        try:
            response = await client.get(self.api_url, params=params, timeout=20)
            response.raise_for_status() 
            data = response.json()

            if 'daily' not in data:
                logger.info("Open-Meteo response OK, but 'daily' key missing.")
                return pd.DataFrame()

            daily_data = data['daily']
            
            df = pd.DataFrame()
            df['Date'] = pd.to_datetime(daily_data['time'])
            df['Temp Max (°C)'] = daily_data.get('temperature_2m_max', 'N/A')
            df['Temp Min (°C)'] = daily_data.get('temperature_2m_min', 'N/A')
            df['Precip. (mm)'] = daily_data.get('precipitation_sum', 'N/A')
            df['Wind (km/h)'] = daily_data.get('wind_speed_10m_max', 'N/A')
            df['Weather Code'] = daily_data.get('weather_code', 0) 
            
            return df.set_index("Date")

        except httpx.HTTPStatusError as e:
            logger.error(f"Open-Meteo API Error: {e}")
        except Exception as e:
            logger.error(f"Error in WeatherAgent.get_daily_forecast: {e}")
            logger.error(traceback.format_exc())

        return pd.DataFrame()