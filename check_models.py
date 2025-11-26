# check_models.py
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

print("🔍 Checking available models for your API key...")
print("-" * 40)

try:
    # List all models that support 'generateContent' (chat/vision)
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Found: {m.name}")
            
    print("-" * 40)
    print("Use one of the names above (without 'models/') in your vision_tool.py")

except Exception as e:
    print(f"❌ Error listing models: {str(e)}")