import asyncio

from travel_agent.places_agent import places_agent


async def main():

    result = await places_agent.run(
        "Find the best anime and shopping places in Tokyo."
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(main())