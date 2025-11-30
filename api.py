from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import MotoMindAgent
from tools.audio_tool import AudioTool
from tools.vision_tool import VisionTool
from tools.maps_tool import MapsTool
from tools.travel_tool import TravelTool
from google.adk.runners import InMemoryRunner
from google.genai import types
import shutil
import os
import traceback

app = FastAPI()

# --- GLOBAL INITIALIZATION ---
try:
    print("🔄 System Startup...")
    motomind = MotoMindAgent()
    runner = InMemoryRunner(agent=motomind.agent, app_name="agents")
    print("✅ MotoMind Ready.")
except Exception as e:
    print("🔥 FATAL STARTUP ERROR:")
    traceback.print_exc()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

async def execute_agent_turn(prompt_text: str):
    response_text = ""
    user_msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])
    async for event in runner.run_async(user_id="web_user", session_id="live_session", new_message=user_msg):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text = part.text
    return response_text

async def run_agent_safe(prompt_text: str):
    try:
        return await execute_agent_turn(prompt_text)
    except Exception as e:
        if "Session not found" in str(e):
            print(f"ℹ️ Re-creating session...")
            await runner.session_service.create_session(app_name="agents", user_id="web_user", session_id="live_session")
            return await execute_agent_turn(prompt_text)
        else:
            print(f"❌ ERROR: {e}")
            return "System Error. Please check logs."

@app.get("/")
def health_check():
    return {"status": "MotoMind Brain is Active"}

@app.post("/chat")
async def chat(request: ChatRequest):
    return {"response": await run_agent_safe(request.message)}

@app.post("/find_mechanics")
async def find_mechanics(request: ChatRequest):
    try:
        content = request.message
        location = "India"
        bike = "Motorcycle"
        if "|" in content:
            parts = content.split("|")
            location = parts[0].replace("User Location:", "").strip()
            bike = parts[1].replace("Bike:", "").strip()
        tool = MapsTool()
        return {"response": tool.find_nearby_mechanic(location, bike)}
    except Exception:
        return {"response": "Error finding mechanics."}

@app.post("/plan_trip")
async def plan_trip(request: ChatRequest):
    try:
        data = request.message.split("|")
        tool = TravelTool()
        plan = tool.plan_trip(data[0], data[1], data[2], int(data[3]), int(data[4]))
        link = tool.get_map_link(data[0], data[1])
        return {"response": f"{plan}\n\n### 🗺️ Navigation\n👉 **[Click to Open Route in Google Maps]({link})**"}
    except Exception:
        return {"response": "Error planning trip."}

@app.post("/diagnose/audio")
async def diagnose_audio(file: UploadFile = File(...), message: str = Form(...)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        tool = AudioTool()
        raw = tool.diagnose_sound(temp_path)
        
        # FIXED PROMPT: Force the AI to own the data
        final = f"""
        INTERNAL DATA FROM YOUR AUDIO TOOL: "{raw}"
        USER QUESTION: "{message}"
        
        INSTRUCTIONS: 
        1. The data above comes from YOUR EARS (the Audio Tool). Do NOT compliment the analysis. 
        2. Present the diagnosis to the user as YOUR professional opinion. 
        3. Be direct and helpful.
        """
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@app.post("/diagnose/vision")
async def diagnose_vision(file: UploadFile = File(...), message: str = Form(...)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        tool = VisionTool()
        raw = tool.scan_bike(temp_path)
        
        # FIXED PROMPT: Force the AI to own the data
        final = f"""
        INTERNAL DATA FROM YOUR VISION TOOL: "{raw}"
        USER QUESTION: "{message}"
        
        INSTRUCTIONS: 
        1. The data above comes from YOUR EYES (the Vision Tool). Do NOT compliment the analysis.
        2. Present the findings to the user as YOUR professional opinion.
        3. Format nicely with Markdown.
        """
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)