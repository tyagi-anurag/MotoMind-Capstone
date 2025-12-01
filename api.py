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
runner = None
# GLOBAL VARIABLE TO HOLD THE ACTIVE SESSION
# We let the system generate this, so we never guess wrong.
ACTIVE_SESSION_ID = None 

# --- GLOBAL INITIALIZATION ---
try:
    if os.getenv("GOOGLE_API_KEY") is None:
        raise ValueError("CRITICAL ERROR: GOOGLE_API_KEY is not set.")

    print("🔄 System Startup...")
    motomind = MotoMindAgent()
    runner = InMemoryRunner(agent=motomind.agent, app_name="agents")
    print("✅ MotoMind Brain Loaded.")

except Exception as e:
    print(f"🔥 FATAL STARTUP ERROR: {e}")
    traceback.print_exc()
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

async def get_or_create_session():
    """
    Smart Session Handler:
    1. Checks if we already have a session.
    2. If not, asks the runner to create one (using whatever method it prefers).
    3. Saves the ID for next time.
    """
    global ACTIVE_SESSION_ID
    
    # Identifiers for the user
    APP_NAME = "agents"
    USER_ID = "web_user"

    # 1. If we already have a session ID, try to verify it exists
    if ACTIVE_SESSION_ID:
        try:
            await runner.session_service.get_session(APP_NAME, USER_ID, ACTIVE_SESSION_ID)
            return ACTIVE_SESSION_ID
        except Exception:
            print("⚠️ Active session lost. Creating new one...")
            ACTIVE_SESSION_ID = None # Reset

    # 2. Create a new session using the "No Arguments" method (Fixes the TypeError)
    try:
        print("ℹ️ Creating new session (Method A: Empty)...")
        # This fixes the "takes 1 argument but 2 given" error
        session = await runner.session_service.create_session()
        ACTIVE_SESSION_ID = session.id
        print(f"✅ Created Session: {ACTIVE_SESSION_ID}")
        return ACTIVE_SESSION_ID
    except Exception as e:
        print(f"⚠️ Method A failed ({e}). Trying Method B (Explicit)...")
        
    # 3. Fallback: Create using explicit arguments (For different ADK versions)
    try:
        new_id = "live_session_backup"
        await runner.session_service.create_session(APP_NAME, USER_ID, new_id)
        ACTIVE_SESSION_ID = new_id
        return ACTIVE_SESSION_ID
    except Exception as e:
        raise RuntimeError(f"Could not create session. All methods failed. Error: {e}")

async def run_agent_safe(prompt_text: str):
    if runner is None:
        return "⚠️ System Error: Agent not running. Check logs."

    try:
        # Step 1: Get a valid Session ID
        session_id = await get_or_create_session()
        
        # Step 2: Run the Agent
        response_text = ""
        user_msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])
        
        async for event in runner.run_async(
            user_id="web_user", 
            session_id=session_id, 
            new_message=user_msg
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response_text = part.text
        return response_text

    except Exception as e:
        print(f"❌ RUNTIME ERROR: {e}")
        traceback.print_exc()
        # Reset session on crash to force a clean slate next time
        global ACTIVE_SESSION_ID
        ACTIVE_SESSION_ID = None 
        return "I encountered a glitch. Please ask me that again."

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
        return {"response": f"Error: {str(e)}"}

@app.post("/plan_trip")
async def plan_trip(request: ChatRequest):
    try:
        data = request.message.split("|")
        tool = TravelTool()
        plan = tool.plan_trip(data[0], data[1], data[2], int(data[3]), int(data[4]))
        map_link = tool.get_map_link(data[0], data[1])
        return {"response": f"{plan}\n\n### 🗺️ Navigation\n👉 **[Click to Open Route in Google Maps]({map_link})**"}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}

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