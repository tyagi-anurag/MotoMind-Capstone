from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import MotoMindAgent
from tools.audio_tool import AudioTool
from tools.vision_tool import VisionTool
from tools.maps_tool import MapsTool
from tools.travel_tool import TravelTool # <--- ENSURE THIS IS HERE
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
    
    # Initialize Runner
    runner = InMemoryRunner(agent=motomind.agent, app_name="agents")
    
    print("✅ MotoMind Ready: Travel, Maps, Vision, Audio active.")

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

async def run_agent_safe(prompt_text: str):
    response_text = ""
    APP_NAME = "agents"
    USER_ID = "web_user"
    SESSION_ID = "live_session"
    
    try:
        # Ensure session exists
        try:
            await runner.session_service.create_session(APP_NAME, USER_ID, SESSION_ID)
        except Exception:
            pass

        # Run Agent
        user_msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])
        async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=user_msg):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text = part.text
        return response_text
    except Exception as e:
        print(f"❌ AGENT ERROR: {e}")
        return "I'm having trouble thinking right now. Please check the server logs."

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
        result = tool.find_nearby_mechanic(location, bike)
        return {"response": result}
    except Exception as e:
        print(f"❌ Maps Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- THIS IS THE MISSING PART THAT CAUSED THE 404 ---
@app.post("/plan_trip")
async def plan_trip(request: ChatRequest):
    """
    Endpoint for Trip Planning
    """
    try:
        data = request.message.split("|")
        source, dest, bike, days, people = data[0], data[1], data[2], data[3], data[4]
        
        print(f"🛣️ Planning Trip: {source} -> {dest}")
        tool = TravelTool()
        
        # Get Plan
        plan = tool.plan_trip(source, dest, bike, int(days), int(people))
        # Get Map Link
        map_link = tool.get_map_link(source, dest)
        
        final_response = f"{plan}\n\n### 🗺️ Navigation\n👉 **[Click to Open Route in Google Maps]({map_link})**"
        return {"response": final_response}
    except Exception as e:
        print(f"❌ Trip Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ----------------------------------------------------

@app.post("/diagnose/audio")
async def diagnose_audio(file: UploadFile = File(...), message: str = Form(...)):
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        tool = AudioTool()
        raw = tool.diagnose_sound(temp_path)
        final = f"Audio Analysis: {raw}\nUser Question: {message}\nExplain this."
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
        final = f"Visual Scan: {raw}\nUser Question: {message}\nExplain this."
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)