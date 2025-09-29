from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date
import random
from .base import BaseTool, ToolInput, ToolOutput


class LodgingSearchInput(ToolInput):
    """Input schema for lodging search."""
    destination: str = Field(..., description="Destination city or area")
    check_in: date = Field(..., description="Check-in date")
    check_out: date = Field(..., description="Check-out date")
    guests: int = Field(2, ge=1, le=10, description="Number of guests")
    rooms: int = Field(1, ge=1, le=5, description="Number of rooms")
    neighborhood: Optional[str] = Field(None, description="Preferred neighborhood")
    max_price_per_night: Optional[float] = Field(None, description="Maximum price per night")
    amenities: List[str] = Field(default=[], description="Required amenities")
    max_results: int = Field(5, ge=1, le=20, description="Maximum number of results")


class Lodging(BaseModel):
    """Lodging information."""
    name: str
    type: str  # hotel, apartment, hostel, etc.
    neighborhood: str
    price_per_night: float
    total_price: float
    rating: float = Field(ge=0, le=5)
    review_count: int
    amenities: List[str]
    cancellation_policy: str
    distance_to_center_km: float
    family_friendly: bool = False
    description: Optional[str] = None


class LodgingSearchOutput(ToolOutput):
    """Output schema for lodging search."""
    lodgings: List[Lodging] = []
    search_params: Optional[Dict[str, Any]] = None


