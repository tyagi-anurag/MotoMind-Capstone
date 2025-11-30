import os
import requests
from dotenv import load_dotenv

load_dotenv()

class MapsTool:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")

    def find_nearby_mechanic(self, location: str, bike_model: str) -> str:
        """
        Finds bike mechanics with clickable Google Maps links.
        """
        if not self.api_key:
            print("⚠️ WARNING: No API Key found. Using Mock Mode.")
            return self._mock_maps_search(location, bike_model)
            
        return self._real_maps_search(location, bike_model)

    def _real_maps_search(self, location, bike_model):
        print(f"🌐 API CALL: Searching Maps for '{bike_model}' mechanics in '{location}'...")
        
        url = "https://places.googleapis.com/v1/places:searchText"
        
        # Request the Google Maps URI specifically
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.googleMapsUri,places.regularOpeningHours"
        }
        
        # Specific query for BIKES, including both local shops and showrooms
        payload = {
            "textQuery": f"Motorcycle mechanic, repair shop, and {bike_model} service center in {location}",
            "maxResultCount": 10  # Get more results
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            data = response.json()
            
            if "places" not in data:
                return f"No mechanics found near {location}."

            results = []
            for place in data["places"]:
                name = place.get("displayName", {}).get("text", "Unknown Shop")
                address = place.get("formattedAddress", "No address")
                rating = place.get("rating", "N/A")
                count = place.get("userRatingCount", 0)
                # THE KEY: Get the direct Google Maps Link
                maps_link = place.get("googleMapsUri", f"https://www.google.com/maps/search/?api=1&query={name}+{location}")
                
                is_open = place.get("regularOpeningHours", {}).get("openNow", None)
                status_emoji = "🟢" if is_open else "🔴" if is_open is False else "⚪"

                # Format as a Markdown Card
                entry = (
                    f"### {status_emoji} [{name}]({maps_link})\n"
                    f"**Rating:** {rating}⭐ ({count} reviews)\n"
                    f"📍 {address}\n"
                    f"🔗 [Open in Google Maps]({maps_link})\n"
                    "---"
                )
                results.append(entry)
            
            return "\n".join(results)

        except Exception as e:
            return f"Network Error: {str(e)}"

    def _mock_maps_search(self, location, bike_model):
        """
        High-quality mock data with fake links for the demo.
        """
        return (
            f"### 🟢 [{bike_model} Authorized Service Center](https://maps.google.com)\n"
            f"**Rating:** 4.6⭐ (120 reviews)\n"
            f"📍 12, Main Road, Near {location}\n"
            f"🔗 [Open in Google Maps](https://maps.google.com)\n"
            "---\n"
            f"### 🟢 [Raju Bike Point (Local Expert)](https://maps.google.com)\n"
            f"**Rating:** 4.8⭐ (45 reviews)\n"
            f"📍 Shop 4, Back Street, {location}\n"
            f"🔗 [Open in Google Maps](https://maps.google.com)\n"
            "---\n"
            f"### 🔴 [Quick Fix Garage](https://maps.google.com)\n"
            f"**Rating:** 3.8⭐ (12 reviews)\n"
            f"📍 1.2km away from {location}\n"
            f"🔗 [Open in Google Maps](https://maps.google.com)"
        )

if __name__ == "__main__":
    tool = MapsTool()
    print(tool.find_nearby_mechanic("Indiranagar, Bangalore", "Royal Enfield"))