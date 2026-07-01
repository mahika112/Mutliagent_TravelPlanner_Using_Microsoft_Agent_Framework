import asyncio

from travel_agent.weather_agent import weather_agent


async def main():

    result = await weather_agent.run(
        "What's the weather in Tokyo?"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())