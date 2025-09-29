from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date, time, datetime, timedelta
import random
from .base import BaseTool, ToolInput, ToolOutput


class EventSearchInput(ToolInput):
    """Input schema for events and attractions search."""
    destination: str = Field(..., description="Destination city")
    start_date: date = Field(..., description="Start date for search")
    end_date: date = Field(..., description="End date for search")
    categories: List[str] = Field(default=[], description="Event categories (museum, concert, festival, etc.)")
    kid_friendly: Optional[bool] = Field(None, description="Filter for kid-friendly events")
    max_price: Optional[float] = Field(None, description="Maximum ticket price")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of results")


class Event(BaseModel):
    """Event or attraction information."""
    name: str
    category: str
    description: str
    location: str
    date: Optional[date] = None  # None for permanent attractions
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    price_usd: float
    kid_friendly: bool = False
    duration_hours: Optional[float] = None
    rating: float = Field(ge=0, le=5)
    booking_required: bool = False
    opening_hours: Optional[str] = None
    website: Optional[str] = None


class EventSearchOutput(ToolOutput):
    """Output schema for events search."""
    events: List[Event] = []
    search_params: Optional[Dict[str, Any]] = None


class EventsTool(BaseTool):
    """Tool for searching events and attractions."""
    
    def __init__(self):
        super().__init__(
            name="events",
            description="Search for events, attractions, museums, and activities",
            timeout_seconds=10
        )
        
        # Sample events and attractions by destination
        self.destination_events = {
            "kyoto": {
                "museums": [
                    {"name": "Kyoto National Museum", "price": 15, "kid_friendly": True, "rating": 4.5},
                    {"name": "Kyoto Museum of Traditional Crafts", "price": 8, "kid_friendly": True, "rating": 4.2},
                    {"name": "Kyoto International Manga Museum", "price": 12, "kid_friendly": True, "rating": 4.7}
                ],
                "temples": [
                    {"name": "Kiyomizu-dera Temple", "price": 5, "kid_friendly": True, "rating": 4.8},
                    {"name": "Fushimi Inari Shrine", "price": 0, "kid_friendly": True, "rating": 4.9},
                    {"name": "Golden Pavilion (Kinkaku-ji)", "price": 6, "kid_friendly": True, "rating": 4.7}
                ],
                "gardens": [
                    {"name": "Bamboo Grove", "price": 0, "kid_friendly": True, "rating": 4.6},
                    {"name": "Philosopher's Path", "price": 0, "kid_friendly": True, "rating": 4.4},
                    {"name": "Maruyama Park", "price": 0, "kid_friendly": True, "rating": 4.3}
                ],
                "cultural": [
                    {"name": "Gion Geisha District Walking Tour", "price": 25, "kid_friendly": False, "rating": 4.5},
                    {"name": "Traditional Tea Ceremony", "price": 35, "kid_friendly": True, "rating": 4.6},
                    {"name": "Kimono Rental Experience", "price": 40, "kid_friendly": True, "rating": 4.4}
                ]
            },
            "paris": {
                "museums": [
                    {"name": "Louvre Museum", "price": 17, "kid_friendly": True, "rating": 4.6},
                    {"name": "Musée d'Orsay", "price": 14, "kid_friendly": True, "rating": 4.5},
                    {"name": "Centre Pompidou", "price": 15, "kid_friendly": True, "rating": 4.3}
                ],
                "landmarks": [
                    {"name": "Eiffel Tower", "price": 25, "kid_friendly": True, "rating": 4.7},
                    {"name": "Notre-Dame Cathedral", "price": 0, "kid_friendly": True, "rating": 4.5},
                    {"name": "Arc de Triomphe", "price": 12, "kid_friendly": True, "rating": 4.4}
                ],
                "entertainment": [
                    {"name": "Seine River Cruise", "price": 18, "kid_friendly": True, "rating": 4.3},
                    {"name": "Moulin Rouge Show", "price": 85, "kid_friendly": False, "rating": 4.2},
                    {"name": "Disneyland Paris", "price": 75, "kid_friendly": True, "rating": 4.5}
                ]
            },
            "tokyo": {
                "museums": [
                    {"name": "Tokyo National Museum", "price": 12, "kid_friendly": True, "rating": 4.4},
                    {"name": "teamLab Borderless", "price": 32, "kid_friendly": True, "rating": 4.8},
                    {"name": "Ghibli Museum", "price": 20, "kid_friendly": True, "rating": 4.7}
                ],
                "districts": [
                    {"name": "Shibuya Crossing Experience", "price": 0, "kid_friendly": True, "rating": 4.5},
                    {"name": "Harajuku Fashion District", "price": 0, "kid_friendly": True, "rating": 4.3},
                    {"name": "Asakusa Traditional District", "price": 0, "kid_friendly": True, "rating": 4.4}
                ],
                "entertainment": [
                    {"name": "Robot Restaurant Show", "price": 65, "kid_friendly": False, "rating": 4.1},
                    {"name": "Tokyo Skytree", "price": 28, "kid_friendly": True, "rating": 4.6},
                    {"name": "Tsukiji Fish Market Tour", "price": 15, "kid_friendly": True, "rating": 4.5}
                ]
            }
        }
        
        self.categories = ["museum", "temple", "garden", "cultural", "landmark", "entertainment", "district", "festival", "concert"]
        
        self.opening_hours_templates = [
            "9:00 AM - 5:00 PM",
            "10:00 AM - 6:00 PM", 
            "8:00 AM - 8:00 PM",
            "24 hours",
            "Varies by season"
        ]
    
    def _get_destination_events(self, destination: str) -> Dict[str, List[Dict]]:
        """Get events for a specific destination."""
        dest_key = destination.lower()
        for key in self.destination_events:
            if key in dest_key:
                return self.destination_events[key]
        
        # Default events for unknown destinations
        return {
            "museums": [
                {"name": "City Art Museum", "price": 12, "kid_friendly": True, "rating": 4.3},
                {"name": "History Museum", "price": 10, "kid_friendly": True, "rating": 4.2}
            ],
            "landmarks": [
                {"name": "City Center Square", "price": 0, "kid_friendly": True, "rating": 4.1},
                {"name": "Historic Cathedral", "price": 5, "kid_friendly": True, "rating": 4.4}
            ],
            "entertainment": [
                {"name": "City Walking Tour", "price": 20, "kid_friendly": True, "rating": 4.2},
                {"name": "Local Cultural Show", "price": 35, "kid_friendly": False, "rating": 4.0}
            ]
        }
    
    def _generate_event_details(self, event_data: Dict, category: str, search_date: date) -> Event:
        """Generate detailed event information."""
        # Determine if this is a permanent attraction or timed event
        permanent_categories = ["museum", "temple", "garden", "landmark", "district"]
        is_permanent = category in permanent_categories
        
        # Generate timing
        if is_permanent:
            event_date = None
            start_time = None
            end_time = None
            opening_hours = random.choice(self.opening_hours_templates)
            duration_hours = random.uniform(1.0, 4.0)
        else:
            # Timed event
            event_date = search_date
            start_time = time(hour=random.randint(10, 20), minute=random.choice([0, 30]))
            duration = random.uniform(1.5, 3.0)
            end_hour = start_time.hour + int(duration)
            end_minute = start_time.minute + int((duration % 1) * 60)
            if end_minute >= 60:
                end_hour += 1
                end_minute -= 60
            end_time = time(hour=min(end_hour, 23), minute=end_minute)
            opening_hours = None
            duration_hours = duration
        
        # Generate description
        descriptions = {
            "museum": f"Explore fascinating exhibits and collections at {event_data['name']}",
            "temple": f"Visit the sacred and beautiful {event_data['name']}",
            "garden": f"Stroll through the peaceful {event_data['name']}",
            "cultural": f"Experience authentic local culture with {event_data['name']}",
            "landmark": f"See the iconic {event_data['name']}",
            "entertainment": f"Enjoy {event_data['name']} for a memorable experience",
            "district": f"Explore the vibrant {event_data['name']} area"
        }
        
        return Event(
            name=event_data["name"],
            category=category,
            description=descriptions.get(category, f"Experience {event_data['name']}"),
            location=f"{event_data['name']} Location",
            date=event_date,
            start_time=start_time,
            end_time=end_time,
            price_usd=event_data["price"],
            kid_friendly=event_data["kid_friendly"],
            duration_hours=round(duration_hours, 1) if duration_hours else None,
            rating=event_data["rating"],
            booking_required=event_data["price"] > 20,
            opening_hours=opening_hours,
            website=f"https://www.{event_data['name'].lower().replace(' ', '')}.com"
        )
    
    async def _execute(self, input_data: EventSearchInput) -> EventSearchOutput:
        """Execute events search."""
        dest_events = self._get_destination_events(input_data.destination)
        
        events = []
        search_days = (input_data.end_date - input_data.start_date).days + 1
        
        # Collect all available events
        all_events = []
        for category, event_list in dest_events.items():
            for event_data in event_list:
                # Filter by category if specified
                if input_data.categories and category not in input_data.categories:
                    continue
                
                # Filter by kid_friendly if specified
                if input_data.kid_friendly is not None and event_data["kid_friendly"] != input_data.kid_friendly:
                    continue
                
                # Filter by price if specified
                if input_data.max_price is not None and event_data["price"] > input_data.max_price:
                    continue
                
                all_events.append((category, event_data))
        
        # Generate events for the search period
        for i in range(min(input_data.max_results, len(all_events) * search_days)):
            category, event_data = random.choice(all_events)
            search_date = input_data.start_date + timedelta(days=random.randint(0, search_days - 1))
            
            event = self._generate_event_details(event_data, category, search_date)
            events.append(event)
        
        # Remove duplicates and sort by rating
        seen_names = set()
        unique_events = []
        for event in events:
            if event.name not in seen_names:
                unique_events.append(event)
                seen_names.add(event.name)
        
        unique_events.sort(key=lambda e: (-e.rating, e.price_usd))
        
        return EventSearchOutput(
            success=True,
            data={"events": [e.model_dump() for e in unique_events[:input_data.max_results]]},
            events=unique_events[:input_data.max_results],
            search_params=input_data.model_dump()
        )
    
    def get_input_schema(self) -> type[ToolInput]:
        return EventSearchInput
    
    def get_output_schema(self) -> type[ToolOutput]:
        return EventSearchOutput

