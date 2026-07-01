"""
planner_agent.py — Master orchestrator with parallel sub-agent execution.

Execution model
───────────────
                        run_parallel_agents(...)
                                    │
                    ┌───────────────┼───────────────┐
                    │  asyncio.gather() — all three  │
                    │  run simultaneously            │
                    ▼               ▼               ▼
              WeatherAgent    PlacesAgent      BudgetAgent
             (OpenWeather)  (Google Places)  (cost profiles)
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                             AggregatorAgent
                       (intent-driven Markdown itinerary)
                                    │
                                    ▼
                              Final output
"""

import os
import asyncio
import time
import logging

from dotenv import load_dotenv
from azure.identity import AzureCliCredential

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient

from travel_agent.weather_agent    import weather_agent
from travel_agent.places_agent     import places_agent
from travel_agent.budget_agent     import budget_agent
from travel_agent.aggregator_agent import aggregator_agent

load_dotenv()

log = logging.getLogger(__name__)

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_NAME       = os.getenv("MODEL_NAME")


# ── Shared response extractor ─────────────────────────────────────────────────

def _extract_text(response) -> str:
    if isinstance(response, list):
        return "\n".join(
            block.text for block in response if hasattr(block, "text")
        ).strip()
    return str(response).strip()


# ── Individual sub-agent callers ──────────────────────────────────────────────

async def _call_weather(city: str) -> tuple:
    t0 = time.perf_counter()
    try:
        response = await weather_agent.run(f"Get the current weather for {city}.")
        result   = _extract_text(response)
    except Exception as exc:
        result = f"[WeatherAgent error] {exc}"
    return ("weather", result, time.perf_counter() - t0)


async def _call_places(city: str, interests: str) -> tuple:
    t0 = time.perf_counter()
    query = f"Find the best places to visit in {city}"
    if interests.strip():
        query += f" for someone interested in: {interests}."
    try:
        response = await places_agent.run(query)
        result   = _extract_text(response)
    except Exception as exc:
        result = f"[PlacesAgent error] {exc}"
    return ("places", result, time.perf_counter() - t0)


async def _call_budget(city: str, days: int, travel_style: str) -> tuple:
    t0 = time.perf_counter()
    try:
        response = await budget_agent.run(
            f"Estimate the budget for a {days}-day {travel_style} "
            f"trip to {city}. Days: {days}. Travel style: {travel_style}."
        )
        result = _extract_text(response)
    except Exception as exc:
        result = f"[BudgetAgent error] {exc}"
    return ("budget", result, time.perf_counter() - t0)


# ── Parallel runner ───────────────────────────────────────────────────────────

async def run_parallel_agents(
    city: str,
    days: int = 3,
    travel_style: str = "mid-range",
    interests: str = "",
    intent: str = "general sightseeing",
    progress_cb=None,
) -> dict:
    """
    Fire WeatherAgent, PlacesAgent, and BudgetAgent simultaneously, then
    pass all results + intent to AggregatorAgent.

    Args:
        city         : Destination city.
        days         : Trip duration in days.
        travel_style : 'budget', 'mid-range', or 'luxury'.
        interests    : Comma-separated search terms for PlacesAgent.
        intent       : Primary trip mood/goal e.g. "party and nightlife".
        progress_cb  : Optional async callable(label, result, elapsed)
                       called as each parallel agent completes.

    Returns dict with keys: weather, places, budget, itinerary, timings.
    """
    results = {}
    timings = {}

    # ── Phase 1: parallel ──────────────────────────────────────────────────
    t_parallel = time.perf_counter()

    gathered = await asyncio.gather(
        _call_weather(city),
        _call_places(city, interests),
        _call_budget(city, days, travel_style),
        return_exceptions=False,
    )

    timings["parallel"] = time.perf_counter() - t_parallel

    for label, result, elapsed in gathered:
        results[label] = result
        timings[label] = elapsed
        if progress_cb:
            await progress_cb(label, result, elapsed)

    # ── Phase 2: aggregation ───────────────────────────────────────────────
    t_agg = time.perf_counter()

    sep = "━" * 50
    agg_prompt = f"""\
City          : {city}
Trip Duration : {days} day{"s" if days != 1 else ""}
Intent        : {intent}
Interests     : {interests or "none specified"}

{sep}
WEATHER DATA
{sep}
{results["weather"]}

{sep}
PLACES DATA
{sep}
{results["places"]}

{sep}
BUDGET DATA
{sep}
{results["budget"]}

The user's primary goal is: {intent}
Build the entire itinerary around this intent.
Follow the output format in your instructions exactly.
"""

    try:
        agg_response         = await aggregator_agent.run(agg_prompt)
        results["itinerary"] = _extract_text(agg_response)
    except Exception as exc:
        results["itinerary"] = f"[AggregatorAgent error] {exc}"

    timings["aggregator"] = time.perf_counter() - t_agg
    timings["total"]      = timings["parallel"] + timings["aggregator"]

    return {**results, "timings": timings}


# ── PlannerAgent (LLM wrapper for conversational / free-form use) ─────────────

client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_NAME,
    credential=AzureCliCredential(),
)

planner_agent = Agent(
    client=client,
    name="PlannerAgent",
    instructions="""
You are a travel-planning coordinator.
Extract parameters from the user's message and return ONLY a JSON object.

Keys to extract:
  city          (string, required)
  days          (integer, default 3)
  travel_style  (budget / mid-range / luxury, default mid-range)
  intent        (2-5 word trip mood/goal, e.g. "party and nightlife")
  interests     (comma-separated search terms, default "")

Respond with ONLY valid JSON. No prose, no markdown fences.
Example:
{"city":"Tokyo","days":5,"travel_style":"luxury","intent":"anime and pop culture","interests":"anime store, manga shop, gaming cafe"}
""",
)