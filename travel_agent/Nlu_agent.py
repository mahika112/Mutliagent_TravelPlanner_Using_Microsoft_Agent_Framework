"""
nlu_agent.py — Natural Language Understanding agent.

Converts any free-form user message into a validated TripPlan JSON.
Now includes 'intent' field so the aggregator knows the trip mood/goal.
"""

import os
import json
import re
import logging

from dotenv import load_dotenv
from azure.identity import AzureCliCredential

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient

load_dotenv()

log = logging.getLogger(__name__)

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
MODEL_NAME       = os.getenv("MODEL_NAME")

_NLU_INSTRUCTIONS = """
You are a travel intent parser. Your ONLY job is to read the user's message
and return a single JSON object. No prose. No markdown. No explanation.

FIELDS TO EXTRACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
city          (string)   The destination city.
                         "I am in X" / "I'm in X" / "currently in X" -> X
                         If absent, use "unknown".

days          (integer)  Trip duration.
                         "today" / "just today"    -> 1
                         "tomorrow"                -> 1
                         "this weekend"            -> 2
                         "a few days"              -> 3
                         "a week" / "next week"    -> 7
                         "two weeks"               -> 14
                         explicit "5 days"         -> 5
                         not mentioned             -> 1 if "today"/"now", else 3

travel_style  (string)   One of: budget / mid-range / luxury
                         "cheap", "backpacker"     -> budget
                         "luxury", "splurge"       -> luxury
                         anything else             -> mid-range

intent        (string)   PRIMARY mood/goal in 2-5 words. Examples:
                         "party and nightlife"
                         "anime and pop culture"
                         "relax and sightsee"
                         "explore food scene"
                         "nature and adventure"
                         If unclear, use "general sightseeing".

interests     (string)   Comma-separated SEARCH TERMS for Google Places.
                         Map colloquial words to searchable terms:

                         NIGHTLIFE / PARTY:
                         "party","partying","night out","club","clubbing",
                         "rave","dance","bar hopping","drinks","cocktails"
                           -> "nightclub, bar, rooftop bar, live music venue,
                               cocktail bar, lounge, night market"

                         ANIMALS / WILDLIFE:
                         "animals","wildlife","creatures"
                           -> "zoo, aquarium, wildlife sanctuary, animal park"

                         ANIME / MANGA / GAMING:
                         "anime","manga","otaku","gaming","cosplay"
                           -> "anime store, manga shop, pop culture, gaming cafe,
                               figurine shop"

                         FOOD:
                         "food","eat","foodie","hungry","cuisine","dining"
                           -> "restaurant, street food, food market, local cuisine"

                         ART / CULTURE:
                         "art","culture","museum","gallery"
                           -> "art museum, gallery, cultural centre, exhibition"

                         HISTORY / HERITAGE:
                         "history","historical","heritage","ancient","ruins"
                           -> "historical site, temple, heritage, monument, museum"

                         NATURE / OUTDOORS:
                         "nature","outdoor","hiking","park","garden","beach"
                           -> "national park, hiking trail, botanical garden, beach"

                         SHOPPING:
                         "shopping","shop","buy","market","mall"
                           -> "shopping mall, market, boutique, department store"

                         RELAXATION / SPA:
                         "relax","chill","spa","massage","wellness","unwind"
                           -> "spa, wellness centre, hot spring, rooftop pool, cafe"

                         SPORTS / ADVENTURE:
                         "sport","adventure","thrill","extreme","active"
                           -> "adventure sports, theme park, sports centre"

                         FAMILY:
                         "family","kids","children","child-friendly"
                           -> "theme park, zoo, aquarium, family attraction"

                         Keep user words that don't match any mapping.
                         If no interests mentioned, return "".

EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Input : "I am in Los Angeles and wanted to party today"
Output: {"city":"Los Angeles","days":1,"travel_style":"mid-range","intent":"party and nightlife","interests":"nightclub, bar, rooftop bar, live music venue, cocktail bar, lounge"}

Input : "I am in Tokyo today, I love animals and anime"
Output: {"city":"Tokyo","days":1,"travel_style":"mid-range","intent":"anime and animals","interests":"zoo, aquarium, wildlife sanctuary, anime store, manga shop, pop culture, gaming cafe"}

Input : "budget trip to Paris for 5 days, into wine and art"
Output: {"city":"Paris","days":5,"travel_style":"budget","intent":"art and wine culture","interests":"art museum, gallery, wine bar, cultural centre"}

Input : "luxury week in Kyoto, temples and food"
Output: {"city":"Kyoto","days":7,"travel_style":"luxury","intent":"heritage and fine dining","interests":"historical site, temple, heritage, monument, restaurant, local cuisine"}

Input : "Bangkok next week 4 days, street food and markets"
Output: {"city":"Bangkok","days":4,"travel_style":"mid-range","intent":"explore food scene","interests":"street food, food market, local cuisine, shopping mall, market"}

Input : "Tokyo tomorrow, 1 day, anime shops"
Output: {"city":"Tokyo","days":1,"travel_style":"mid-range","intent":"anime and pop culture","interests":"anime store, manga shop, pop culture, gaming cafe, figurine shop"}

Input : "Rome this weekend, history buff"
Output: {"city":"Rome","days":2,"travel_style":"mid-range","intent":"history and heritage","interests":"historical site, temple, heritage, monument, museum"}

Input : "relax in Bali for a week, luxury, spa and beach"
Output: {"city":"Bali","days":7,"travel_style":"luxury","intent":"relaxation and wellness","interests":"spa, wellness centre, hot spring, rooftop pool, beach"}

RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Output ONLY the JSON object. No backticks, no "json" label, no extra text.
- All FIVE keys must always be present: city, days, travel_style, intent, interests.
- interests is a flat comma-separated string of search terms, NOT a JSON list.
- intent is a short human-readable phrase (2-5 words).
- Never add fields beyond the five above.
"""


client = FoundryChatClient(
    project_endpoint=PROJECT_ENDPOINT,
    model=MODEL_NAME,
    credential=AzureCliCredential(),
)

nlu_agent = Agent(
    client=client,
    name="NLUAgent",
    instructions=_NLU_INSTRUCTIONS,
)


def _extract_text(response) -> str:
    if isinstance(response, list):
        return "\n".join(
            block.text for block in response if hasattr(block, "text")
        ).strip()
    return str(response).strip()


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def parse_user_input(message: str) -> dict:
    """
    Parse a free-form user message into a structured dict with keys:
    city, days, travel_style, intent, interests.

    Raises ValueError if the model returns invalid JSON or missing keys.
    """
    log.debug("NLUAgent parsing: %r", message)

    response = await nlu_agent.run(message)
    raw_text = _extract_text(response)
    clean    = _strip_json_fences(raw_text)

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"NLUAgent returned non-JSON.\n"
            f"  Raw : {raw_text!r}\n"
            f"  Error: {exc}"
        )

    required = {"city", "days", "travel_style", "intent", "interests"}
    missing  = required - parsed.keys()
    if missing:
        raise ValueError(
            f"NLUAgent JSON missing keys: {missing}\n"
            f"  Got: {parsed}"
        )

    log.debug("NLUAgent result: %s", parsed)
    return parsed