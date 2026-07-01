import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
PLACES_URL = "https://places.googleapis.com/v1/places:searchText"

# Maximum results to return (Google Places New API supports up to 20)
MAX_RESULTS = 5

# How long to wait for Google before giving up (seconds)
REQUEST_TIMEOUT = 10

# Fields to request from Google Places (New API field mask syntax)
FIELD_MASK = ",".join([
    "places.displayName",
    "places.formattedAddress",
    "places.rating",
    "places.userRatingCount",   # extra: adds credibility signal
    "places.primaryType",
    "places.websiteUri",        # extra: useful for the itinerary
])


def search_places(city: str, interest: str = "") -> list[dict]:
    """
    Search for places in a city using the Google Places API (New).

    Args:
        city:     Destination city e.g. "Tokyo".
        interest: Optional theme to narrow results e.g. "anime, food".
                  Multiple interests can be comma-separated.

    Returns:
        List of dicts, each with keys:
        name, rating, rating_count, address, type, website.
        Returns an empty list if no places are found.

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
            "GOOGLE_PLACES_API_KEY is not set. "
            "Add it to your .env file."
        )

    # ── Build query ────────────────────────────────────────────────────────
    interest = interest.strip()
    if interest:
        # Handle comma-separated interests: pick the first for the query,
        # mention the rest to help the model rank results
        primary = interest.split(",")[0].strip()
        query = f"{primary} attractions in {city}"
    else:
        query = f"Top tourist attractions in {city}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    body = {
        "textQuery": query,
        "pageSize": MAX_RESULTS,       # limit at the API level, not just slicing
        "languageCode": "en",          # always return English names
    }

    # ── API call ───────────────────────────────────────────────────────────
    try:
        response = requests.post(
            PLACES_URL,
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.Timeout:
        raise requests.Timeout(
            f"Google Places did not respond within {REQUEST_TIMEOUT}s "
            f"for city '{city}'."
        )

    # ── Error handling ─────────────────────────────────────────────────────
    if response.status_code == 400:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"Google Places bad request: {detail}")

    if response.status_code == 403:
        raise RuntimeError(
            "Google Places API key is invalid or the Places API (New) "
            "is not enabled for this project. Check GOOGLE_PLACES_API_KEY."
        )

    if response.status_code == 429:
        raise RuntimeError(
            "Google Places quota exceeded. "
            "Check your usage limits in Google Cloud Console."
        )

    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(
            f"Google Places error {response.status_code}: {detail}"
        )

    # ── Parse response ─────────────────────────────────────────────────────
    data = response.json()
    raw_places = data.get("places", [])

    if not raw_places:
        return []

    places = []
    for place in raw_places[:MAX_RESULTS]:
        # displayName is always present per the field mask
        name = place.get("displayName", {}).get("text", "Unknown")

        places.append({
            "name": name,
            "rating": place.get("rating", "N/A"),
            "rating_count": place.get("userRatingCount", "N/A"),
            "address": place.get("formattedAddress", "N/A"),
            "type": place.get("primaryType", "N/A"),
            "website": place.get("websiteUri", "N/A"),
        })

    return places