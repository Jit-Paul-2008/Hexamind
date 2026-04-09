import subprocess
import sys
import os

def check_ollama():
    """Checks if Ollama is running and tiered models are available."""
    print("🛰️  Checking Lighter Aurora Hardware Readiness (1.5B/7B)...")
    
    models_to_check = ["deepseek-r1:1.5b", "deepseek-r1:7b"]
    
    try:
        # Check if ollama is in path
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
        print("✅ Ollama is installed.")
        
        # Check for models
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        
        for model in models_to_check:
            if model in result.stdout:
                print(f"✅ {model} is pulled and ready.")
            else:
                print(f"❌ {model} NOT found.")
                print(f"Action: Run 'ollama pull {model}' to initiate.")
            
    except subprocess.CalledProcessError:
        print("❌ Ollama service is not responding.")
        print("Action: Ensure Ollama is running in the background.")
    except FileNotFoundError:
        print("❌ Ollama binary not found in PATH.")

if __name__ == "__main__":
    check_ollama()
