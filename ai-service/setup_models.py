import subprocess
import sys
import os

def check_ollama():
    """Checks if Ollama is running and the deepseek-r1:14b model is available."""
    print("🛰️  Checking Aurora v4 Hardware Readiness...")
    
    try:
        # Check if ollama is in path
        subprocess.run(["ollama", "--version"], capture_output=True, check=True)
        print("✅ Ollama is installed.")
        
        # Check for model
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        if "deepseek-r1:14b" in result.stdout:
            print("✅ DeepSeek-R1 (14B) is pulled and ready.")
        else:
            print("❌ DeepSeek-R1 (14B) NOT found.")
            print("Action: Run 'ollama pull deepseek-r1:14b' manually to initiate the brain.")
            
    except subprocess.CalledProcessError:
        print("❌ Ollama service is not responding.")
        print("Action: Ensure Ollama is running in the background.")
    except FileNotFoundError:
        print("❌ Ollama binary not found in PATH.")

if __name__ == "__main__":
    check_ollama()
