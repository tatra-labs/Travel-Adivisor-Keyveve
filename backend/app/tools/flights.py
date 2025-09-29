from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date, timedelta
import random
from .base import BaseTool, ToolInput, ToolOutput


class FlightSearchInput(ToolInput):
    """Input schema for flight search."""
    origin: str = Field(..., description="Origin airport code (e.g., 'LAX')")
    destination: str = Field(..., description="Destination airport code (e.g., 'NRT')")
    departure_date: date = Field(..., description="Departure date")
    return_date: Optional[date] = Field(None, description="Return date for round-trip")
    passengers: int = Field(1, ge=1, le=9, description="Number of passengers")
    class_preference: str = Field("economy", description="Cabin class: economy, business, first")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results")


class Flight(BaseModel):
    """Flight information."""
    airline: str
    flight_number: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    price_usd: float
    co2_kg: float
    stops: int = 0
    aircraft_type: Optional[str] = None


class FlightSearchOutput(ToolOutput):
    """Output schema for flight search."""
    flights: List[Flight] = []
    search_params: Optional[Dict[str, Any]] = None


class FlightsTool(BaseTool):
    """Tool for searching flights with fixture data and pricing heuristics."""
    
    def __init__(self):
        super().__init__(
            name="flights",
            description="Search for flights between airports with pricing and CO2 estimates",
            timeout_seconds=10
        )
        
        # Sample airlines and aircraft
        self.airlines = [
            "United Airlines", "American Airlines", "Delta Air Lines", 
            "Japan Airlines", "All Nippon Airways", "Air France",
            "British Airways", "Lufthansa", "Emirates", "Singapore Airlines"
        ]
        
        self.aircraft_types = [
            "Boeing 777", "Boeing 787", "Airbus A350", "Airbus A380",
            "Boeing 737", "Airbus A320", "Boeing 767", "Airbus A330"
        ]
    
    def _generate_flight_number(self, airline: str) -> str:
        """Generate realistic flight number."""
        airline_codes = {
            "United Airlines": "UA",
            "American Airlines": "AA", 
            "Delta Air Lines": "DL",
            "Japan Airlines": "JL",
            "All Nippon Airways": "NH",
            "Air France": "AF",
            "British Airways": "BA",
            "Lufthansa": "LH",
            "Emirates": "EK",
            "Singapore Airlines": "SQ"
        }
        code = airline_codes.get(airline, "XX")
        return f"{code}{random.randint(100, 9999)}"
    
    def _calculate_distance_km(self, origin: str, destination: str) -> float:
        """Calculate approximate distance between airports (simplified)."""
        # Simplified distance calculation based on common routes
        distances = {
            ("LAX", "NRT"): 8815,
            ("LAX", "KIX"): 8820,
            ("JFK", "NRT"): 10850,
            ("JFK", "CDG"): 5837,
            ("LAX", "CDG"): 9080,
            ("SFO", "NRT"): 8280,
            ("ORD", "NRT"): 10150,
        }
        
        key = (origin.upper(), destination.upper())
        reverse_key = (destination.upper(), origin.upper())
        
        if key in distances:
            return distances[key]
        elif reverse_key in distances:
            return distances[reverse_key]
        else:
            # Default estimate based on typical international flight
            return random.uniform(5000, 12000)
    
    def _calculate_price(self, distance_km: float, class_preference: str, stops: int) -> float:
        """Calculate flight price using heuristics."""
        # Base price per km
        base_price_per_km = 0.12
        
        # Class multipliers
        class_multipliers = {
            "economy": 1.0,
            "business": 3.5,
            "first": 6.0
        }
        
        # Calculate base price
        base_price = distance_km * base_price_per_km
        
        # Apply class multiplier
        price = base_price * class_multipliers.get(class_preference, 1.0)
        
        # Adjust for stops (direct flights are more expensive)
        if stops == 0:
            price *= 1.2
        elif stops == 1:
            price *= 0.9
        else:
            price *= 0.8
        
        # Add some randomness
        price *= random.uniform(0.8, 1.3)
        
        return round(price, 2)
    
    def _calculate_co2(self, distance_km: float, class_preference: str) -> float:
        """Calculate CO2 emissions in kg."""
        # Base emissions per km per passenger (economy)
        base_co2_per_km = 0.115  # kg CO2 per km
        
        # Class multipliers (business/first take more space)
        class_multipliers = {
            "economy": 1.0,
            "business": 2.3,
            "first": 3.5
        }
        
        co2 = distance_km * base_co2_per_km * class_multipliers.get(class_preference, 1.0)
        return round(co2, 1)
    
    def _generate_flight_times(self, departure_date: date, distance_km: float, stops: int) -> tuple:
        """Generate realistic departure and arrival times."""
        # Flight duration based on distance and stops
        base_duration = distance_km / 800  # Approximate speed in km/h
        if stops == 1:
            base_duration += 2  # 2 hour layover
        elif stops >= 2:
            base_duration += 4  # Multiple layovers
        
        duration_minutes = int(base_duration * 60)
        
        # Random departure time (prefer morning/afternoon)
        departure_hour = random.choices(
            [6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 20, 21],
            weights=[5, 8, 10, 12, 10, 8, 12, 10, 8, 6, 4, 3, 2, 1]
        )[0]
        departure_minute = random.choice([0, 15, 30, 45])
        
        departure_time = datetime.combine(departure_date, datetime.min.time().replace(
            hour=departure_hour, minute=departure_minute
        ))
        
        arrival_time = departure_time + timedelta(minutes=duration_minutes)
        
        return departure_time, arrival_time, duration_minutes
    
    async def _execute(self, input_data: FlightSearchInput) -> FlightSearchOutput:
        """Execute flight search with fixture data."""
        distance_km = self._calculate_distance_km(input_data.origin, input_data.destination)
        
        flights = []
        for i in range(input_data.max_results):
            # Vary number of stops
            stops = random.choices([0, 1, 2], weights=[60, 35, 5])[0]
            
            airline = random.choice(self.airlines)
            aircraft = random.choice(self.aircraft_types)
            
            departure_time, arrival_time, duration_minutes = self._generate_flight_times(
                input_data.departure_date, distance_km, stops
            )
            
            price = self._calculate_price(distance_km, input_data.class_preference, stops)
            co2 = self._calculate_co2(distance_km, input_data.class_preference)
            
            flight = Flight(
                airline=airline,
                flight_number=self._generate_flight_number(airline),
                departure_time=departure_time,
                arrival_time=arrival_time,
                duration_minutes=duration_minutes,
                price_usd=price,
                co2_kg=co2,
                stops=stops,
                aircraft_type=aircraft
            )
            flights.append(flight)
        
        # Sort by price
        flights.sort(key=lambda f: f.price_usd)
        
        return FlightSearchOutput(
            success=True,
            data={"flights": [f.model_dump() for f in flights]},
            flights=flights,
            search_params=input_data.model_dump()
        )
    
    def get_input_schema(self) -> type[ToolInput]:
        return FlightSearchInput
    
    def get_output_schema(self) -> type[ToolOutput]:
        return FlightSearchOutput

