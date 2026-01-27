"""Quick start script."""
import subprocess
import sys
import os

def main():
    """Run Streamlit app."""
    app_path = os.path.join("app", "streamlit_app.py")
    if not os.path.exists(app_path):
        print(f"Error: {app_path} not found")
        sys.exit(1)
    
    print("Starting AI Interview System...")
    print("=" * 50)
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])

if __name__ == "__main__":
    main()

