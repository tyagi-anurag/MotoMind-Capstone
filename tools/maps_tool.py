import os
import requests
from dotenv import load_dotenv

# 1. THIS IS THE MISSING LINK: Load the secrets from .env
load_dotenv()

class MapsTool:
    """
    Professional-grade Maps Tool with API Key security and Mock fallback.
    """
    
    def __init__(self):
        # 2. Securely fetch the key. 
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
    def find_nearby_mechanic(self, location: str, bike_model: str) -> str:
        """
        Finds top-rated mechanics. Switches between Live and Mock mode automatically.
        """
        # 3. If the key is missing or empty, warn the user and use Mock Mode
        if not self.api_key:
            print("⚠️ WARNING: No API Key found. Using Mock Mode.")
            return self._mock_maps_search(location, bike_model)
            
        return self._real_maps_search(location, bike_model)

    def _real_maps_search(self, location, bike_model):
        print(f"🌐 API CALL: Searching Google Maps for '{bike_model}' in '{location}'...")
        
        # Google Places API (New) Text Search
        url = "https://places.googleapis.com/v1/places:searchText"
        
        # Secure headers
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.regularOpeningHours"
        }
        
        payload = {
            "textQuery": f"{bike_model} mechanic in {location}",
            "maxResultCount": 3
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            data = response.json()
            
            # Check for valid response
            if "places" not in data:
                print(f"Google API Response: {data}") # Debugging help
                return "No mechanics found or API error."

            results = []
            for place in data["places"]:
                name = place.get("displayName", {}).get("text", "Unknown Shop")
                address = place.get("formattedAddress", "No address")
                rating = place.get("rating", "N/A")
                
                # Formatting the output
                results.append(f"📍 **{name}** ({rating}⭐)\n   Address: {address}")
            
            return "\n\n".join(results)

        except Exception as e:
            return f"Network Error: {str(e)}"

    def _mock_maps_search(self, location, bike_model):
        """
        High-quality mock data for demo videos if API fails.
        """
        return (
            f"Simulated Results for {bike_model} near {location}:\n"
            f"1. {bike_model} Authorized Service Center (4.5⭐) - 2km away\n"
            f"2. Raju's Bike Point (4.2⭐) - 0.5km away\n"
            f"3. Quick Fix Garage (3.8⭐) - 1.2km away"
        )

if __name__ == "__main__":
    # Test block
    tool = MapsTool()
    print(tool.find_nearby_mechanic("Indiranagar, Bangalore", "Royal Enfield"))