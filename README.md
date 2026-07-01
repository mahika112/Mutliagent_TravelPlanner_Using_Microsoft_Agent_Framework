# 🌍 AI Travel Planner — Multi-Agent System

A conversational AI travel planner built on **Microsoft Azure AI Foundry** using the **Agent Framework**. Just describe your trip in plain English — the system understands your intent, runs multiple specialist AI agents in parallel, and composes a full day-by-day itinerary tailored to what you actually want to do.

---

## 💬 How It Works

Just type naturally:

```
You › I am in Los Angeles for 3 days and wanted to party today
You › I am in Tokyo today, I love animals and anime
You › Budget trip to Paris 5 days, wine and art
You › Luxury week in Kyoto, temples and food
```

No forms. No dropdowns. No structured input required.

---

## 🏗️ Architecture

```
User (natural language)
        │
        ▼
   NLUAgent  ←── Parses city, days, style, intent, interests
        │
        ▼
  PlannerAgent  (orchestrator)
        │
        ├─────────────────────────────────────┐
        │         asyncio.gather()            │
        ▼               ▼                    ▼
  WeatherAgent    PlacesAgent          BudgetAgent
  (OpenWeather)  (Google Places)    (cost profiles)
        │               │                    │
        └───────────────┼────────────────────┘
                        ▼
               AggregatorAgent
          (intent-driven itinerary)
                        │
                        ▼
            Final Markdown Itinerary
```

### Agents

| Agent | Role | API / Source |
|---|---|---|
| **NLUAgent** | Parses free-form text into structured trip parameters | Azure AI Foundry LLM |
| **WeatherAgent** | Fetches live weather for the destination | OpenWeatherMap API |
| **PlacesAgent** | Finds top venues filtered by intent and interests | Google Places API (New) |
| **BudgetAgent** | Estimates per-day and total trip costs | Built-in cost profiles |
| **AggregatorAgent** | Composes the full itinerary shaped around user intent | Azure AI Foundry LLM |

---

## ⚡ Parallel Execution

WeatherAgent, PlacesAgent, and BudgetAgent run **simultaneously** using `asyncio.gather()` — not sequentially. From a real run:

```
⚡ WeatherAgent + PlacesAgent + BudgetAgent in parallel…

  🌤️  WeatherAgent  ✓ done  (8.8s)
  📍 PlacesAgent   ✓ done  (8.9s)
  💰 BudgetAgent   ✓ done  (6.1s)

Parallel wall : 8.9s  (vs ~23.8s sequential → 62% faster)
```

**62% faster** than running agents one after the other.

---

## 🎯 Intent-Driven Output

The system extracts the user's **primary intent** and reshapes the entire itinerary around it — not just the place search.

**Input:** `"I am in Los Angeles for 3 days and wanted to party today"`

**Parsed:**
```
city=Los Angeles  days=3  style=mid-range
intent=party and nightlife
interests=nightclub, bar, rooftop bar, live music venue, cocktail bar, lounge
```

**Output (excerpt):**
```markdown
# 💃 Travel Itinerary: Los Angeles, USA
> party and nightlife — Dive into LA's hottest bars, clubs, and
  rooftop lounges for three nights of non-stop fun.

### Day 1 — Speakeasy & Live Beats

**Evening**
- Dirty Laundry (Cocktail Bar / Lounge) — ⭐ 3.9
  📍 1725 N Hudson Ave, Los Angeles, CA 90028
  🕙 Best time to arrive: 20:00
  💡 Hidden speakeasy with vintage vibe — perfect warm-up.

- The Virgil (Bar / Live Music Venue) — ⭐ 4.3
  📍 4519 Santa Monica Blvd, Los Angeles, CA 90029
  🕙 Best time to arrive: 22:30
  💡 DJs and live bands — cover charge varies by night.
```

Intent examples and how the itinerary changes:

