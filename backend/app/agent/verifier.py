from typing import List, Dict, Any, Optional
from app.agent.state import AgentState, Constraint, ConstraintType, Violation, PlanStep, BudgetCounter
from datetime import datetime, date, timedelta


class Verifier:
    """Verifies the current plan or partial plan against defined constraints."""
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        constraints: List[Constraint] = state["constraints"]
        plan: List[PlanStep] = state["plan"]
        working_set: Dict[str, Any] = state["working_set"]
        violations: List[Violation] = []
        budget_counters: BudgetCounter = state["budget_counters"]
        
        # 1. Budget Check
        self._check_budget(constraints, working_set, violations, budget_counters)
        
        # 2. Feasibility Check (e.g., flight transfers, overnight flights)
        self._check_feasibility(constraints, working_set, violations)
        
        # 3. Weather Sensitivity Check (requires weather tool output)
        self._check_weather_sensitivity(constraints, working_set, violations)
        
        # 4. Preference Fit Check
        self._check_preferences(constraints, working_set, violations)
        
        return {
            "violations": violations,
            "budget_counters": budget_counters, # Update budget counters
            "working_set": working_set # Pass through working set
        }
    
    def _check_budget(self, constraints: List[Constraint], working_set: Dict[str, Any], 
                      violations: List[Violation], budget_counters: BudgetCounter):
        """Checks if the total cost exceeds the budget limit."""
        budget_limit = next((c.value for c in constraints if c.type == ConstraintType.BUDGET), None)
        if not budget_limit:
            return # No budget constraint
        
        # Aggregate costs from working_set (example: flights, lodging)
        total_cost = 0.0
        
        # Flights cost
        for key, value in working_set.items():
            if "flights" in key and "output" in key and value and "flights" in value:
                for flight in value["flights"]:
                    total_cost += flight["price_usd"]
        budget_counters.flights = total_cost # This is a simplification, should be more granular

        # Lodging cost
        lodging_cost = 0.0
        for key, value in working_set.items():
            if "lodging" in key and "output" in key and value and "lodgings" in value:
                for lodging in value["lodgings"]:
                    lodging_cost += lodging["total_price"]
        budget_counters.lodging = lodging_cost
        
        # TODO: Add other costs (events, transit, daily spending)
        budget_counters.total = budget_counters.flights + budget_counters.lodging + budget_counters.activities + budget_counters.transport + budget_counters.food

        if budget_counters.total > budget_limit:
            violations.append(Violation(
                constraint_type=ConstraintType.BUDGET,
                description=f"Total estimated cost ({budget_counters.total:.2f} USD) exceeds budget limit ({budget_limit:.2f} USD).",
                severity="critical",
                suggested_fix="Consider cheaper flights, lodging, or fewer activities."
            ))
    
    def _check_feasibility(self, constraints: List[Constraint], working_set: Dict[str, Any], violations: List[Violation]):
        """Checks for feasibility issues like overnight flights or transfer times."""
        avoid_overnight = any(c.value == "Avoid overnight flights" for c in constraints if c.type == ConstraintType.PREFERENCES)
        
        # Check for overnight flights
        if avoid_overnight:
            for key, value in working_set.items():
                if "flights" in key and "output" in key and value and "flights" in value:
                    for flight in value["flights"]:
                        departure = datetime.fromisoformat(flight["departure_time"])
                        arrival = datetime.fromisoformat(flight["arrival_time"])
                        if arrival.date() > departure.date() + timedelta(days=1): # Simplified check for overnight
                            violations.append(Violation(
                                constraint_type=ConstraintType.PREFERENCES,
                                description=f"Flight {flight['flight_number']} is an overnight flight, which user prefers to avoid.",
                                severity="warning",
                                suggested_fix="Search for alternative flights or adjust travel dates."
                            ))
        
        # TODO: Add transfer buffer checks, opening hours alignment for events
    
    def _check_weather_sensitivity(self, constraints: List[Constraint], working_set: Dict[str, Any], violations: List[Violation]):
        """Checks if weather conditions impact planned activities and suggests swaps."""
        # This check would typically compare planned outdoor activities with weather forecasts.
        # For MVP, we'll just check if there's rain and suggest alternatives.
        
        weather_forecast = None
        for key, value in working_set.items():
            if "weather" in key and "output" in key and value and "daily_forecast" in value:
                weather_forecast = value["daily_forecast"]
                break
        
        if weather_forecast:
            for day_forecast in weather_forecast:
                if day_forecast["is_rainy"]:
                    violations.append(Violation(
                        constraint_type=ConstraintType.WEATHER,
                        description=f"Rain expected on {day_forecast['date']}. Consider swapping outdoor activities for indoor ones.",
                        severity="info",
                        suggested_fix="Identify outdoor activities on this day and find indoor alternatives."
                    ))
    
    def _check_preferences(self, constraints: List[Constraint], working_set: Dict[str, Any], violations: List[Violation]):
        """Checks if user preferences are respected."""
        preferences = [c.value for c in constraints if c.type == ConstraintType.PREFERENCES]
        
        # Example: Check for kid-friendly activities if preferred
        kid_friendly_pref = any("toddler-friendly" in p.lower() or "kid-friendly" in p.lower() for p in preferences)
        
        if kid_friendly_pref:
            found_kid_friendly = False
            for key, value in working_set.items():
                if "events" in key and "output" in key and value and "events" in value:
                    for event in value["events"]:
                        if event["kid_friendly"]:
                            found_kid_friendly = True
                            break
                if found_kid_friendly: break
            
            if not found_kid_friendly:
                violations.append(Violation(
                    constraint_type=ConstraintType.PREFERENCES,
                    description="No kid-friendly activities found, but user prefers them.",
                    severity="warning",
                    suggested_fix="Search for kid-friendly events or attractions."
                ))
        
        # Example: Check for museum preference
        museum_pref = any("museum" in p.lower() for p in preferences)
        if museum_pref:
            found_museum = False
            for key, value in working_set.items():
                if "events" in key and "output" in key and value and "events" in value:
                    for event in value["events"]:
                        if "museum" in event["category"].lower() or "museum" in event["name"].lower():
                            found_museum = True
                            break
                if found_museum: break
            
            if not found_museum:
                violations.append(Violation(
                    constraint_type=ConstraintType.PREFERENCES,
                    description="No museums found, but user prefers them.",
                    severity="warning",
                    suggested_fix="Search for museums in the destination."
                ))

