import os

from dotenv import load_dotenv

from azure.identity import AzureCliCredential

from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient

from tools.weather_tool import get_weather

load_dotenv()

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_NAME = os.getenv("MODEL_NAME")


@tool(approval_mode="never_require")
def weather(city: str) -> str:
    """
    Get live weather for a city.
    """
    data = get_weather(city)

    return f"""
City: {data['city']}

Country: {data['country']}

Temperature: {data['temperature']}°C

Feels Like: {data['feels_like']}°C

Humidity: {data['humidity']}%

Weather: {data['weather']}

Description: {data['description']}

Wind Speed: {data['wind_speed']} m/s
"""


client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_NAME,
    credential=AzureCliCredential(),
)

weather_agent = Agent(
    client=client,
    name="WeatherAgent",
    instructions="""
You are a weather specialist.

Whenever the user asks about weather,
ALWAYS use the weather tool.

Never make up weather.

Only use the tool.
""",
    tools=[weather],
)