# agent.py
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types
import os

# Import our tools
from tools.maps_tool import MapsTool
from tools.vision_tool import VisionTool  # <--- NEW IMPORT

class MotoMindAgent:
    def __init__(self, model_name="gemini-2.5-flash-lite"):
        self.persona = (
            "You are MotoMind, an expert Indian motorcycle mechanic. "
            "You are bilingual (English/Hindi). "
            "Your goal is to help users diagnose bike problems. "
            "1. If the user sends an image, use the 'scan_bike' tool to analyze it. "
            "2. If the user needs a mechanic, use 'find_nearby_mechanic'. "
        )
        
        # 1. Initialize Tools
        maps = MapsTool()
        vision = VisionTool()
        
        # 2. Wrap as ADK Tools
        find_mechanic_tool = FunctionTool(func=maps.find_nearby_mechanic)
        scan_bike_tool = FunctionTool(func=vision.scan_bike)
        
        # 3. Create Agent with BOTH tools
        self.agent = LlmAgent(
            model=Gemini(model=model_name),
            name="MotoMind",
            instruction=self.persona,
            tools=[find_mechanic_tool, scan_bike_tool]
        )
        print("✅ MotoMind Agent Initialized (with Maps & Vision).")

if __name__ == "__main__":
    # Test connection
    bot = MotoMindAgent()
    print(f"Agent ready with {len(bot.agent.tools)} tools.")
    
    # Optional: Simulate an image scan if you want to test the agent logic
    # print(bot.agent.run("Analyze this bike image: data/test_bike.jpg"))