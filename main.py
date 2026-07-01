"""
main.py — Entry point for the multi-agent travel planner.

Default mode: conversational chat loop — just type naturally:

    You › I am in Los Angeles and wanted to party today
    You › I am in Tokyo today, I love animals and anime
    You › luxury week in Kyoto, temples and food please
"""

import asyncio
import argparse
import sys
import textwrap

from pydantic import ValidationError

from models.trip_plan     import TripPlan, VALID_STYLES
from travel_agent.Nlu_agent     import parse_user_input
from travel_agent.planner_agent import run_parallel_agents

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BLUE   = "\033[94m"
DIM    = "\033[2m"
RED    = "\033[91m"

AGENT_ICONS = {
    "weather" : "🌤️  WeatherAgent",
    "places"  : "📍 PlacesAgent ",
    "budget"  : "💰 BudgetAgent ",
}

# ── Intent → emoji mapping for the header ────────────────────────────────────
INTENT_EMOJI = {
    "party":     "🎉",
    "nightlife": "🎉",
    "anime":     "🎌",
    "animal":    "🐾",
    "food":      "🍜",
    "nature":    "🌿",
    "history":   "🏛️",
    "art":       "🎨",
    "relax":     "🧘",
    "spa":       "🧘",
    "shopping":  "🛍️",
    "adventure": "🧗",
    "family":    "👨‍👩‍👧",
}

def intent_emoji(intent: str) -> str:
    intent_lower = intent.lower()
    for keyword, emoji in INTENT_EMOJI.items():
        if keyword in intent_lower:
            return emoji
    return "🌍"


# ── Progress callback ─────────────────────────────────────────────────────────

async def on_agent_done(label: str, result: str, elapsed: float) -> None:
    is_error = result.strip().startswith("[")
    status   = f"{GREEN}✓ done{RESET}" if not is_error else f"{YELLOW}⚠ error{RESET}"
    print(f"    {AGENT_ICONS[label]}  {status}  {DIM}({elapsed:.1f}s){RESET}")


# ── Timing summary ────────────────────────────────────────────────────────────

def print_timings(timings: dict) -> None:
    seq   = timings["weather"] + timings["places"] + timings["budget"]
    saved = max(seq - timings["parallel"], 0.0)
    pct   = int(saved / seq * 100) if seq > 0 else 0
    print(f"\n{DIM}  ── Timing ──────────────────────────────────{RESET}")
    print(f"{DIM}  WeatherAgent   : {timings['weather']:.1f}s{RESET}")
    print(f"{DIM}  PlacesAgent    : {timings['places']:.1f}s{RESET}")
    print(f"{DIM}  BudgetAgent    : {timings['budget']:.1f}s{RESET}")
    print(f"{DIM}  Parallel wall  : {timings['parallel']:.1f}s  "
          f"(vs ~{seq:.1f}s sequential → {pct}% faster){RESET}")
    print(f"{DIM}  AggregatorAgent: {timings['aggregator']:.1f}s{RESET}")
    print(f"{DIM}  Total          : {timings['total']:.1f}s{RESET}")
    print(f"{DIM}  ─────────────────────────────────────────────{RESET}\n")


# ── Core pipeline ─────────────────────────────────────────────────────────────

