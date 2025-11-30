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

# Initialize runner globally
runner = None

# --- GLOBAL INITIALIZATION ---
try:
    # CRITICAL CHECK: Ensure keys are present before initialization
    if os.getenv("GOOGLE_API_KEY") is None:
        # This will print to Render logs if the key is missing
        raise ValueError("CRITICAL ERROR: GOOGLE_API_KEY is not set in environment variables.")

    print("🔄 System Startup...")
    motomind = MotoMindAgent()
    
    # Initialize Runner: We rely on this object for all agent logic
    runner = InMemoryRunner(agent=motomind.agent, app_name="agents")
    
    print("✅ MotoMind Brain Loaded Successfully.")

except Exception as e:
    print("\n\n🔥 FATAL STARTUP CRASH! The AI Agent failed to load.")
    print(f"Error Details: {e}")
    traceback.print_exc()
    # Setting runner to None ensures endpoints return a safety message
    runner = None
    
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
    """Helper that runs the agent loop."""
    response_text = ""
    user_msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])
    
    async for event in runner.run_async(
        user_id="web_user", 
        session_id="live_session", 
        new_message=user_msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'text') and part.text:
                    response_text = part.text
    return response_text

async def run_agent_safe(prompt_text: str):
    """
    Self-Healing Runner: Ensures session exists before running the agent.
    """
    if runner is None:
        return "⚠️ SYSTEM ERROR: AI Brain failed to start. Check Render Environment Variables (API Key)."

    SESSION_ID = "live_session" 
    APP_NAME = "agents"
    USER_ID = "web_user"
    
    try:
        # 1. Check if session exists, if not, create it.
        # This handles server restarts gracefully.
        await runner.session_service.get_session(APP_NAME, USER_ID, SESSION_ID)
    except Exception:
        # Session not found? Create it immediately.
        await runner.session_service.create_session(APP_NAME, USER_ID, SESSION_ID)
    
    # 2. Execute the agent
    try:
        return await execute_agent_turn(prompt_text)
    except Exception as e:
        # Catch any subsequent runtime errors
        print(f"❌ RUNTIME ERROR: {e}")
        traceback.print_exc()
        return "I'm having trouble thinking right now. Please check the server logs."

@app.get("/")
def health_check():
    if runner is None:
        return {"status": "CRITICAL - Runner Failed to Load"}
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

@app.post("/plan_trip")
async def plan_trip(request: ChatRequest):
    try:
        data = request.message.split("|")
        tool = TravelTool()
        plan = tool.plan_trip(data[0], data[1], data[2], int(data[3]), int(data[4]))
        map_link = tool.get_map_link(data[0], data[1])
        return {"response": f"{plan}\n\n### 🗺️ Navigation\n👉 **[Click to Open Route in Google Maps]({map_link})**"}
    except Exception as e:
        print(f"❌ Trip Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diagnose/audio")
async def diagnose_audio(file: UploadFile = File(...), message: str = Form(...)):
    if runner is None: return {"response": "System Error: Agent not running."}
    
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        tool = AudioTool()
        raw = tool.diagnose_sound(temp_path)
        final = f"Audio Analysis Result: {raw}\nUser Question: {message}\nExplain this."
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)

@app.post("/diagnose/vision")
async def diagnose_vision(file: UploadFile = File(...), message: str = Form(...)):
    if runner is None: return {"response": "System Error: Agent not running."}

    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer: shutil.copyfileobj(file.file, buffer)
        tool = VisionTool()
        raw = tool.scan_bike(temp_path)
        final = f"Visual Scan Result: {raw}\nUser Question: {message}\nAnswer the user."
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path): os.remove(temp_path)