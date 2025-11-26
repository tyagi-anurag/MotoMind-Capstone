import os
from tools.audio_tool import AudioTool

def run_audio_test_suite():
    print("🎧 STARTING MOTOMIND AUDIO DIAGNOSTIC TEST SUITE")
    print("="*60)
    
    # Initialize the tool once
    tool = AudioTool()
    
    # List of test files
    test_files = [
        "data/audio_samples/dead_battery.mp3",
        "data/audio_samples/rod_knock.mp3",
        "data/audio_samples/vacuum_leak.mp3"
    ]
    
    for file_path in test_files:
        print(f"\n🔍 TESTING FILE: {file_path}")
        print("-" * 30)
        
        if os.path.exists(file_path):
            # Run the diagnosis
            result = tool.diagnose_sound(file_path)
            print(f"🤖 DIAGNOSIS:\n{result}")
        else:
            print(f"⚠️ FILE NOT FOUND: {file_path}")
            print("   (Did you rename it correctly?)")
            
    print("\n" + "="*60)
    print("✅ TEST SUITE COMPLETE")

if __name__ == "__main__":
    run_audio_test_suite()