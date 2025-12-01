import os
import shutil
import traceback
import inspect
import uuid
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Your agent + tools imports (same as before)
from agent import MotoMindAgent
from tools.audio_tool import AudioTool
from tools.vision_tool import VisionTool
from tools.maps_tool import MapsTool
from tools.travel_tool import TravelTool
from google.adk.runners import InMemoryRunner
from google.genai import types
# Import base64 to handle image data
import base64

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = None
ACTIVE_SESSION_ID: Optional[str] = None

# --- Initialization: create your agent + runner ---
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


class ChatRequest(BaseModel):
    message: str


async def _maybe_await(fn_or_val, *args, **kwargs):
    """Call fn_or_val if callable (supports sync/async functions). Otherwise return value."""
    try:
        if callable(fn_or_val):
            res = fn_or_val(*args, **kwargs)
        else:
            res = fn_or_val
        # if it's awaitable / coroutine, await it
        if inspect.isawaitable(res):
            return await res
        return res
    except Exception:
        raise


async def get_or_create_session():
    """
    Defensive session creation that supports multiple ADK versions.
    """
    global ACTIVE_SESSION_ID
    if runner is None:
        raise RuntimeError("Runner not initialized")

    APP_NAME = "agents"
    USER_ID = "web_user"
    svc = runner.session_service

    # 1) Verify existing session
    if ACTIVE_SESSION_ID:
        try:
            await _maybe_await(
                svc.get_session,
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=ACTIVE_SESSION_ID
            )
            return ACTIVE_SESSION_ID
        except Exception:
            print("⚠️ Active session missing or verification failed. Creating new one...")
            ACTIVE_SESSION_ID = None

    # 2) Method A: no-arg create_session()
    try:
        print("ℹ️ Creating new session (Method A: no args)...")
        session = await _maybe_await(svc.create_session)
        if session is not None and hasattr(session, "id"):
            ACTIVE_SESSION_ID = session.id
        elif isinstance(session, str) and session:
            ACTIVE_SESSION_ID = session
        else:
            ACTIVE_SESSION_ID = f"session_{uuid.uuid4().hex[:8]}"
        print("✅ Created session (A):", ACTIVE_SESSION_ID)
        return ACTIVE_SESSION_ID
    except Exception as e:
        print("⚠️ Method A failed:", e)

    # 3) Method B: keyword args
    try:
        print("ℹ️ Creating new session (Method B: keywords)...")
        new_id = f"session_{uuid.uuid4().hex[:8]}"
        session = await _maybe_await(
            svc.create_session,
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=new_id
        )
        if session is not None and hasattr(session, "id"):
            ACTIVE_SESSION_ID = session.id
        else:
            ACTIVE_SESSION_ID = new_id
        print("✅ Created session (B):", ACTIVE_SESSION_ID)
        return ACTIVE_SESSION_ID
    except Exception as e:
        print("⚠️ Method B failed:", e)

    # 4) Method C: positional (last resort)
    try:
        print("ℹ️ Creating new session (Method C: positional fallback)...")
        session = await _maybe_await(svc.create_session, APP_NAME, USER_ID, f"session_{uuid.uuid4().hex[:8]}")
        if session is not None and hasattr(session, "id"):
            ACTIVE_SESSION_ID = session.id
        else:
            # If it fails to return an object but doesn't crash, generate a fallback ID
            ACTIVE_SESSION_ID = f"session_{uuid.uuid4().hex[:8]}"
        print("✅ Created session (C):", ACTIVE_SESSION_ID)
        return ACTIVE_SESSION_ID
    except Exception as e:
        print("⛔ All session creation methods failed.")
        raise RuntimeError(f"Could not create session. Errors: {e}")


async def run_agent_safe(prompt_text: str):
    """
    Run the agent with a valid session. Returns the plain text response.
    On error: reset ACTIVE_SESSION_ID and return user-friendly message (no crashes).
    """
    if runner is None:
        return "⚠️ System Error: Agent not running. Check logs."

    try:
        # Step 1: Get a valid Session ID
        session_id = await get_or_create_session()
        response_text = ""
        user_msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])

        # runner.run_async is expected to be async-iterable. Support both async-iterable and sync iterable.
        async for event in runner.run_async(
            user_id="web_user",
            session_id=session_id,
            new_message=user_msg
        ):
            # event.content.parts is expected; gather the latest non-empty .text
            if event and getattr(event, "content", None) and getattr(event.content, "parts", None):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text if not response_text else ("\n" + part.text)
        # Ensure at least something meaningful is returned
        if not response_text:
            return "I processed your request but didn't generate a detailed answer. Try rephrasing or ask again."
        return response_text
    except Exception as e:
        print("❌ RUNTIME ERROR in run_agent_safe:", e)
        traceback.print_exc()
        # Reset session on crash to force clean start next time
        global ACTIVE_SESSION_ID
        ACTIVE_SESSION_ID = None
        return "I encountered a glitch. Please try again."