async def handle_message(user_message: str) -> None:
    """NLUAgent → validate → parallel agents → aggregator → print."""

    # Step 1: NLU
    print(f"\n{CYAN}  🧠 NLUAgent parsing intent…{RESET}")
    try:
        raw = await parse_user_input(user_message)
    except ValueError as exc:
        print(f"{RED}  ✗ Could not understand: {exc}{RESET}")
        print(f"{YELLOW}  Try: \"I am in Tokyo today, I love animals and anime\"{RESET}\n")
        return

    intent   = raw.get("intent", "general sightseeing")
    emoji    = intent_emoji(intent)
    interests_display = raw["interests"] or "none"

    print(f"  {DIM}Understood →{RESET} "
          f"{BOLD}city={raw['city']}{RESET}  "
          f"days={raw['days']}  "
          f"style={raw['travel_style']}  "
          f"{CYAN}intent={intent}{RESET}  "
          f"interests={interests_display}")

    if raw["city"].lower() in ("unknown", "", "none"):
        print(f"{YELLOW}  ✗ Couldn't identify a city. "
              f"Try: \"I'm in Los Angeles\"{RESET}\n")
        return

    # Step 2: Validate — strip 'intent' before passing to TripPlan
    # (TripPlan only knows city/days/travel_style/interests)
    trip_raw = {k: raw[k] for k in ("city", "days", "travel_style", "interests")}
    try:
        plan = TripPlan(**trip_raw)
    except ValidationError as exc:
        print(f"{RED}  ✗ Validation error: {exc}{RESET}\n")
        return

    # Step 3: Header
    day_word = "day" if plan.days == 1 else "days"
    print(f"\n  {BOLD}{emoji} {plan.city}  ·  {plan.days} {day_word}  "
          f"·  {plan.travel_style.title()}  ·  {intent}{RESET}")
    print(f"  {'─' * 58}")
    print(f"\n  {CYAN}⚡ WeatherAgent + PlacesAgent + BudgetAgent in parallel…{RESET}\n")

    # Step 4: Parallel sub-agents
    try:
        output = await run_parallel_agents(
            city         = plan.city,
            days         = plan.days,
            travel_style = plan.travel_style,
            interests    = plan.interests,
            intent       = intent,
            progress_cb  = on_agent_done,
        )
    except Exception as exc:
        print(f"{RED}  ✗ Agent pipeline failed: {exc}{RESET}\n")
        return

    # Step 5: Print itinerary
    print(f"\n  {CYAN}✍️  AggregatorAgent composing itinerary…  "
          f"{DIM}({output['timings']['aggregator']:.1f}s){RESET}\n")
    print(f"  {'─' * 58}")
    print(output["itinerary"])
    print(f"  {'─' * 58}")
    print_timings(output["timings"])
    print(f"  {GREEN}{BOLD}✅  Done. Bon voyage! 🧳{RESET}\n")


# ── CLI args ──────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI-powered parallel multi-agent travel planner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Default: conversational chat — just run `python main.py`

            CLI examples:
              python main.py --city "Los Angeles" --days 1 --interests "nightclub, bar"
              python main.py --city Tokyo --days 1 --interests "anime, zoo"
              python main.py --city Kyoto --days 7 --style luxury --interests "temple, food"
        """),
    )
    parser.add_argument("--city",      type=str, default="")
    parser.add_argument("--days",      type=int, default=0)
    parser.add_argument("--style",     type=str, default="",
                        choices=VALID_STYLES + ("",))
    parser.add_argument("--interests", type=str, default="")
    parser.add_argument("--intent",    type=str, default="general sightseeing")
    return parser.parse_args()


# ── Chat loop ─────────────────────────────────────────────────────────────────

async def chat_loop() -> None:
    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  🌍  AI Travel Planner  —  just tell me what you want!{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")
    print(f"{DIM}  Examples:{RESET}")
    print(f"{DIM}    I am in Los Angeles and wanted to party today{RESET}")
    print(f"{DIM}    I am in Tokyo today, I love animals and anime{RESET}")
    print(f"{DIM}    Budget trip to Paris 5 days, wine and art{RESET}")
    print(f"{DIM}    Luxury week in Kyoto, temples and food{RESET}")
    print(f"{DIM}  Type  exit  to quit.{RESET}")
    print(f"{BOLD}{'─' * 60}{RESET}\n")

    while True:
        try:
            user_input = input(f"{BLUE}You ›{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}  Goodbye! 👋{RESET}\n")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "bye", "q"}:
            print(f"\n{DIM}  Safe travels! 👋{RESET}\n")
            break

        await handle_message(user_input)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    args = parse_args()

    if args.city:
        # CLI mode — build a natural sentence so NLU parses it consistently
        msg = (
            f"I am in {args.city} for "
            f"{args.days if args.days > 0 else 3} "
            f"day{'s' if (args.days or 3) != 1 else ''}, "
            f"{args.style or 'mid-range'} travel, "
            f"intent: {args.intent}"
            + (f", interests: {args.interests}" if args.interests else "")
        )
        await handle_message(msg)
        return

    await chat_loop()


if __name__ == "__main__":
    asyncio.run(main())