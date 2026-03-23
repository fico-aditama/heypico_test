import os
import requests
from urllib.parse import quote

def search_places(query: str):
    """
    Calls the Google Maps Text Search API to find places matching the query.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key or api_key == "YOUR_GOOGLE_MAPS_API_KEY":
        # Fallback if no API key is set
        return {"error": "Google Maps API Key is not configured correctly. Please configure it in .env file."}
    
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={quote(query)}&key={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") == "OK":
            results = data.get("results", [])[:3] # limit to 3 results
            places = []
            for r in results:
                name = r.get("name")
                address = r.get("formatted_address")
                rating = r.get("rating", "N/A")
                
                # Directions / Search Link
                search_url = f"https://www.google.com/maps/search/?api=1&query={quote(name + ' ' + address)}"
                
                # Embed Map URL
                embed_url = f"https://www.google.com/maps/embed/v1/place?key={api_key}&q={quote(name + ' ' + address)}"
                
                places.append({
                    "name": name,
                    "address": address,
                    "rating": rating,
                    "search_link": search_url,
                    "embed_map_url": embed_url
                })
            return {"status": "success", "places": places}
        else:
            return {"status": "error", "message": data.get("error_message") or data.get("status")}
    except Exception as e:
        return {"status": "error", "message": str(e)}
