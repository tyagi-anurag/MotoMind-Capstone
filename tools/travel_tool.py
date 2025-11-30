import os
from dotenv import load_dotenv
import google.generativeai as genai
import math

load_dotenv()

class TravelTool:
    """
    A specialist tool for planning GROUP motorcycle trips.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def plan_trip(self, source: str, destination: str, bike_model: str, days: int, people: int) -> str:
        print(f"🛣️ TRAVEL CALL: Planning ROUND TRIP {days} days from {source} to {destination} for {people} people...")
        
        # Logic: Assume max 2 people per bike
        bikes_needed = math.ceil(people / 2)
        convoy_desc = f"{bikes_needed}x {bike_model}s"
        
        prompt = f"""
        Act as a veteran motorcycle tour captain. Plan a group expedition.
        
        **LOGISTICS:**
        - Route: {source} <-> {destination} (Round Trip)
        - Squad Size: {people} Riders
        - Fleet: {convoy_desc} (Assuming double-riding or mix)
        - Duration: {days} Days
        
        **INSTRUCTIONS:**
        1. Since this is a group of {people}, emphasize CONVOY rules (riding formation, tail gunner, communication).
        2. Adjust travel times (groups move slower than solo riders).
        3. Suggest accommodation that can handle {people} people (e.g., "Book homestays in advance").
        
        **STRICT OUTPUT FORMAT (Use Markdown):**
        
        # 🏍️ Convoy Order: {destination} Expedition
        > *"{people} Riders | {bikes_needed} Bikes | {days} Days"*
        
        ---
        
        ## 🗺️ Route Strategy
        * **Outbound:** [Route A]
        * **Return:** [Route B (Circuit if possible)]
        * **Group Pace:** [Advice for keeping {bikes_needed} bikes together]
        
        ---
        
        ## 🛠️ Fleet Prep ({bike_model})
        * **Spares Kit:** [What to carry for {bikes_needed} bikes (shared spares?)]
        * **Mechanic:** [Should one rider carry advanced tools?]
        
        ---
        
        ## 📅 Group Itinerary
        * **Day 1:** [Start] -> [Stop] (Km) - [Hotel Advice for Group]
        ...
        
        ---
        
        ## ⛽ Logistics & Safety
        * **Fuel:** [Warning about filling {bikes_needed} tanks at once]
        * **Medical:** [AMS/First Aid for large group]
        
        ---
        
        > *Ride as a Pack. Arrive as a Pack.*
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Travel Tool Error: {str(e)}"

    def get_map_link(self, source: str, destination: str) -> str:
        s = source.replace(" ", "+")
        d = destination.replace(" ", "+")
        return f"https://www.google.com/maps/dir/{s}/{d}/{s}"

if __name__ == "__main__":
    tool = TravelTool()
    print(tool.plan_trip("Delhi", "Leh", "RE Classic 350", 12, 16))