| Intent | Morning | Evening focus | Tips |
|---|---|---|---|
| `party and nightlife` | Recovery / sleep in | Bars, clubs, rooftop venues | Dress codes, cover charges, rideshare |
| `anime and pop culture` | Anime stores open early | Gaming cafes, figurine shops | Limited-edition drops, best floors |
| `nature and adventure` | Early hike start | Sunset viewpoints | Trail gear, water, difficulty levels |
| `relax and wellness` | Spa booking | Quiet rooftop dinner | Quietest hours, advance booking |
| `explore food scene` | Food market | Night food tour | Reservations, cash vs card |

---

## 🖥️ Real Output

```
════════════════════════════════════════════════════════════
  🌍  AI Travel Planner  —  just tell me what you want!
════════════════════════════════════════════════════════════
  Examples:
    I am in Los Angeles and wanted to party today
    I am in Tokyo today, I love animals and anime
    Budget trip to Paris 5 days, wine and art
    Luxury week in Kyoto, temples and food
  Type  exit  to quit.
────────────────────────────────────────────────────────────

You › I am in Los Angeles for 3 days and wanted to party today.

  🧠 NLUAgent parsing intent…
  Understood → city=Los Angeles  days=3  style=mid-range
               intent=party and nightlife
               interests=nightclub, bar, rooftop bar, live music venue, cocktail bar, lounge

  🎉 Los Angeles  ·  3 days  ·  Mid-Range  ·  party and nightlife
  ──────────────────────────────────────────────────────────

  ⚡ WeatherAgent + PlacesAgent + BudgetAgent in parallel…

    🌤️  WeatherAgent  ✓ done  (8.8s)
    📍 PlacesAgent   ✓ done  (8.9s)
    💰 BudgetAgent   ✓ done  (6.1s)

  ✍️  AggregatorAgent composing itinerary…  (24.9s)
  ──────────────────────────────────────────────────────────

  ── Timing ──────────────────────────────────
  WeatherAgent   : 8.8s
  PlacesAgent    : 8.9s
  BudgetAgent    : 6.1s
  Parallel wall  : 8.9s  (vs ~23.8s sequential → 62% faster)
  AggregatorAgent: 24.9s
  Total          : 33.7s
  ─────────────────────────────────────────────

  ✅  Done. Bon voyage! 🧳
```

---

## 📁 Project Structure

```
TravelPlannerAgent/
├── main.py                    # Conversational chat loop + CLI entry point
├── .env                       # API keys (never commit)
│
├── models/
│   └── trip_plan.py           # Pydantic input model with validation
│
├── agents/
│   ├── nlu_agent.py           # Parses natural language → structured JSON
│   ├── weather_agent.py       # Fetches live weather
│   ├── places_agent.py        # Finds venues filtered by interests
│   ├── budget_agent.py        # Estimates travel costs
│   ├── aggregator_agent.py    # Composes intent-driven itinerary
│   └── planner_agent.py       # Orchestrator + parallel runner
│
└── tools/
    ├── weather_tool.py        # OpenWeatherMap API wrapper
    └── places_tool.py         # Google Places API (New) wrapper
```

---

## 🚀 Setup

### 1. Install dependencies

```bash
pip install azure-ai-projects azure-identity python-dotenv pydantic requests
```

### 2. Configure `.env`

```env
PROJECT_ENDPOINT=https://<your-hub>.api.azureml.ms/...
MODEL_NAME=gpt-4o
OPENWEATHER_API_KEY=your_openweathermap_key
GOOGLE_PLACES_API_KEY=your_google_places_key
```

### 3. Authenticate with Azure

```bash
az login
```

### 4. Run

```bash
python main.py
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Agent Framework | Microsoft Azure AI Foundry — Agent Framework |
| LLM | GPT-4o via Azure AI Foundry |
| Auth | Azure CLI Credential (`az login`) |
| Weather | OpenWeatherMap API |
| Places | Google Places API (New) |
| Parallelism | Python `asyncio.gather()` |
| Validation | Pydantic v2 |

---

## 🔭 What's Next

- **Streamlit UI** — visual chat interface with a map
- **Flight search** — add a FlightsAgent via a travel API
- **Hotel recommendations** — HotelAgent with booking links
- **Memory** — remember past trips across sessions
- **Export** — save itinerary as PDF or share link
