import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

class AudioTool:
    """
    The 'Ears' of MotoMind. Uploads audio to Gemini for acoustic diagnostics.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("⚠️ Error: GOOGLE_API_KEY not found.")
            return
        
        genai.configure(api_key=self.api_key)
        
        # UPDATED: Models available in your specific account
        self.model_candidates = [
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini-2.0-flash-lite',
            'gemini-1.5-flash'
        ]
        self._init_working_model()

    def _init_working_model(self):
        print(f"🔄 Initializing Audio Model (Targeting: {self.model_candidates[0]})...")
        self.model = genai.GenerativeModel(self.model_candidates[0])

    def diagnose_sound(self, audio_path: str) -> str:
        """
        Uploads an engine sound file and asks Gemini to diagnose it.
        """
        print(f"👂 AUDIO CALL: Listening to {audio_path}...")
        
        if not os.path.exists(audio_path):
            return f"Error: Audio file not found at {audio_path}"

        try:
            # 1. Upload the file to Google AI Studio
            print("   ...Uploading audio file to Gemini...")
            audio_file = genai.upload_file(path=audio_path)
            
            # 2. Wait for processing
            while audio_file.state.name == "PROCESSING":
                print("   ...Processing audio...")
                time.sleep(1)
                audio_file = genai.get_file(audio_file.name)

            if audio_file.state.name == "FAILED":
                return "Error: Audio processing failed on Google's side."

            # 3. The Diagnostic Prompt
            prompt = (
                "You are an expert mechanic with perfect acoustic pitch. "
                "Listen to this engine sound carefully. "
                "1. Describe the sound (e.g., clicking, deep knocking, hissing, smooth idle). "
                "2. Identify the mechanical issue (e.g., dead battery solenoid, rod knock, vacuum leak). "
                "3. Rate the severity (Low/Medium/High/Critical). "
                "4. Recommend the immediate next step."
            )

            # 4. Ask Gemini (with retry loop)
            last_error = None
            for model_name in self.model_candidates:
                try:
                    # print(f"   👉 Trying model: {model_name}...")
                    active_model = genai.GenerativeModel(model_name)
                    response = active_model.generate_content([prompt, audio_file])
                    return response.text
                except Exception as e:
                    # print(f"   ❌ Failed with {model_name}: {e}")
                    last_error = e
                    continue
            
            return f"Error: Could not analyze audio. Last error: {last_error}"

        except Exception as e:
            return f"Audio Tool Error: {str(e)}"

if __name__ == "__main__":
    tool = AudioTool()
    print(tool.diagnose_sound("data/audio_samples/dummy_engine.wav"))