import asyncio

from travel_agent.planner_agent import planner_agent
from travel_agent.weather_agent import weather_agent
from travel_agent.places_agent import places_agent
from travel_agent.aggregator_agent import aggregator_agent


async def run_travel_workflow(user_request: str):

    print("Planner Agent...\n")

    planner = await planner_agent.run(user_request)

    planner_output = planner.text

    print(planner_output)

    print("\nRunning Weather & Places in parallel...\n")

    weather_task = asyncio.create_task(
        weather_agent.run(planner_output)
    )

    places_task = asyncio.create_task(
        places_agent.run(planner_output)
    )

    weather_result, places_result = await asyncio.gather(
        weather_task,
        places_task,
    )

    final_prompt = f"""
User Request

{user_request}

------------------------

Planner Output

{planner_output}

------------------------

Weather

{weather_result.text}

------------------------

Places

{places_result.text}

Create the final itinerary.
"""

    final_result = await aggregator_agent.run(final_prompt)

    return final_result