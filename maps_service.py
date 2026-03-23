import os
import logging
import requests
from urllib.parse import quote
from functools import lru_cache

# Setup Production-grade Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Max number of places to return
MAX_RESULTS = 3

# Request timeout (seconds)
REQUEST_TIMEOUT = 10
PLACES_NEW_API_URL = "https://places.googleapis.com/v1/places:searchText"


@lru_cache(maxsize=100)
def search_places(query: str) -> dict:
    """
    Calls Google Maps Places API (New) Text Search with Caching.

    Security & Usage Best Practices:
    - API Key loaded from .env.
    - @lru_cache prevents quota burn for repeated identical queries.
    - FieldMask heavily restricts payload size to save bandwidth/costs.
    - MAX_RESULTS caps the quota per search.
    """
    logger.info(f"Maps API call executing for: '{query}'. (Cache miss)")
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    if not api_key or api_key in ("YOUR_GOOGLE_MAPS_API_KEY", ""):
        logger.error("API Key missing.")
        return {"status": "error", "message": "Google Maps API Key config missing."}

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.rating,"
            "places.userRatingCount,"
            "places.id,"
            "places.types,"
            "places.googleMapsUri"
        ),
        "Referer": "http://localhost:8000/"
    }

    body = {
        "textQuery": query,
        "maxResultCount": MAX_RESULTS,
        "languageCode": "id"
    }

    try:
        response = requests.post(PLACES_NEW_API_URL, json=body, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        logger.warning("Places API Request Timed Out.")
        return {"status": "error", "message": "API request timed out."}
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        return {"status": "error", "message": f"Network error: {str(e)}"}

    raw_places = data.get("places", [])
    if not raw_places:
        return {"status": "error", "message": f"No places found for: '{query}'"}

    places = []
    for r in raw_places:
        name = r.get("displayName", {}).get("text", "Unknown Place")
        address = r.get("formattedAddress", "Address not available")
        rating = r.get("rating", "N/A")
        total_ratings = r.get("userRatingCount", 0)
        place_id = r.get("id", "")
        types = r.get("types", [])[:3]

        # Explicit Directions Link for the User Requirement
        encoded_dest = quote(f"{name} {address}")
        directions_link = f"https://www.google.com/maps/dir/?api=1&destination={encoded_dest}"
        if place_id:
            directions_link += f"&destination_place_id={place_id}"

        # Embedded iframe map
        if place_id:
            embed_url = f"https://www.google.com/maps/embed/v1/place?key={api_key}&q=place_id:{place_id}"
        else:
            embed_url = f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={encoded_dest}"

        places.append({
            "name": name,
            "address": address,
            "rating": rating,
            "user_ratings_total": total_ratings,
            "types": types,
            "search_link": directions_link,  # Changed from search to directions
            "embed_map_url": embed_url,
        })

    return {"status": "success", "query": query, "places": places}
