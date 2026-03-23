import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_MAPS_API_KEY")
print(f"Testing with API Key: {api_key[:10]}...{api_key[-5:]}" if api_key else "NO API KEY FOUND")

url = "https://places.googleapis.com/v1/places:searchText"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
    "X-Goog-FieldMask": "places.displayName"
}
body = {
    "textQuery": "coffee in bali"
}

print("\nSending request to Places API (New)...")
response = requests.post(url, json=body, headers=headers)

if response.status_code == 200:
    print("✅ SUCCESS! Places API (New) is working perfectly.")
else:
    print(f"❌ ERROR {response.status_code}: {response.text}")
