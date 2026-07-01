import os
 
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
 
from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
 
load_dotenv()
 
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_NAME = os.getenv("MODEL_NAME")
 
 
@tool(approval_mode="never_require")
def estimate_budget(
    city: str,
    days: int = 3,
    travel_style: str = "mid-range",
) -> str:
    """
    Estimate a travel budget for a city trip.
 
    Args:
        city: Destination city name.
        days: Number of days for the trip (default 3).
        travel_style: One of 'budget', 'mid-range', or 'luxury'.
 
    Returns:
        A formatted string with daily and total cost breakdown.
    """
 
    # Per-day cost ranges in USD by travel style
    COST_PROFILES = {
        "budget": {
            "accommodation": 30,
            "food": 20,
            "transport": 10,
            "activities": 15,
            "misc": 10,
        },
        "mid-range": {
            "accommodation": 100,
            "food": 50,
            "transport": 25,
            "activities": 40,
            "misc": 25,
        },
        "luxury": {
            "accommodation": 350,
            "food": 150,
            "transport": 80,
            "activities": 120,
            "misc": 80,
        },
    }
 
    style = travel_style.lower()
    if style not in COST_PROFILES:
        style = "mid-range"
 
    profile = COST_PROFILES[style]
    daily_total = sum(profile.values())
    trip_total = daily_total * days
 
    lines = [
        f"Budget Estimate for {city} ({days} days, {style.title()} style)",
        "=" * 50,
        "",
        "Daily Breakdown (per person, USD):",
        f"  • Accommodation : ${profile['accommodation']}",
        f"  • Food & Drinks : ${profile['food']}",
        f"  • Local Transport: ${profile['transport']}",
        f"  • Activities    : ${profile['activities']}",
        f"  • Miscellaneous : ${profile['misc']}",
        f"  ─────────────────────────────",
        f"  Daily Total     : ${daily_total}",
        "",
        f"Total for {days} days: ${trip_total}",
        "",
        "Note: Estimates are approximate and vary by season and exchange rates.",
    ]
 
    return "\n".join(lines)
 
 
client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_NAME,
    credential=AzureCliCredential(),
)
 
budget_agent = Agent(
    client=client,
    name="BudgetAgent",
    instructions="""
You are a travel budget specialist.
 
Your ONLY job is to estimate trip costs.
 
ALWAYS use the estimate_budget tool — never invent numbers.
 
Ask the user for:
  - Number of days if not provided (default to 3).
  - Travel style: budget, mid-range, or luxury (default mid-range).
 
Present the breakdown clearly and concisely.
""",
    tools=[estimate_budget],
)
 