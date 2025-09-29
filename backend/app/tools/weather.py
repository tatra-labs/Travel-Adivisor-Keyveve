from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, datetime
import random
import asyncio
import aiohttp
from .base import BaseTool, ToolInput, ToolOutput


class WeatherInput(ToolInput):
    """Input schema for weather forecast."""
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    start_date: date = Field(..., description="Start date for forecast")
    end_date: date = Field(..., description="End date for forecast")
    include_hourly: bool = Field(False, description="Include hourly forecast")


class WeatherDay(BaseModel):
    """Daily weather information."""
    date: date
    temperature_max: float  # Celsius
    temperature_min: float  # Celsius
    precipitation_mm: float
    precipitation_probability: int  # 0-100
    wind_speed_kmh: float
    weather_code: int  # WMO weather codes
    weather_description: str
    is_rainy: bool = False
    is_sunny: bool = False
    is_cloudy: bool = False


class WeatherHour(BaseModel):
    """Hourly weather information."""
    datetime: datetime
    temperature: float  # Celsius
    precipitation_mm: float
    weather_code: int
    weather_description: str


class WeatherOutput(ToolOutput):
    """Output schema for weather forecast."""
    daily_forecast: List[WeatherDay] = []
    hourly_forecast: List[WeatherHour] = []
    location: Optional[Dict[str, float]] = None


