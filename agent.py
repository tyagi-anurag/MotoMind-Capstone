from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types
import os

# Import ONLY the active tools (No Garage!)
from tools.maps_tool import MapsTool
from tools.vision_tool import VisionTool
from tools.audio_tool import AudioTool
from tools.travel_tool import TravelTool
from tools.search_tool import SearchTool

class MotoMindAgent:
    def __init__(self, model_name="gemini-2.5-flash-lite"):
        self.persona = """
        You are MotoMind, an expert Indian motorcycle mechanic and riding companion.
        
        CAPABILITIES:
        1. **DIAGNOSE:** If sent an image ('scan_bike') or audio ('diagnose_sound'), analyze it.
           - Use specific mechanical terms (e.g. "Tappet noise", "Rich mixture").
        2. **PLAN TRIPS:** If asked about travel, use 'plan_trip' to generate itineraries.
        3. **LOCATE:** Use 'find_nearby_mechanic' if the user needs help.
        4. **VISUALS:** If asked "Show me X", use 'search_part_image'.
        
        TONE: Helpful, safety-first, professional but conversational.
        """
        
        # Initialize Tools
        maps = MapsTool()
        vision = VisionTool()
        audio = AudioTool()
        travel = TravelTool()
        search = SearchTool()
        
        # Wrap as ADK Tools
        self.tools_list = [
            FunctionTool(func=maps.find_nearby_mechanic),
            FunctionTool(func=vision.scan_bike),
            FunctionTool(func=audio.diagnose_sound),
            FunctionTool(func=travel.plan_trip),
            FunctionTool(func=travel.get_map_link),
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