@app.get("/")
def health_check():
    return {"status": "MotoMind Brain is Active"}


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Expects JSON: { "message": "..." }
    Returns: { "response": "plain text string", "images": [optional urls] }
    """
    try:
        prompt = request.message
        result = await run_agent_safe(prompt)
        # Always return plain text in "response"
        return {"response": result, "images": []}
    except Exception as e:
        print("ERROR /chat:", e)
        traceback.print_exc()
        return {"response": "⚠️ System Error: Could not process chat request.", "images": []}


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
        # tool returns string; keep it plain
        return {"response": str(result), "images": []}
    except Exception as e:
        print("ERROR /find_mechanics:", e)
        return {"response": f"Error: {str(e)}", "images": []}


@app.post("/plan_trip")
async def plan_trip(request: ChatRequest):
    try:
        data = request.message.split("|")
        if len(data) < 5:
            return {"response": "Invalid trip payload. Expected format: from|to|bike|days|riders", "images": []}
        tool = TravelTool()
        plan = tool.plan_trip(data[0], data[1], data[2], int(data[3]), int(data[4]))
        map_link = tool.get_map_link(data[0], data[1])
        combined = f"{plan}\n\n### 🗺️ Navigation\n👉 **Open route:** {map_link}"
        return {"response": combined, "images": []}
    except Exception as e:
        print("ERROR /plan_trip:", e)
        traceback.print_exc()
        return {"response": f"Error: {str(e)}", "images": []}


@app.post("/diagnose/audio")
async def diagnose_audio(file: UploadFile = File(...), message: str = Form(...)):
    """
    Expects multipart/form-data with fields:
      - file: audio file
      - message: textual context (string)
    Returns:
      { "response": "<plain text answer>", "images": [] }
    """
    if runner is None:
        return {"response": "System Error: Agent not running.", "images": []}

    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        tool = AudioTool()
        # tool.diagnose_sound should return a string summary; convert to string to be safe
        raw = tool.diagnose_sound(temp_path)
        if not isinstance(raw, str):
            raw = str(raw)
        final = f"Audio Analysis Result: {raw}\nUser Question: {message}\nExplain this."
        # Ask agent to explain the result (optional)
        explanation = await run_agent_safe(final)
        return {"response": explanation, "images": []}
    except Exception as e:
        print("ERROR /diagnose/audio:", e)
        traceback.print_exc()
        return {"response": f"Error processing audio: {e}", "images": []}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/diagnose/vision")
async def diagnose_vision(file: UploadFile = File(...), message: str = Form(...)):
    """
    Expects multipart/form-data with:
      - file: image
      - message: textual context
    Returns:
      { "response": "<plain text answer>", "images": [optional urls] }
    """
    if runner is None:
        return {"response": "System Error: Agent not running.", "images": []}

    temp_path = f"temp_{file.filename}"
    try:
        # 1. Save the file locally temporarily
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. Run Vision Tool
        tool = VisionTool()
        raw = tool.scan_bike(temp_path)  # may be string or dict
        
        # 3. Process Agent Explanation
        final_text = ""
        image_url = None

        if isinstance(raw, dict):
            # try to extract message + image url if present
            text = raw.get("text") or raw.get("description") or str(raw)
            # Ensure we extract a usable image string if the tool provides one
            image_url = raw.get("images") or raw.get("image_urls")
            final_text = f"Visual Scan Result: {text}\nUser Question: {message}\nAnswer the user."
        else:
            txt = str(raw)
            final_text = f"Visual Scan Result: {txt}\nUser Question: {message}\nAnswer the user."

        explanation = await run_agent_safe(final_text)

        # 4. RETURN THE IMAGE TO THE FRONTEND
        # Since we don't have a permanent cloud storage bucket for this demo,
        # we will return the SAME image data back to the frontend as a base64 string
        # so it can display it.
        
        # Read file bytes
        with open(temp_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create a data URL
        data_url = f"data:image/jpeg;base64,{encoded_string}"
        
        # Return response with the image data URL
        return {"response": explanation, "images": [data_url]}

    except Exception as e:
        print("ERROR /diagnose/vision:", e)
        traceback.print_exc()
        return {"response": f"Error processing image: {e}", "images": []}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)