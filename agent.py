# agent.py
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import FunctionTool
from google.genai import types
from tools.maps_tool import MapsTool  # Import the tool we made

class MotoMindAgent:
    def __init__(self, model_name="gemini-2.5-flash-lite"):
        self.persona = (
            "You are MotoMind, an expert Indian motorcycle mechanic. "
            "You are bilingual (English/Hindi). "
            "Use your tools to find mechanics when the user asks."
        )
        
        # 1. Initialize the Map Tool
        maps = MapsTool()
        
        # 2. Convert it to an ADK FunctionTool
        find_mechanic_tool = FunctionTool(
            func=maps.find_nearby_mechanic
        )
        
        # 3. Create the Agent with the Tool
        self.agent = LlmAgent(
            model=Gemini(model=model_name),
            name="MotoMind",
            instruction=self.persona,
            tools=[find_mechanic_tool]  # Give the tool to the agent
        )
        print("✅ MotoMind Agent Initialized (with Maps Tool).")

if __name__ == "__main__":
    # Test it
    bot = MotoMindAgent()
    print("Agent is ready.")