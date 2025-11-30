from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types
import os

# Import ALL tools
from tools.maps_tool import MapsTool
from tools.vision_tool import VisionTool
from tools.audio_tool import AudioTool
from tools.travel_tool import TravelTool # <--- NEW
from tools.search_tool import SearchTool

class MotoMindAgent:
    def __init__(self, model_name="gemini-2.5-flash-lite"):
        self.persona = """
        You are MotoMind, the ultimate riding companion and mechanic.
        
        CORE CAPABILITIES:
        1. **TRIP PLANNER:** If user wants to travel (e.g. "Plan a trip to Ladakh"), use `plan_trip`.
           - ALWAYS provide the Google Maps link at the end.
           
        2. **DIAGNOSE:** Use 'scan_bike' (Vision) or 'diagnose_sound' (Audio) for problems.
        3. **VISUALS:** Use 'search_part_image' if they ask to see a part.
        4. **LOCATE:** Use 'find_nearby_mechanic' for immediate help.
        
        Speak like a pro rider. Be encouraging but safety-first.
        """
        
        # Initialize Tools
        maps = MapsTool()
        vision = VisionTool()
        audio = AudioTool()
        travel = TravelTool() # <--- NEW
        search = SearchTool()
        
        # Wrap as ADK Tools
        self.tools_list = [
            FunctionTool(func=maps.find_nearby_mechanic),
            FunctionTool(func=vision.scan_bike),
            FunctionTool(func=audio.diagnose_sound),
            FunctionTool(func=travel.plan_trip),      # <--- NEW
            FunctionTool(func=travel.get_map_link),   # <--- NEW
            FunctionTool(func=search.search_part_image)
        ]
        
        # Create Agent
        self.agent = LlmAgent(
            model=Gemini(model=model_name),
            name="MotoMind",
            instruction=self.persona,
            tools=self.tools_list
        )
        print(f"✅ MotoMind Agent Initialized with {len(self.tools_list)} tools.")

if __name__ == "__main__":
    bot = MotoMindAgent()