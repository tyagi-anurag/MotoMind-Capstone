from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.genai import types

# We will import the other agents later, for now we just set up the supervisor
# from .mechanic_agent import MechanicAgent
# from .travel_agent import TravelAgent

class MotoMindSupervisor:
    """
    The Main Brain of MotoMind. 
    It acts as a router, sending the user to either the Mechanic or the Travel companion.
    """
    def __init__(self, model_name="gemini-2.5-flash-lite"):
        
        self.persona = """
        You are MotoMind, the ultimate motorcycle AI assistant.
        Your job is to ROUTE the user to the right specialist.
        
        You have two modes:
        1. MECHANIC MODE: If the user talks about breakdowns, noises, parts, repairs, or mechanics.
        2. TRAVEL MODE: If the user talks about trips, routes, weather, or safety monitoring.
        
        Listen to the user and decide which mode is needed.
        """
        
        self.agent = LlmAgent(
            name="MotoMind_Supervisor",
            model=Gemini(model=model_name),
            description="Root agent that routes tasks.",
            instruction=self.persona
        )
        print("✅ MotoMind Supervisor Initialized.")

if __name__ == "__main__":
    # Simple test to check if it loads
    bot = MotoMindSupervisor()