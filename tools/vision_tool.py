import os
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# Load environment variables
load_dotenv()

class VisionTool:
    """
    The 'Eyes' of MotoMind. Uses Gemini Vision to analyze bike photos.
    """
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            print("⚠️ Error: GOOGLE_API_KEY not found in .env")
            return
            
        # Configure the Gemini Vision model
        genai.configure(api_key=self.api_key)
        
        # UPDATED LIST based on your check_models.py output
        self.model_candidates = [
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini-2.0-flash-lite',
            'gemini-2.0-pro-exp'
        ]
        self.model = None
        self._init_working_model()

    def _init_working_model(self):
        """
        Sets the default model to the first candidate.
        """
        print(f"🔄 Initializing Vision Model (Targeting: {self.model_candidates[0]})...")
        self.model = genai.GenerativeModel(self.model_candidates[0])

    def scan_bike(self, image_path: str) -> str:
        """
        Analyzes a bike image to identify the model and visual issues.
        """
        # Clean path just in case
        clean_path = image_path.replace("ddata", "data")
        print(f"👁️ VISION CALL: Analyzing image at {clean_path}...")
        
        if not os.path.exists(clean_path):
            return f"Error: Image file not found at {clean_path}"
            
        img = Image.open(clean_path)
        
        # The Prompt
        prompt = (
            "Act as an expert motorcycle mechanic. Analyze this image. "
            "1. Identify the Bike: Make, Model, and estimated Year. "
            "2. Visual Inspection: List any visible modifications, damage, rust, or wear. "
            "3. Verdict: Is it stock or modified? "
            "Provide the response in a clean, structured format."
        )

        # RETRY LOOP
        last_error = None
        for model_name in self.model_candidates:
            try:
                # print(f"   👉 Trying model: {model_name}...")
                active_model = genai.GenerativeModel(model_name)
                response = active_model.generate_content([prompt, img])
                return response.text
                
            except Exception as e:
                # print(f"   ❌ Failed with {model_name}...")
                last_error = e
                continue
        
        return f"Vision Error: Could not find a working model. Last error: {str(last_error)}"

if __name__ == "__main__":
    tool = VisionTool()
    print(tool.scan_bike("data/test_bike.jpg"))