class LodgingTool(BaseTool):
    """Tool for searching lodging options."""
    
    def __init__(self):
        super().__init__(
            name="lodging",
            description="Search for hotels, apartments, and other accommodations",
            timeout_seconds=15
        )
        
        # Sample data for different destinations
        self.destination_data = {
            "kyoto": {
                "neighborhoods": ["Gion", "Arashiyama", "Fushimi", "Central Kyoto", "Higashiyama"],
                "hotel_names": [
                    "Kyoto Traditional Ryokan", "Gion Corner Hotel", "Arashiyama Bamboo Inn",
                    "Fushimi Sake District Hotel", "Kyoto Station Grand", "Philosopher's Path Lodge",
                    "Golden Pavilion Resort", "Kyoto Imperial Garden Hotel"
                ]
            },
            "paris": {
                "neighborhoods": ["Marais", "Saint-Germain", "Montmartre", "Louvre", "Latin Quarter"],
                "hotel_names": [
                    "Hotel des Arts", "Marais Boutique Hotel", "Montmartre View Inn",
                    "Seine Riverside Hotel", "Latin Quarter Charm", "Louvre Palace Hotel",
                    "Saint-Germain Classic", "Champs-Élysées Grand"
                ]
            },
            "tokyo": {
                "neighborhoods": ["Shibuya", "Shinjuku", "Ginza", "Asakusa", "Harajuku"],
                "hotel_names": [
                    "Tokyo Sky Tower Hotel", "Shibuya Crossing Inn", "Ginza Luxury Suites",
                    "Asakusa Traditional Hotel", "Shinjuku Business Hotel", "Harajuku Fashion Hotel",
                    "Tokyo Station Central", "Imperial Palace View"
                ]
            }
        }
        
        self.lodging_types = ["hotel", "apartment", "ryokan", "hostel", "boutique hotel"]
        self.amenities_pool = [
            "wifi", "breakfast", "gym", "spa", "pool", "parking", "restaurant",
            "bar", "concierge", "laundry", "kitchen", "balcony", "air_conditioning",
            "family_rooms", "pet_friendly", "business_center", "airport_shuttle"
        ]
        
        self.cancellation_policies = [
            "Free cancellation until 24h before",
            "Free cancellation until 48h before", 
            "Non-refundable",
            "Flexible cancellation",
            "Moderate cancellation policy"
        ]
    
    def _get_destination_info(self, destination: str) -> Dict[str, Any]:
        """Get destination-specific data."""
        dest_key = destination.lower()
        for key in self.destination_data:
            if key in dest_key:
                return self.destination_data[key]
        
        # Default data for unknown destinations
        return {
            "neighborhoods": ["City Center", "Old Town", "Business District", "Riverside", "Historic Quarter"],
            "hotel_names": [
                "Grand Central Hotel", "City View Inn", "Historic District Lodge",
                "Riverside Suites", "Business Plaza Hotel", "Old Town Charm",
                "Metropolitan Hotel", "Cultural Quarter Inn"
            ]
        }
    
    def _calculate_price(self, lodging_type: str, neighborhood: str, rating: float, guests: int) -> float:
        """Calculate lodging price based on various factors."""
        # Base prices by type
        base_prices = {
            "hostel": 25,
            "apartment": 80,
            "hotel": 120,
            "boutique hotel": 180,
            "ryokan": 200
        }
        
        base_price = base_prices.get(lodging_type, 100)
        
        # Rating multiplier
        rating_multiplier = 0.5 + (rating / 5.0) * 1.5
        
        # Guest multiplier
        guest_multiplier = 1.0 + (guests - 2) * 0.3
        
        # Neighborhood premium (some neighborhoods are more expensive)
        premium_neighborhoods = ["Gion", "Marais", "Ginza", "Louvre", "Shibuya"]
        neighborhood_multiplier = 1.3 if neighborhood in premium_neighborhoods else 1.0
        
        price = base_price * rating_multiplier * guest_multiplier * neighborhood_multiplier
        
        # Add randomness
        price *= random.uniform(0.8, 1.4)
        
        return round(price, 2)
    
    def _generate_amenities(self, lodging_type: str, price_range: str) -> List[str]:
        """Generate realistic amenities based on lodging type and price."""
        base_amenities = ["wifi"]
        
        if lodging_type == "hostel":
            possible = ["shared_kitchen", "laundry", "common_area", "lockers"]
        elif lodging_type == "apartment":
            possible = ["kitchen", "laundry", "balcony", "parking"]
        elif lodging_type in ["hotel", "boutique hotel"]:
            possible = ["breakfast", "restaurant", "concierge", "gym", "spa", "bar", "parking"]
        elif lodging_type == "ryokan":
            possible = ["traditional_bath", "tatami_rooms", "kaiseki_dinner", "garden_view"]
        else:
            possible = self.amenities_pool
        
        # Higher-priced places have more amenities
        if price_range == "luxury":
            num_amenities = random.randint(4, 7)
        elif price_range == "mid":
            num_amenities = random.randint(2, 4)
        else:
            num_amenities = random.randint(1, 3)
        
        selected = random.sample(possible, min(num_amenities, len(possible)))
        return base_amenities + selected
    
    async def _execute(self, input_data: LodgingSearchInput) -> LodgingSearchOutput:
        """Execute lodging search."""
        dest_info = self._get_destination_info(input_data.destination)
        nights = (input_data.check_out - input_data.check_in).days
        
        lodgings = []
        for i in range(input_data.max_results):
            lodging_type = random.choice(self.lodging_types)
            neighborhood = input_data.neighborhood or random.choice(dest_info["neighborhoods"])
            rating = round(random.uniform(3.0, 5.0), 1)
            
            price_per_night = self._calculate_price(lodging_type, neighborhood, rating, input_data.guests)
            
            # Apply max price filter
            if input_data.max_price_per_night and price_per_night > input_data.max_price_per_night:
                price_per_night = input_data.max_price_per_night * random.uniform(0.8, 1.0)
            
            total_price = price_per_night * nights
            
            # Determine price range for amenities
            if price_per_night > 200:
                price_range = "luxury"
            elif price_per_night > 100:
                price_range = "mid"
            else:
                price_range = "budget"
            
            amenities = self._generate_amenities(lodging_type, price_range)
            
            # Check if required amenities are met
            if input_data.amenities:
                missing_amenities = set(input_data.amenities) - set(amenities)
                if missing_amenities:
                    # Add required amenities
                    amenities.extend(list(missing_amenities))
            
            lodging = Lodging(
                name=random.choice(dest_info["hotel_names"]),
                type=lodging_type,
                neighborhood=neighborhood,
                price_per_night=price_per_night,
                total_price=total_price,
                rating=rating,
                review_count=random.randint(50, 2000),
                amenities=amenities,
                cancellation_policy=random.choice(self.cancellation_policies),
                distance_to_center_km=round(random.uniform(0.5, 8.0), 1),
                family_friendly=random.choice([True, False]),
                description=f"A {rating}-star {lodging_type} in {neighborhood} with excellent amenities."
            )
            lodgings.append(lodging)
        
        # Sort by rating and price
        lodgings.sort(key=lambda l: (-l.rating, l.price_per_night))
        
        return LodgingSearchOutput(
            success=True,
            data={"lodgings": [l.model_dump() for l in lodgings]},
            lodgings=lodgings,
            search_params=input_data.model_dump()
        )
    
    def get_input_schema(self) -> type[ToolInput]:
        return LodgingSearchInput
    
    def get_output_schema(self) -> type[ToolOutput]:
        return LodgingSearchOutput

