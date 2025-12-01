# api.py
from fastapi import FastAPI, UploadFile, File, Form
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
import inspect
import asyncio

app = FastAPI()
runner = None
# GLOBAL VARIABLE TO HOLD THE ACTIVE SESSION
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


async def _maybe_await(callable_or_result, *args, **kwargs):
    """
    Accepts either:
      - a callable to be executed (sync or async)
      - OR a value (already the result)
    If callable_or_result is callable, call it with args/kwargs.
    If the returned value is awaitable, await it.
    Returns the final result.
    """
    try:
        if callable(callable_or_result):
            res = callable_or_result(*args, **kwargs)
        else:
            res = callable_or_result
        if inspect.isawaitable(res):
            return await res
        return res
    except Exception:
        # Re-raise to be handled by caller
        raise


async def get_or_create_session():
    """
    Smart Session Handler:
    1. Checks if we already have a session.
    2. If not, asks the runner to create one (using whatever method it prefers).
    3. Saves the ID for next time.

    This implementation is defensive:
      - uses keyword args for ADK versions that expect them
      - tries no-arg create_session()
      - tries explicit keyword create_session(...)
      - supports sync or async session_service methods
    """
    global ACTIVE_SESSION_ID

    if runner is None:
        raise RuntimeError("Runner is not initialized.")

    # Identifiers for the user
    APP_NAME = "agents"
    USER_ID = "web_user"

    # 1. If we already have a session ID, try to verify it exists
    if ACTIVE_SESSION_ID:
        try:
            svc = runner.session_service
            # attempt to call get_session using keyword args; support sync/async
            await _maybe_await(svc.get_session, app_name=APP_NAME, user_id=USER_ID, session_id=ACTIVE_SESSION_ID)
            return ACTIVE_SESSION_ID
        except Exception:
            print("⚠️ Active session lost or verification failed. Creating new one...")
            ACTIVE_SESSION_ID = None  # Reset

    svc = runner.session_service

    # Debug: print signature and type to logs so we can see what implementation we have
    try:
        print("session_service type:", type(svc))
        if hasattr(svc, "create_session"):
            print("create_session signature:", inspect.signature(svc.create_session))
        if hasattr(svc, "get_session"):
            print("get_session signature:", inspect.signature(svc.get_session))
    except Exception:
        # don't fail if introspection fails
        pass

    # 2. Try create_session() with no args (some ADK examples use this)
    try:
        print("ℹ️ Creating new session (Method A: Empty args)...")
        session = await _maybe_await(svc.create_session)
        if session is not None and hasattr(session, "id"):
            ACTIVE_SESSION_ID = session.id
        elif isinstance(session, str) and session:
            ACTIVE_SESSION_ID = session
        else:
            # session may be None but creation succeeded; create a fallback id and try to register it
            print("ℹ️ Method A returned no session object; using fallback id.")
            ACTIVE_SESSION_ID = "live_session_fallback_a"
        print(f"✅ Created Session (Method A): {ACTIVE_SESSION_ID}")
        return ACTIVE_SESSION_ID
    except Exception as e:
        print(f"⚠️ Method A failed ({e}). Trying Method B (Explicit keyword args)...")
        # fall-through to Method B

    # 3. Try create_session with explicit keyword args (works with keyword-only implementations)
    try:
        new_id = "live_session_backup"
        print("ℹ️ Creating new session (Method B: explicit keywords)...")
        session = await _maybe_await(
            svc.create_session,
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=new_id
        )
        if session is not None and hasattr(session, "id"):
            ACTIVE_SESSION_ID = session.id
        else:
            # If the implementation doesn't return a session object, assume creation succeeded and use new_id
            ACTIVE_SESSION_ID = new_id
        print(f"✅ Created Session (Method B): {ACTIVE_SESSION_ID}")
        return ACTIVE_SESSION_ID
    except Exception as e:
        # 4. Last ditch: try positional (some VERY old/strange implementations might accept it)
        try:
            print("ℹ️ Trying Method C: positional fallback (last resort)...")
            session = await _maybe_await(svc.create_session, APP_NAME, USER_ID, "live_session_positional")
            if session is not None and hasattr(session, "id"):
                ACTIVE_SESSION_ID = session.id
            else:
                ACTIVE_SESSION_ID = "live_session_positional"
            print(f"✅ Created Session (Method C): {ACTIVE_SESSION_ID}")
            return ACTIVE_SESSION_ID
        except Exception as e2:
            raise RuntimeError(f"Could not create session. All methods failed. Errors: MethodB: {e}; MethodC: {e2}")


async def run_agent_safe(prompt_text: str):
    """
    Runs the agent using the runner while ensuring we have a valid session.
    Resets the ACTIVE_SESSION_ID on error so next call attempts a fresh session creation.
    """
    if runner is None:
        return "⚠️ System Error: Agent not running. Check logs."

    try:
        # Step 1: Get a valid Session ID
        session_id = await get_or_create_session()

        # Step 2: Run the Agent
        response_text = ""
        user_msg = types.Content(role="user", parts=[types.Part(text=prompt_text)])

        # runner.run_async is expected to be async-iterable. Support both async-iterable and sync iterable.
        async for event in runner.run_async(
            user_id="web_user",
            session_id=session_id,
            new_message=user_msg
        ):
            if event and getattr(event, "content", None) and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text = part.text
        return response_text

    except Exception as e:
        print(f"❌ RUNTIME ERROR in run_agent_safe: {e}")
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
    if runner is None:
        return {"response": "System Error: Agent not running."}
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        tool = AudioTool()
        raw = tool.diagnose_sound(temp_path)
        final = f"Audio Analysis Result: {raw}\nUser Question: {message}\nExplain this."
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/diagnose/vision")
async def diagnose_vision(file: UploadFile = File(...), message: str = Form(...)):
    if runner is None:
        return {"response": "System Error: Agent not running."}
    temp_path = f"temp_{file.filename}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        tool = VisionTool()
        raw = tool.scan_bike(temp_path)
        final = f"Visual Scan Result: {raw}\nUser Question: {message}\nAnswer the user."
        return {"response": await run_agent_safe(final)}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