class WeatherTool(BaseTool):
    """Tool for getting weather forecasts using Open-Meteo API with fallback to fixtures."""
    
    def __init__(self):
        super().__init__(
            name="weather",
            description="Get weather forecast for a location with caching",
            timeout_seconds=10
        )
        
        # WMO Weather interpretation codes
        self.weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy", 
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        self.rainy_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
        self.sunny_codes = {0, 1}
        self.cloudy_codes = {2, 3, 45, 48}
    
    def _generate_fixture_weather(self, lat: float, lon: float, start_date: date, end_date: date) -> List[WeatherDay]:
        """Generate realistic fixture weather data."""
        days = []
        current_date = start_date
        
        # Determine climate based on latitude (simplified)
        if abs(lat) < 23.5:  # Tropical
            temp_base = 28
            temp_variation = 5
            rain_probability = 0.4
        elif abs(lat) < 40:  # Temperate
            temp_base = 18
            temp_variation = 8
            rain_probability = 0.3
        else:  # Cold
            temp_base = 8
            temp_variation = 12
            rain_probability = 0.25
        
        # Seasonal adjustment (simplified for Northern Hemisphere)
        month = start_date.month
        if month in [12, 1, 2]:  # Winter
            temp_base -= 8
            rain_probability += 0.1
        elif month in [6, 7, 8]:  # Summer
            temp_base += 8
            rain_probability -= 0.1
        
        while current_date <= end_date:
            # Generate weather with some persistence (weather patterns)
            if days and random.random() < 0.6:  # 60% chance to continue similar weather
                prev_day = days[-1]
                temp_max = prev_day.temperature_max + random.uniform(-3, 3)
                is_rainy = prev_day.is_rainy if random.random() < 0.7 else random.random() < rain_probability
            else:
                temp_max = temp_base + random.uniform(-temp_variation, temp_variation)
                is_rainy = random.random() < rain_probability
            
            temp_min = temp_max - random.uniform(5, 12)
            
            if is_rainy:
                weather_code = random.choice([61, 63, 80, 81])
                precipitation = random.uniform(2, 15)
                precip_prob = random.randint(70, 95)
            else:
                if random.random() < 0.4:  # Sunny
                    weather_code = random.choice([0, 1])
                else:  # Cloudy
                    weather_code = random.choice([2, 3])
                precipitation = 0
                precip_prob = random.randint(0, 20)
            
            day = WeatherDay(
                date=current_date,
                temperature_max=round(temp_max, 1),
                temperature_min=round(temp_min, 1),
                precipitation_mm=round(precipitation, 1),
                precipitation_probability=precip_prob,
                wind_speed_kmh=round(random.uniform(5, 25), 1),
                weather_code=weather_code,
                weather_description=self.weather_codes[weather_code],
                is_rainy=weather_code in self.rainy_codes,
                is_sunny=weather_code in self.sunny_codes,
                is_cloudy=weather_code in self.cloudy_codes
            )
            days.append(day)
            current_date = date.fromordinal(current_date.toordinal() + 1)
        
        return days
    
    async def _fetch_real_weather(self, lat: float, lon: float, start_date: date, end_date: date) -> Optional[List[WeatherDay]]:
        """Fetch real weather data from Open-Meteo API."""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,weather_code",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timezone": "auto"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_weather_response(data)
            
        except Exception as e:
            print(f"Weather API error: {e}")
        
        return None
    
    def _parse_weather_response(self, data: Dict) -> List[WeatherDay]:
        """Parse Open-Meteo API response."""
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        temp_max = daily.get("temperature_2m_max", [])
        temp_min = daily.get("temperature_2m_min", [])
        precipitation = daily.get("precipitation_sum", [])
        precip_prob = daily.get("precipitation_probability_max", [])
        wind_speed = daily.get("wind_speed_10m_max", [])
        weather_codes = daily.get("weather_code", [])
        
        days = []
        for i in range(len(dates)):
            weather_code = weather_codes[i] if i < len(weather_codes) else 1
            
            day = WeatherDay(
                date=date.fromisoformat(dates[i]),
                temperature_max=temp_max[i] if i < len(temp_max) else 20,
                temperature_min=temp_min[i] if i < len(temp_min) else 10,
                precipitation_mm=precipitation[i] if i < len(precipitation) else 0,
                precipitation_probability=precip_prob[i] if i < len(precip_prob) else 0,
                wind_speed_kmh=wind_speed[i] if i < len(wind_speed) else 10,
                weather_code=weather_code,
                weather_description=self.weather_codes.get(weather_code, "Unknown"),
                is_rainy=weather_code in self.rainy_codes,
                is_sunny=weather_code in self.sunny_codes,
                is_cloudy=weather_code in self.cloudy_codes
            )
            days.append(day)
        
        return days
    
    async def _execute(self, input_data: WeatherInput) -> WeatherOutput:
        """Execute weather forecast request."""
        # Try to fetch real weather data first
        daily_forecast = await self._fetch_real_weather(
            input_data.latitude, 
            input_data.longitude,
            input_data.start_date,
            input_data.end_date
        )
        
        # Fallback to fixture data if API fails
        if not daily_forecast:
            daily_forecast = self._generate_fixture_weather(
                input_data.latitude,
                input_data.longitude, 
                input_data.start_date,
                input_data.end_date
            )
        
        # Generate hourly data if requested (simplified)
        hourly_forecast = []
        if input_data.include_hourly and daily_forecast:
            for day in daily_forecast[:3]:  # Only first 3 days for hourly
                for hour in range(0, 24, 3):  # Every 3 hours
                    temp = day.temperature_min + (day.temperature_max - day.temperature_min) * (
                        0.5 + 0.5 * random.sin((hour - 6) * 3.14159 / 12)  # Temperature curve
                    )
                    
                    hourly = WeatherHour(
                        datetime=datetime.combine(day.date, datetime.min.time().replace(hour=hour)),
                        temperature=round(temp, 1),
                        precipitation_mm=day.precipitation_mm / 8 if day.is_rainy else 0,
                        weather_code=day.weather_code,
                        weather_description=day.weather_description
                    )
                    hourly_forecast.append(hourly)
        
        return WeatherOutput(
            success=True,
            data={
                "daily_forecast": [d.model_dump() for d in daily_forecast],
                "hourly_forecast": [h.model_dump() for h in hourly_forecast]
            },
            daily_forecast=daily_forecast,
            hourly_forecast=hourly_forecast,
            location={"latitude": input_data.latitude, "longitude": input_data.longitude}
        )
    
    def get_input_schema(self) -> type[ToolInput]:
        return WeatherInput
    
    def get_output_schema(self) -> type[ToolOutput]:
        return WeatherOutput

