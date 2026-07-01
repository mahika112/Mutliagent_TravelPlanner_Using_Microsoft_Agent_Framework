import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# How long to wait for OpenWeather before giving up (seconds)
REQUEST_TIMEOUT = 10


def get_weather(city: str) -> dict:
    """
    Fetch current weather for a city from OpenWeatherMap.

    Args:
        city: City name, optionally with country code e.g. "London,GB".

    Returns:
        Dict with keys: city, country, temperature, feels_like,
        humidity, weather, description, wind_speed.

    Raises:
        ValueError: If city is empty or API key is missing.
        RuntimeError: If the API returns a non-200 response.
        requests.Timeout: If the request takes longer than REQUEST_TIMEOUT.
    """

    # ── Input validation ───────────────────────────────────────────────────
    if not city or not city.strip():
        raise ValueError("City name must not be empty.")

    if not API_KEY:
        raise ValueError(
            "OPENWEATHER_API_KEY is not set. "
            "Add it to your .env file."
        )

    # ── API call ───────────────────────────────────────────────────────────
    params = {
        "q": city.strip(),
        "appid": API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        raise requests.Timeout(
            f"OpenWeatherMap did not respond within {REQUEST_TIMEOUT}s "
            f"for city '{city}'."
        )

    # ── Error handling ─────────────────────────────────────────────────────
    if response.status_code == 401:
        raise RuntimeError(
            "Invalid OpenWeatherMap API key. Check OPENWEATHER_API_KEY in .env."
        )
    if response.status_code == 404:
        raise RuntimeError(
            f"City '{city}' not found. "
            "Try including the country code e.g. 'Paris,FR'."
        )
    if response.status_code == 429:
        raise RuntimeError(
            "OpenWeatherMap rate limit exceeded. "
            "Wait a moment and retry."
        )
    if response.status_code != 200:
        # Surface the full API error message for unexpected codes
        try:
            detail = response.json().get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(
            f"OpenWeatherMap error {response.status_code}: {detail}"
        )

    # ── Parse response ─────────────────────────────────────────────────────
    data = response.json()

    return {
        "city": data["name"],
        "country": data["sys"]["country"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "weather": data["weather"][0]["main"],
        "description": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"],
    }