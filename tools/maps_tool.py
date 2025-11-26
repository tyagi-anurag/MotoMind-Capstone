# tools/maps_tool.py
import os
import requests

class MapsTool:
    """
    Tools for finding local services like mechanics and towing.
    """
    
    def __init__(self):
        # We try to get the API key, but we don't crash if it's missing
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        
    def find_nearby_mechanic(self, location: str, bike_model: str) -> str:
        """
        Finds the nearest authorized service center or roadside mechanic
        based on the bike model and user location.
        
        Args:
            location (str): The user's current location (e.g., "Indiranagar, Bangalore").
            bike_model (str): The model of the bike (e.g., "Royal Enfield Classic 350").
            
        Returns:
            str: A formatted list of nearby mechanics.
        """
        print(f"🔧 TOOL CALL: Searching for mechanics for {bike_model} near {location}...")
        
        # STRATEGY: If we have an API Key, we do a real search.
        if self.api_key:
            return self._real_maps_search(location, bike_model)
        else:
            return self._mock_maps_search(location, bike_model)

    def _real_maps_search(self, location, bike_model):
        # This is the production-ready code for Google Places API
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        query = f"{bike_model} mechanic near {location}"
        params = {
            "query": query,
            "key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "OK":
                results = []
                for place in data["results"][:3]: # Get top 3
                    name = place.get("name")
                    addr = place.get("formatted_address")
                    rating = place.get("rating", "N/A")
                    results.append(f"- {name} ({rating}⭐): {addr}")
                return "\n".join(results)
            else:
                return "Error finding mechanics via Google Maps API."
        except Exception as e:
            return f"Connection Error: {str(e)}"

    def _mock_maps_search(self, location, bike_model):
        # This ensures your demo ALWAYS works, even if the API fails
        return (
            f"Simulated Results for {bike_model} near {location}:\n"
            f"1. {bike_model} Authorized Service Center (4.5⭐) - 2km away\n"
            f"2. Raju's Bike Point (4.2⭐) - 0.5km away\n"
            f"3. Quick Fix Garage (3.8⭐) - 1.2km away"
        )
    
if __name__ == "__main__":
# Simple test to see if your key works
    tool = MapsTool()
    print(tool.find_nearby_mechanic("Indiranagar, Bangalore", "Royal Enfield"))