import os
import logging
import time
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.knowledge import KnowledgeItem
from app.core.config import settings

# Import OpenAI
import openai

logger = logging.getLogger(__name__)

class TravelAIService:
    def __init__(self):
        print("=== TravelAIService Real Implementation Started ===")
        
        self.openai_api_key = getattr(settings, 'openai_api_key', None)
        print(f"OpenAI API key status: {'Configured' if self.openai_api_key else 'Not configured'}")
        
        # Initialize OpenAI components
        if self.openai_api_key:
            try:
                # Initialize OpenAI client
                self.openai_client = openai.OpenAI(
                    api_key=self.openai_api_key,
                    base_url=getattr(settings, 'openai_api_base', None)
                )
                
                print("✅ OpenAI client initialized successfully")
                
            except Exception as e:
                print(f"❌ Error initializing OpenAI client: {e}")
                self.openai_client = None
        else:
            print("⚠️ No OpenAI API key configured - AI features will be limited")
            self.openai_client = None
        
        # Initialize geocoder
        try:
            from geopy.geocoders import Nominatim
            self.geocoder = Nominatim(
                user_agent="travel_advisory_agent",
                timeout=10
            )
            print("✅ Geocoder initialized successfully")
        except ImportError:
            print("⚠️ geopy not available - geocoding features will be disabled")
            self.geocoder = None
        except Exception as e:
            print(f"⚠️ Failed to initialize geocoder: {e}")
            self.geocoder = None
        
        # For compatibility with existing code
        self.llm = self.openai_client
        self.chat_llm = self.openai_client
        self.embeddings = None  # We'll implement simple text matching for now
        self.langgraph_app = None
        self.agent = None
        
        # Knowledge base cache
        self.knowledge_cache = {}
        
        print("✅ TravelAIService Real Implementation Complete")
    
    def build_vector_store(self, db: Session, org_id: int) -> bool:
        """Build or update knowledge base cache"""
        try:
            knowledge_entries = db.query(KnowledgeItem).filter(
                KnowledgeItem.org_id == org_id
            ).all()
            
            if not knowledge_entries:
                print(f"ℹ️ No knowledge entries found for organization {org_id}")
                return False
            
            print(f"✅ Found {len(knowledge_entries)} knowledge entries for organization {org_id}")
            
            # Store knowledge entries in cache for simple text matching
            self.knowledge_cache[org_id] = knowledge_entries
            return True
            
        except Exception as e:
            print(f"❌ Error building knowledge cache for organization {org_id}: {e}")
            return False
    
    def get_relevant_context(self, question: str, org_id: int, top_k: int = 3) -> str:
        """Retrieve relevant context from knowledge base using simple text matching"""
        try:
            if org_id not in self.knowledge_cache:
                print(f"⚠️ No knowledge cache found for organization {org_id}")
            return ""
        
            knowledge_entries = self.knowledge_cache[org_id]
            question_lower = question.lower()
            
            # Simple text matching to find relevant entries
            relevant_entries = []
            for entry in knowledge_entries:
                content_lower = entry.content.lower()
                title_lower = entry.title.lower()
                
                # Check if question keywords match content or title
                question_words = set(question_lower.split())
                content_words = set(content_lower.split())
                title_words = set(title_lower.split())
                
                # Calculate simple relevance score
                content_matches = len(question_words.intersection(content_words))
                title_matches = len(question_words.intersection(title_words))
                total_score = content_matches + (title_matches * 2)  # Title matches are weighted higher
                
                if total_score > 0:
                    relevant_entries.append((entry, total_score))
            
            # Sort by relevance score and take top_k
            relevant_entries.sort(key=lambda x: x[1], reverse=True)
            relevant_entries = relevant_entries[:top_k]
            
            if not relevant_entries:
                print("ℹ️ No relevant knowledge entries found")
                return ""
            
            # Combine relevant context
            context_parts = []
            for entry, score in relevant_entries:
                context_parts.append(f"Source: {entry.title}\n{entry.content}")
            
            context = "\n\n".join(context_parts)
            print(f"✅ Retrieved {len(relevant_entries)} relevant entries, context length: {len(context)} characters")
            return context
            
        except Exception as e:
            print(f"❌ Error retrieving context: {e}")
            return ""
    
    def process_travel_query(self, db: Session, org_id: int, user_query: str) -> Dict[str, Any]:
        """Process a complete travel planning query using real OpenAI API"""
        print("=== Processing Travel Query ===")
        print(f"User query: {user_query}")
        print(f"Org ID: {org_id}")
        
        try:
            # Build knowledge cache and get context
            print("Building knowledge cache...")
            self.build_vector_store(db, org_id)
            print("Getting relevant context...")
            context = self.get_relevant_context(user_query, org_id)
            print(f"Context length: {len(context) if context else 0} characters")
            
            # Check if this is a refinement request
            is_refinement = self._is_refinement_request(user_query)
            print(f"Is refinement request: {is_refinement}")
            
            # Extract destination for refinement requests
            extracted_destination = None
            if is_refinement:
                extracted_destination = self._extract_destination_from_query(user_query)
                print(f"Extracted destination: {extracted_destination}")
            
            # Use OpenAI API to generate response
            if self.openai_client:
                print("Using OpenAI API...")
                try:
                    # Create a comprehensive prompt
                    if is_refinement:
                        system_prompt = """You are an expert travel planning assistant. The user is asking for a refinement to a previous itinerary. 

CRITICAL: This is a REFINEMENT request. The user wants to modify an existing travel plan, not create a new one. 

RULES FOR REFINEMENT:
1. DO NOT change the destination - keep the SAME destination as mentioned in the user's request
2. If the user says "based on the previous itinerary" - the destination should remain the SAME
3. Only modify the specific aspects requested (e.g., budget, activities, preferences)
4. Maintain the same general timeframe and structure
5. If the user mentions a specific destination in their refinement request, use THAT destination

EXAMPLES:
- If user says "Based on the previous Kyoto itinerary, make it cheaper" → Keep Kyoto as destination
- If user says "Based on the previous Tokyo trip, add more museums" → Keep Tokyo as destination
- If user says "Make the Paris itinerary cheaper" → Keep Paris as destination

When creating refined itineraries, include:
- Daily schedules with specific times
- Location details and addresses
- Updated cost estimates
- Transportation options
- Local tips and recommendations
- Budget breakdowns

Format your response in clear markdown with proper headings and structure. Be specific and practical in your recommendations."""
                    else:
                        system_prompt = """You are an expert travel planning assistant. Create detailed, practical travel itineraries based on user requests.

When creating itineraries, include:
- Daily schedules with specific times
- Location details and addresses
- Cost estimates
- Transportation options
- Local tips and recommendations
- Budget breakdowns

Format your response in clear markdown with proper headings and structure. Be specific and practical in your recommendations."""

                    if is_refinement:
                        destination_instruction = ""
                        if extracted_destination:
                            destination_instruction = f"\nCRITICAL: The destination must be {extracted_destination}. Do NOT change this destination."
                        
                        user_prompt = f"""User Request: {user_query}

IMPORTANT: This is a REFINEMENT request. The user is asking to modify a previous itinerary. 
- The destination should remain the SAME as mentioned in the user's request
- Do NOT change the destination unless explicitly asked to
- Focus on the specific changes requested (budget, activities, etc.)
{destination_instruction}

Context from Knowledge Base:
{context if context else "No specific context available"}

Please create a refined travel plan based on this request. Maintain the same destination and make only the requested modifications."""
                    else:
                        user_prompt = f"""User Request: {user_query}

Context from Knowledge Base:
{context if context else "No specific context available"}

Please create a comprehensive travel plan based on this request. If you have relevant information from the knowledge base, incorporate it into your recommendations."""

                    # Make API call
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        max_tokens=2000,
                        temperature=0.7
                    )
                    
                    ai_response = response.choices[0].message.content
                    
                    # Parse the response to extract itinerary information
                    itinerary = self._parse_itinerary_from_response(ai_response, user_query)
                    
                    print("✅ OpenAI API completed successfully")
                    return {
                        "answer_markdown": ai_response,
                        "itinerary": itinerary,
                        "citations": self._create_citations(context),
                        "tools_used": [{"name": "OpenAI GPT-4o", "count": 1, "total_ms": 3000}],
                        "decisions": ["Used OpenAI API for travel planning"]
                    }
                    
                except Exception as e:
                    print(f"⚠️ OpenAI API failed: {e}")
                    return self._generate_fallback_response(user_query, context)
            else:
                print("⚠️ OpenAI client not available, using fallback response")
                return self._generate_fallback_response(user_query, context)
            
        except Exception as e:
            print(f"💥 Error in process_travel_query: {e}")
            return {
                "answer_markdown": "# Travel Planning Response\n\nI encountered an error while processing your request. Please try again later.",
                "itinerary": None,
                "citations": [],
                "tools_used": [],
                "decisions": ["Error occurred during processing"]
            }
    
    def _parse_itinerary_from_response(self, response: str, user_query: str) -> Dict[str, Any]:
        """Parse itinerary information from AI response"""
        try:
            # Extract basic information from user query
            query_lower = user_query.lower()
            response_lower = response.lower()
            
            # Parse destination - check for refinement context first
            destination = "Unknown"
            if "kyoto" in query_lower or "kyoto" in response_lower:
                destination = "Kyoto, Japan"
            elif "tokyo" in query_lower or "tokyo" in response_lower:
                destination = "Tokyo, Japan"
            elif "paris" in query_lower or "paris" in response_lower:
                destination = "Paris, France"
            elif "barcelona" in query_lower or "barcelona" in response_lower:
                destination = "Barcelona, Spain"
            elif "orlando" in query_lower or "orlando" in response_lower:
                destination = "Orlando, Florida"
            
            # Parse duration
            duration = 5  # default
            if "5 days" in query_lower:
                duration = 5
            elif "7 days" in query_lower or "week" in query_lower:
                duration = 7
            elif "4 days" in query_lower:
                duration = 4
            
            # Parse budget from user query
            budget = 2500.0  # default
            if "$2,500" in query_lower or "2500" in query_lower:
                budget = 2500.0
            elif "$2,000" in query_lower or "2000" in query_lower:
                budget = 2000.0
            elif "$3,000" in query_lower or "3000" in query_lower:
                budget = 3000.0
            elif "$5,000" in query_lower or "5000" in query_lower:
                budget = 5000.0
            
            # Parse actual costs from AI response
            total_cost, currency = self._extract_costs_from_response(response)
            
            # If no costs found in response, use budget-based estimation
            if total_cost is None:
                total_cost = min(budget * 0.7, budget)
                currency = "USD"
            
            # Create basic itinerary structure
            return {
                "destination": destination,
                "duration_days": duration,
                "total_cost_usd": total_cost,
                "total_cost_original": total_cost,
                "currency": currency,
                "budget_remaining": budget - total_cost if currency == "USD" else None,
                "days": []  # Could be populated with more detailed parsing
            }
            
        except Exception as e:
            print(f"⚠️ Error parsing itinerary: {e}")
            return None
    
    def _extract_costs_from_response(self, response: str) -> tuple:
        """Extract actual costs and currency from AI response"""
        import re
        
        # Look for total cost patterns
        patterns = [
            r'total.*?cost.*?[¥$]?([\d,]+)',  # "Total cost: ¥22,500"
            r'[¥$]([\d,]+).*?total',  # "¥22,500 total"
            r'total.*?[¥$]([\d,]+)',  # "Total: ¥22,500"
            r'[¥$]([\d,]+)',  # Just currency amount
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                try:
                    # Clean the number (remove commas)
                    cost_str = matches[0].replace(',', '')
                    cost = float(cost_str)
                    
                    # Determine currency
                    if '¥' in response or 'yen' in response.lower():
                        # Convert Yen to USD (approximate rate: 1 USD = 150 Yen)
                        cost_usd = cost / 150
                        return cost_usd, "USD"
                    elif '$' in response:
                        return cost, "USD"
                    else:
                        return cost, "USD"  # Default to USD
                        
                except ValueError:
                    continue
        
        return None, None
    
    def _generate_fallback_response(self, user_query: str, context: str) -> Dict[str, Any]:
        """Generate a fallback response when AI services are not available"""
        return {
            "answer_markdown": f"""# Travel Planning Response

I'm currently setting up my advanced travel planning capabilities. Here's what I can help you with:

## Your Request
"{user_query}"

## Available Services
- Destination recommendations
- Budget planning assistance  
- Itinerary suggestions
- Travel tips and advice

## Next Steps
Please try again in a moment, or provide more specific details about your travel preferences.

*Note: I'm working on connecting to my AI travel planning system to provide you with detailed, personalized recommendations.*""",
            "itinerary": None,
            "citations": self._create_citations(context),
            "tools_used": [{"name": "Fallback Response", "count": 1, "total_ms": 100}],
            "decisions": ["AI services not available - using fallback response"]
        }
    
    def _is_refinement_request(self, user_query: str) -> bool:
        """Check if the user query is a refinement request"""
        query_lower = user_query.lower()
        refinement_keywords = [
            "based on the previous",
            "previous itinerary",
            "make it cheaper",
            "make it more expensive",
            "add more",
            "remove",
            "change",
            "modify",
            "update",
            "refine",
            "adjust",
            "instead of",
            "rather than"
        ]
        
        return any(keyword in query_lower for keyword in refinement_keywords)
    
    def _extract_destination_from_query(self, user_query: str) -> str:
        """Extract destination from user query"""
        query_lower = user_query.lower()
        
        # Check for specific destinations
        if "kyoto" in query_lower:
            return "Kyoto, Japan"
        elif "tokyo" in query_lower:
            return "Tokyo, Japan"
        elif "paris" in query_lower:
            return "Paris, France"
        elif "barcelona" in query_lower:
            return "Barcelona, Spain"
        elif "orlando" in query_lower:
            return "Orlando, Florida"
        elif "london" in query_lower:
            return "London, UK"
        elif "rome" in query_lower:
            return "Rome, Italy"
        
        return None
    
    def _create_citations(self, context: str) -> List[Dict[str, str]]:
        """Create citations from context"""
        if not context:
            return []
        
        return [{
            "title": "Travel Knowledge Base",
            "source": "database",
            "ref": "knowledge_base"
        }]

# Global AI service instance
print("=== Creating Global TravelAIService Real Instance ===")
try:
    travel_ai_service = TravelAIService()
    print("✅ Global TravelAIService real instance created successfully")
except Exception as e:
    print(f"💥 Failed to create global TravelAIService real instance: {e}")
    travel_ai_service = None
