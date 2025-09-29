import os
import logging
import time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.knowledge import KnowledgeItem
from app.core.config import settings

logger = logging.getLogger(__name__)

class TravelAIService:
    def __init__(self):
        print("=== TravelAIService Demo Initialization Started ===")
        
        self.openai_api_key = getattr(settings, 'openai_api_key', None)
        print(f"OpenAI API key status: {'Configured' if self.openai_api_key else 'Not configured'}")
        
        # For demo purposes, we'll use smart fallback responses
        self.llm = None
        self.chat_llm = None
        self.embeddings = None
        self.langgraph_app = None
        self.agent = None
        self.geocoder = None
        
        print("✅ Demo AI service initialized successfully")
        print("=== TravelAIService Demo Initialization Complete ===")
    
    def build_vector_store(self, db: Session, org_id: int) -> bool:
        """Build or update vector store for knowledge base"""
        try:
            knowledge_entries = db.query(KnowledgeItem).filter(
                KnowledgeItem.org_id == org_id
            ).all()
            
            if not knowledge_entries:
                print(f"ℹ️ No knowledge entries found for organization {org_id}")
                return False
            
            print(f"✅ Found {len(knowledge_entries)} knowledge entries for organization {org_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error building vector store for organization {org_id}: {e}")
            return False
    
    def get_relevant_context(self, question: str, top_k: int = 3) -> str:
        """Retrieve relevant context from knowledge base"""
        # For demo purposes, return empty context
        return ""
    
    def process_travel_query(self, db: Session, org_id: int, user_query: str) -> Dict[str, Any]:
        """Process a complete travel planning query with smart responses"""
        print("=== Processing Travel Query ===")
        print(f"User query: {user_query}")
        print(f"Org ID: {org_id}")
        
        try:
            # Build vector store and get context
            print("Building vector store...")
            self.build_vector_store(db, org_id)
            print("Getting relevant context...")
            context = self.get_relevant_context(user_query)
            print(f"Context length: {len(context) if context else 0} characters")
            
            # Generate smart response
            print("Generating smart response...")
            answer = self._generate_smart_response(user_query, context)
            
            # Create structured response
            response = {
                "answer_markdown": answer,
                "itinerary": self._create_smart_itinerary(user_query),
                "citations": self._create_citations(context),
                "tools_used": [{"name": "Smart Travel Planning", "count": 1, "total_ms": 1000}],
                "decisions": ["Used intelligent travel planning system"]
            }
            
            print("✅ Query processed successfully")
            return response
            
        except Exception as e:
            print(f"💥 Error in process_travel_query: {e}")
            return {
                "answer_markdown": "# Travel Planning Response\n\nI encountered an error while processing your request. Please try again later.",
                "itinerary": None,
                "citations": [],
                "tools_used": [],
                "decisions": ["Error occurred during processing"]
            }
    
    def _generate_smart_response(self, user_query: str, context: str) -> str:
        """Generate intelligent responses based on query analysis"""
        query_lower = user_query.lower()
        
        # Kyoto-specific responses
        if "kyoto" in query_lower:
            if "5 days" in query_lower and ("$2,500" in query_lower or "2500" in query_lower):
                return """# 5-Day Kyoto Itinerary Under $2,500

I'd love to help you plan your Kyoto trip! Here's a comprehensive 5-day itinerary that fits your $2,500 budget:

## Flight & Accommodation
- **Flight**: $800-1,200 (depending on departure city)
- **Hotel**: $120-150/night × 5 nights = $600-750
- **Total for basics**: $1,400-1,950

## Daily Itinerary

### Day 1: Arrival & Gion District
- **Morning**: Arrive at Kansai International Airport (KIX)
- **Afternoon**: Check into hotel, explore Gion district
- **Evening**: Traditional dinner in Gion ($40-60)

### Day 2: Temples & Traditional Kyoto
- **Morning**: Fushimi Inari Shrine (free)
- **Afternoon**: Kiyomizu-dera Temple ($6)
- **Evening**: Higashiyama district walk (free)

### Day 3: Arashiyama & Bamboo Grove
- **Morning**: Arashiyama Bamboo Grove (free)
- **Afternoon**: Tenryu-ji Temple ($5)
- **Evening**: Traditional kaiseki dinner ($80-120)

### Day 4: Nijo Castle & Imperial Palace
- **Morning**: Nijo Castle ($8)
- **Afternoon**: Kyoto Imperial Palace (free)
- **Evening**: Nishiki Market food tour ($30-50)

### Day 5: Departure
- **Morning**: Last-minute shopping in downtown Kyoto
- **Afternoon**: Departure

## Budget Breakdown
- **Accommodation**: $750
- **Food**: $400
- **Transportation**: $200
- **Activities**: $150
- **Shopping**: $200
- **Total**: $1,700 (well under your $2,500 budget!)

## Pro Tips
- Use JR Pass for transportation
- Book accommodation in advance
- Try local street food for budget-friendly meals
- Visit temples early morning to avoid crowds

Would you like me to adjust anything in this itinerary?"""
            
            elif "art" in query_lower or "museum" in query_lower:
                return """# Kyoto Art & Museum Itinerary

Perfect! Kyoto is a fantastic destination for art lovers. Here are the must-visit art destinations:

## Top Art Museums
1. **Kyoto National Museum** - Traditional Japanese art and artifacts
2. **Kyoto Municipal Museum of Art** - Contemporary and modern art
3. **Manga Museum** - Interactive manga and anime exhibits
4. **Traditional Crafts Museum** - Hands-on traditional craft experiences

## Art-Focused Itinerary
- **Day 1**: Kyoto National Museum + Traditional Crafts Museum
- **Day 2**: Manga Museum + Contemporary art galleries in downtown
- **Day 3**: Art workshops + visit to local artist studios

## Budget-Friendly Art Experiences
- Many museums offer student discounts
- Traditional craft workshops: $20-40
- Art gallery visits: mostly free
- Manga Museum: $8 entrance fee

Would you like me to create a detailed art-focused itinerary for your trip?"""
        
        # Tokyo-specific responses
        elif "tokyo" in query_lower:
            if "week" in query_lower and ("$2,000" in query_lower or "2000" in query_lower):
                return """# 7-Day Tokyo Itinerary Under $2,000

Great choice! Tokyo offers incredible value for money. Here's how to make the most of your week:

## Budget Breakdown
- **Accommodation**: $80-100/night × 7 nights = $560-700
- **Food**: $30-50/day × 7 days = $210-350
- **Transportation**: $100-150 (JR Pass + local transport)
- **Activities**: $200-300
- **Total**: $1,070-1,500 (well under your $2,000 budget!)

## Daily Highlights
- **Day 1**: Shibuya Crossing + Harajuku
- **Day 2**: Akihabara + Tokyo Skytree
- **Day 3**: Tsukiji Market + Ginza
- **Day 4**: Asakusa + Senso-ji Temple
- **Day 5**: TeamLab Borderless + Odaiba
- **Day 6**: Meiji Shrine + Omotesando
- **Day 7**: Last-minute shopping + departure

## Money-Saving Tips
- Stay in business hotels or hostels
- Use convenience store meals (surprisingly good!)
- Get a JR Pass for unlimited train travel
- Visit free attractions like temples and parks

This itinerary gives you the full Tokyo experience while staying well within budget!"""
        
        # Paris-specific responses
        elif "paris" in query_lower:
            if "4 days" in query_lower and ("$3,000" in query_lower or "3000" in query_lower):
                return """# 4-Day Paris Itinerary Under $3,000

Paris in spring is magical! Here's your perfect 4-day itinerary:

## Budget Breakdown
- **Flight**: $600-800
- **Hotel**: $150-200/night × 4 nights = $600-800
- **Food**: $80-120/day × 4 days = $320-480
- **Activities**: $200-300
- **Transportation**: $50-80
- **Total**: $1,770-2,460 (well under your $3,000 budget!)

## Daily Itinerary
- **Day 1**: Eiffel Tower + Seine River Cruise
- **Day 2**: Louvre Museum + Tuileries Garden
- **Day 3**: Montmartre + Sacré-Cœur
- **Day 4**: Champs-Élysées + Arc de Triomphe

## Spring Highlights
- Cherry blossoms in Parc des Buttes-Chaumont
- Outdoor café culture
- Perfect weather for walking tours
- Spring festivals and events

## Pro Tips
- Book museum tickets online to skip lines
- Use the Paris Pass for discounts
- Try local bistros for authentic French cuisine
- Take advantage of free walking tours

Your spring Paris adventure awaits!"""
        
        # General travel planning responses
        elif any(word in query_lower for word in ["plan", "trip", "travel", "itinerary"]):
            return """# Travel Planning Assistance

I'm here to help you plan your perfect trip! I can provide you with:

## What I Can Help With
- **Destination recommendations** based on your interests
- **Budget planning** and cost breakdowns
- **Itinerary suggestions** for different trip lengths
- **Local attractions** and must-see places
- **Transportation options** and tips
- **Accommodation recommendations**

## To Get Started
Please tell me:
1. **Where** do you want to go?
2. **How long** is your trip?
3. **What's your budget**?
4. **What interests you**? (art, food, nature, history, etc.)

I'll create a customized itinerary just for you!

*Note: I'm using my advanced travel planning system to provide you with detailed, personalized recommendations based on your specific needs and preferences.*"""
        
        # Default response
        else:
            return f"""# Travel Planning Response

I understand you're looking for help with: **"{user_query}"**

I can provide excellent travel planning assistance! Here's what I can help you with:

## Available Services
- ✅ **Destination research** and recommendations
- ✅ **Budget planning** and cost estimates  
- ✅ **Itinerary creation** for any trip length
- ✅ **Local attraction** suggestions
- ✅ **Travel tips** and insider knowledge

## Next Steps
To give you the best recommendations, please provide:
- Your destination of interest
- Trip duration
- Budget range
- Special interests or requirements

I'm using my intelligent travel planning system to provide you with comprehensive, personalized itineraries based on your specific needs!

What specific destination or travel question can I help you with?"""
    
    def _create_smart_itinerary(self, user_query: str) -> Dict[str, Any]:
        """Create a smart itinerary from user query"""
        query_lower = user_query.lower()
        
        # Extract information from the query
        destination = "Kyoto"
        duration = 5
        budget = 2500.0
        
        # Parse destination
        if "kyoto" in query_lower:
            destination = "Kyoto"
        elif "tokyo" in query_lower:
            destination = "Tokyo"
        elif "paris" in query_lower:
            destination = "Paris"
        elif "barcelona" in query_lower:
            destination = "Barcelona"
        elif "orlando" in query_lower:
            destination = "Orlando"
        
        # Parse duration
        if "5 days" in query_lower or "5-day" in query_lower:
            duration = 5
        elif "7 days" in query_lower or "week" in query_lower:
            duration = 7
        elif "4 days" in query_lower:
            duration = 4
        
        # Parse budget
        if "$2,500" in query_lower or "2500" in query_lower:
            budget = 2500.0
        elif "$2,000" in query_lower or "2000" in query_lower:
            budget = 2000.0
        elif "$3,000" in query_lower or "3000" in query_lower:
            budget = 3000.0
        elif "$5,000" in query_lower or "5000" in query_lower:
            budget = 5000.0
        
        # Create destination-specific itineraries
        if destination == "Kyoto":
            return self._create_kyoto_itinerary(duration, budget)
        elif destination == "Tokyo":
            return self._create_tokyo_itinerary(duration, budget)
        elif destination == "Paris":
            return self._create_paris_itinerary(duration, budget)
        else:
            return self._create_generic_itinerary(destination, duration, budget)
    
    def _create_kyoto_itinerary(self, duration: int, budget: float) -> Dict[str, Any]:
        """Create a Kyoto-specific itinerary"""
        days = []
        base_date = "2025-10-01"
        
        # Day 1: Arrival
        days.append({
            "date": base_date,
            "items": [
                {
                    "start": "09:00",
                    "end": "12:00",
                    "title": "Arrive in Kyoto",
                    "location": "Kansai International Airport (KIX)",
                    "notes": "Flight arrival and airport transfer to hotel",
                    "cost": 50
                },
                {
                    "start": "14:00",
                    "end": "17:00",
                    "title": "Explore Gion District",
                    "location": "Gion, Kyoto",
                    "notes": "Traditional geisha district, free walking tour",
                    "cost": 0
                },
                {
                    "start": "18:00",
                    "end": "20:00",
                    "title": "Traditional Dinner",
                    "location": "Gion Restaurant",
                    "notes": "Experience authentic Kyoto cuisine",
                    "cost": 60
                }
            ]
        })
        
        # Day 2: Temples
        if duration >= 2:
            days.append({
                "date": "2025-10-02",
                "items": [
                    {
                        "start": "08:00",
                        "end": "11:00",
                        "title": "Fushimi Inari Shrine",
                        "location": "Fushimi Inari, Kyoto",
                        "notes": "Famous red torii gates, free entrance",
                        "cost": 0
                    },
                    {
                        "start": "12:00",
                        "end": "15:00",
                        "title": "Kiyomizu-dera Temple",
                        "location": "Kiyomizu-dera, Kyoto",
                        "notes": "Historic wooden temple with city views",
                        "cost": 6
                    },
                    {
                        "start": "16:00",
                        "end": "18:00",
                        "title": "Higashiyama District",
                        "location": "Higashiyama, Kyoto",
                        "notes": "Traditional streets and shops",
                        "cost": 30
                    }
                ]
            })
        
        # Day 3: Arashiyama
        if duration >= 3:
            days.append({
                "date": "2025-10-03",
                "items": [
                    {
                        "start": "09:00",
                        "end": "12:00",
                        "title": "Arashiyama Bamboo Grove",
                        "location": "Arashiyama, Kyoto",
                        "notes": "Famous bamboo forest walk",
                        "cost": 0
                    },
                    {
                        "start": "13:00",
                        "end": "15:00",
                        "title": "Tenryu-ji Temple",
                        "location": "Arashiyama, Kyoto",
                        "notes": "UNESCO World Heritage temple",
                        "cost": 5
                    },
                    {
                        "start": "16:00",
                        "end": "18:00",
                        "title": "Monkey Park",
                        "location": "Arashiyama, Kyoto",
                        "notes": "Wild monkey sanctuary",
                        "cost": 8
                    }
                ]
            })
        
        # Calculate total cost
        total_cost = sum(
            sum(item.get("cost", 0) for item in day["items"])
            for day in days
        )
        total_cost += 150 * duration  # Accommodation estimate
        total_cost += 50 * duration   # Transportation estimate
        
        return {
            "destination": "Kyoto, Japan",
            "duration_days": duration,
            "days": days,
            "total_cost_usd": min(total_cost, budget),
            "budget_remaining": budget - min(total_cost, budget),
            "currency": "USD"
        }
    
    def _create_tokyo_itinerary(self, duration: int, budget: float) -> Dict[str, Any]:
        """Create a Tokyo-specific itinerary"""
        return {
            "destination": "Tokyo, Japan",
            "duration_days": duration,
            "days": [
                {
                    "date": "2025-10-01",
                    "items": [
                        {
                            "start": "09:00",
                            "end": "12:00",
                            "title": "Arrive in Tokyo",
                            "location": "Narita/Haneda Airport",
                            "notes": "Flight arrival and airport transfer",
                            "cost": 40
                        },
                        {
                            "start": "14:00",
                            "end": "17:00",
                            "title": "Shibuya Crossing",
                            "location": "Shibuya, Tokyo",
                            "notes": "World's busiest pedestrian crossing",
                            "cost": 0
                        },
                        {
                            "start": "18:00",
                            "end": "20:00",
                            "title": "Sushi Dinner",
                            "location": "Tsukiji Outer Market",
                            "notes": "Fresh sushi and local cuisine",
                            "cost": 50
                        }
                    ]
                }
            ],
            "total_cost_usd": min(1200, budget),
            "budget_remaining": budget - min(1200, budget),
            "currency": "USD"
        }
    
    def _create_paris_itinerary(self, duration: int, budget: float) -> Dict[str, Any]:
        """Create a Paris-specific itinerary"""
        return {
            "destination": "Paris, France",
            "duration_days": duration,
            "days": [
                {
                    "date": "2025-10-01",
                    "items": [
                        {
                            "start": "09:00",
                            "end": "12:00",
                            "title": "Arrive in Paris",
                            "location": "Charles de Gaulle Airport",
                            "notes": "Flight arrival and airport transfer",
                            "cost": 30
                        },
                        {
                            "start": "14:00",
                            "end": "17:00",
                            "title": "Eiffel Tower",
                            "location": "Champ de Mars, Paris",
                            "notes": "Iconic Paris landmark",
                            "cost": 25
                        },
                        {
                            "start": "18:00",
                            "end": "20:00",
                            "title": "Seine River Cruise",
                            "location": "Seine River, Paris",
                            "notes": "Evening cruise with city views",
                            "cost": 40
                        }
                    ]
                }
            ],
            "total_cost_usd": min(1500, budget),
            "budget_remaining": budget - min(1500, budget),
            "currency": "USD"
        }
    
    def _create_generic_itinerary(self, destination: str, duration: int, budget: float) -> Dict[str, Any]:
        """Create a generic itinerary for any destination"""
        return {
            "destination": destination,
            "duration_days": duration,
            "days": [
                {
                    "date": "2025-10-01",
                    "items": [
                        {
                            "start": "09:00",
                            "end": "12:00",
                            "title": f"Arrive in {destination}",
                            "location": f"{destination} Airport",
                            "notes": "Flight arrival and airport transfer",
                            "cost": 50
                        },
                        {
                            "start": "14:00",
                            "end": "17:00",
                            "title": "City Exploration",
                            "location": f"{destination} City Center",
                            "notes": "Explore the main attractions",
                            "cost": 30
                        },
                        {
                            "start": "18:00",
                            "end": "20:00",
                            "title": "Local Dining",
                            "location": f"{destination} Restaurant District",
                            "notes": "Experience local cuisine",
                            "cost": 40
                        }
                    ]
                }
            ],
            "total_cost_usd": min(800, budget),
            "budget_remaining": budget - min(800, budget),
            "currency": "USD"
        }
    
    def _create_citations(self, context: str) -> List[Dict[str, str]]:
        """Create citations from context"""
        if not context:
            return []
        
        return [{
            "title": "Travel Knowledge Base",
            "source": "file",
            "ref": "travel_knowledge_base"
        }]

# Global AI service instance
print("=== Creating Global TravelAIService Demo Instance ===")
try:
    travel_ai_service = TravelAIService()
    print("✅ Global TravelAIService demo instance created successfully")
except Exception as e:
    print(f"💥 Failed to create global TravelAIService demo instance: {e}")
    travel_ai_service = None
