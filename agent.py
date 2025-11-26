# agent.py
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types
import os

# Import ALL tools
from tools.maps_tool import MapsTool
from tools.vision_tool import VisionTool
from tools.audio_tool import AudioTool    # <--- NEW IMPORT

class MotoMindAgent:
    def __init__(self, model_name="gemini-2.5-flash-lite"):
        self.persona = (
            "You are MotoMind, an expert Indian motorcycle mechanic. "
            "You are bilingual (English/Hindi). "
            "Your goal is to help users diagnose bike problems. "
            "1. If the user sends an image, use 'scan_bike'. "
            "2. If the user sends an audio recording, use 'diagnose_sound'. "
            "3. If the user needs a mechanic, use 'find_nearby_mechanic'. "
        )
        
        # 1. Initialize Tools
        maps = MapsTool()
        vision = VisionTool()
        audio = AudioTool()  # <--- NEW
        
        # 2. Wrap as ADK Tools
        find_mechanic_tool = FunctionTool(func=maps.find_nearby_mechanic)
        scan_bike_tool = FunctionTool(func=vision.scan_bike)
        diagnose_sound_tool = FunctionTool(func=audio.diagnose_sound) # <--- NEW
        
        # 3. Create Agent with ALL 3 tools
        self.agent = LlmAgent(
            model=Gemini(model=model_name),
            name="MotoMind",
            instruction=self.persona,
            tools=[find_mechanic_tool, scan_bike_tool, diagnose_sound_tool]
        )
        print("✅ MotoMind Agent Initialized (Maps + Vision + Audio).")

if __name__ == "__main__":
    bot = MotoMindAgent()
    print(f"Agent ready with {len(bot.agent.tools)} tools.")