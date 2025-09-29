from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import random
import math
from .base import BaseTool, ToolInput, ToolOutput


class TransitInput(ToolInput):
    """Input schema for transit time estimation."""
    origin: str = Field(..., description="Origin location")
    destination: str = Field(..., description="Destination location")
    mode: str = Field("mixed", description="Transport mode: walk, public, taxi, mixed")
    departure_time: Optional[str] = Field(None, description="Departure time (HH:MM)")


class TransitRoute(BaseModel):
    """Transit route information."""
    mode: str
    duration_minutes: int
    distance_km: float
    cost_usd: float
    description: str
    steps: List[str] = []
    walking_time_minutes: int = 0


class TransitOutput(ToolOutput):
    """Output schema for transit information."""
    routes: List[TransitRoute] = []
    fastest_route: Optional[TransitRoute] = None
    cheapest_route: Optional[TransitRoute] = None


class TransitTool(BaseTool):
    """Tool for estimating transit times and costs between locations."""
    
    def __init__(self):
        super().__init__(
            name="transit",
            description="Get door-to-door travel time and cost estimates between locations",
            timeout_seconds=5
        )
        
        # Base speeds in km/h
        self.speeds = {
            "walk": 5,
            "bicycle": 15,
            "bus": 25,
            "train": 40,
            "subway": 35,
            "taxi": 30,
            "car": 35
        }
        
        # Base costs per km
        self.costs_per_km = {
            "walk": 0,
            "bicycle": 0,
            "bus": 0.5,
            "train": 0.8,
            "subway": 0.6,
            "taxi": 2.5,
            "car": 1.2
        }
        
        # Common locations and their approximate distances
        self.location_distances = {
            # Kyoto
            ("gion", "kyoto station"): 3.5,
            ("gion", "kiyomizu temple"): 1.2,
            ("gion", "fushimi inari"): 8.5,
            ("kyoto station", "kinkaku-ji"): 7.2,
            ("kyoto station", "arashiyama"): 12.0,
            ("arashiyama", "bamboo grove"): 0.8,
            
            # Paris
            ("louvre", "eiffel tower"): 3.2,
            ("louvre", "notre dame"): 1.8,
            ("eiffel tower", "arc de triomphe"): 2.1,
            ("marais", "montmartre"): 4.5,
            ("latin quarter", "champs elysees"): 3.8,
            
            # Tokyo
            ("shibuya", "harajuku"): 2.1,
            ("shibuya", "ginza"): 4.8,
            ("shinjuku", "asakusa"): 8.2,
            ("tokyo station", "tsukiji"): 2.5,
            ("ginza", "tokyo skytree"): 6.1,
        }
    
    def _estimate_distance(self, origin: str, destination: str) -> float:
        """Estimate distance between two locations."""
        origin_clean = origin.lower().strip()
        dest_clean = destination.lower().strip()
        
        # Check direct mapping
        key = (origin_clean, dest_clean)
        reverse_key = (dest_clean, origin_clean)
        
        if key in self.location_distances:
            return self.location_distances[key]
        elif reverse_key in self.location_distances:
            return self.location_distances[reverse_key]
        
        # Check partial matches
        for (loc1, loc2), distance in self.location_distances.items():
            if (loc1 in origin_clean and loc2 in dest_clean) or \
               (loc2 in origin_clean and loc1 in dest_clean):
                return distance
        
        # Default estimate based on typical city distances
        return random.uniform(2.0, 15.0)
    
    def _calculate_walking_route(self, distance_km: float) -> TransitRoute:
        """Calculate walking route."""
        duration = int((distance_km / self.speeds["walk"]) * 60)
        
        return TransitRoute(
            mode="walk",
            duration_minutes=duration,
            distance_km=distance_km,
            cost_usd=0,
            description=f"Walk {distance_km:.1f} km",
            steps=[f"Walk {distance_km:.1f} km to destination"],
            walking_time_minutes=duration
        )
    
    def _calculate_public_transport_route(self, distance_km: float) -> TransitRoute:
        """Calculate public transport route."""
        # Assume combination of walking + public transport
        walking_distance = random.uniform(0.3, 0.8)  # Walk to/from stations
        public_distance = distance_km - walking_distance
        
        # Choose transport type based on distance
        if distance_km < 3:
            transport_type = "bus"
        elif distance_km < 10:
            transport_type = random.choice(["bus", "subway"])
        else:
            transport_type = random.choice(["train", "subway"])
        
        # Calculate times
        walking_time = int((walking_distance / self.speeds["walk"]) * 60)
        public_time = int((public_distance / self.speeds[transport_type]) * 60)
        waiting_time = random.randint(3, 12)  # Wait for transport
        
        total_time = walking_time + public_time + waiting_time
        cost = public_distance * self.costs_per_km[transport_type] + random.uniform(1, 3)  # Base fare
        
        steps = [
            f"Walk {walking_distance:.1f} km to {transport_type} station ({walking_time} min)",
            f"Take {transport_type} for {public_distance:.1f} km ({public_time} min)",
            f"Walk to destination"
        ]
        
        return TransitRoute(
            mode="public",
            duration_minutes=total_time,
            distance_km=distance_km,
            cost_usd=round(cost, 2),
            description=f"Public transport via {transport_type}",
            steps=steps,
            walking_time_minutes=walking_time
        )
    
    def _calculate_taxi_route(self, distance_km: float) -> TransitRoute:
        """Calculate taxi/ride-hail route."""
        # Account for traffic and route efficiency
        actual_distance = distance_km * random.uniform(1.1, 1.3)
        duration = int((actual_distance / self.speeds["taxi"]) * 60)
        
        # Taxi pricing: base fare + distance + time
        base_fare = random.uniform(3, 8)
        distance_cost = actual_distance * self.costs_per_km["taxi"]
        time_cost = duration * 0.3  # Per minute charge
        cost = base_fare + distance_cost + time_cost
        
        return TransitRoute(
            mode="taxi",
            duration_minutes=duration,
            distance_km=actual_distance,
            cost_usd=round(cost, 2),
            description=f"Taxi/ride-hail {actual_distance:.1f} km",
            steps=[f"Take taxi directly to destination ({duration} min)"],
            walking_time_minutes=2  # Minimal walking to/from pickup
        )
    
    def _calculate_mixed_route(self, distance_km: float) -> TransitRoute:
        """Calculate optimal mixed-mode route."""
        if distance_km < 1.5:
            return self._calculate_walking_route(distance_km)
        elif distance_km < 8:
            return self._calculate_public_transport_route(distance_km)
        else:
            # For longer distances, compare public vs taxi
            public_route = self._calculate_public_transport_route(distance_km)
            taxi_route = self._calculate_taxi_route(distance_km)
            
            # Choose based on time vs cost tradeoff
            if taxi_route.duration_minutes < public_route.duration_minutes * 0.7:
                return taxi_route
            else:
                return public_route
    
    async def _execute(self, input_data: TransitInput) -> TransitOutput:
        """Execute transit calculation."""
        distance_km = self._estimate_distance(input_data.origin, input_data.destination)
        
        routes = []
        
        # Always include walking if reasonable distance
        if distance_km <= 5:
            walking_route = self._calculate_walking_route(distance_km)
            routes.append(walking_route)
        
        # Public transport route
        if distance_km >= 1:
            public_route = self._calculate_public_transport_route(distance_km)
            routes.append(public_route)
        
        # Taxi route
        taxi_route = self._calculate_taxi_route(distance_km)
        routes.append(taxi_route)
        
        # Mixed mode route (if different from others)
        if input_data.mode == "mixed":
            mixed_route = self._calculate_mixed_route(distance_km)
            # Only add if significantly different
            if not any(abs(r.duration_minutes - mixed_route.duration_minutes) < 5 for r in routes):
                routes.append(mixed_route)
        
        # Filter by requested mode
        if input_data.mode != "mixed":
            routes = [r for r in routes if r.mode == input_data.mode or 
                     (input_data.mode == "public" and r.mode == "public")]
        
        # Find fastest and cheapest
        fastest_route = min(routes, key=lambda r: r.duration_minutes) if routes else None
        cheapest_route = min(routes, key=lambda r: r.cost_usd) if routes else None
        
        return TransitOutput(
            success=True,
            data={
                "routes": [r.model_dump() for r in routes],
                "fastest": fastest_route.model_dump() if fastest_route else None,
                "cheapest": cheapest_route.model_dump() if cheapest_route else None
            },
            routes=routes,
            fastest_route=fastest_route,
            cheapest_route=cheapest_route
        )
    
    def get_input_schema(self) -> type[ToolInput]:
        return TransitInput
    
    def get_output_schema(self) -> type[ToolOutput]:
        return TransitOutput

