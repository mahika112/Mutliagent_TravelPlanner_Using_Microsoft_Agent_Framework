import os

from dotenv import load_dotenv
from azure.identity import AzureCliCredential

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient

from tools.places_tool import search_places

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_NAME = os.getenv("MODEL_NAME")


@tool(approval_mode="never_require")
def find_places(city: str, interest: str = "") -> str:
    """
    Find tourist attractions using Google Places.
    """

    places = search_places(city, interest)

    if not places:
        return "No attractions found."

    output = ""

    for i, place in enumerate(places, start=1):

        output += (
            f"{i}. {place['name']}\n"
            f"Rating: {place['rating']}\n"
            f"Address: {place['address']}\n\n"
        )

    return output


client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_NAME,
    credential=AzureCliCredential(),
)

places_agent = Agent(
    client=client,
    name="PlacesAgent",
    instructions="""
You are a travel destination expert.

Your ONLY responsibility is recommending attractions.

Always use the find_places tool.

Never invent attractions.

If the user specifies interests (anime, food, history, shopping, nature),
pass them to the tool to refine the search.

Present the results clearly.
""",
    tools=[find_places],
)