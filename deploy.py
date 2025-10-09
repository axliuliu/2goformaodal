import modal
import sys
import os

app = modal.App(name="persistent-app-v2")

# Define the image with necessary system packages (curl) 
# and Python dependencies from requirements.txt.
image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .pip_install_from_requirements("requirements.txt")
    # Add the local directory (which contains app.py) to the remote workspace
    .add_local_dir(".", remote_path="/workspace")
)

# MODIFIED: Use a function structure that supports long-running service.
# Set a very long timeout (e.g., 1 year) and keep_warm to simulate persistence.
@app.function(
    image=image,
    timeout=86400 * 365,
    keep_warm=1,
    allow_concurrent_runs=1,
)
def run_app_service():
    os.chdir("/workspace")
    print("🟢 Launching app.py as the main service process...")

    # MODIFIED: Use os.execle() to replace the current Python process 
    # with the app.py script. This is the simplest and most reliable way
    # to ensure all app.py output (including background services) 
    # flows directly into Modal logs.
    try:
        os.execle(sys.executable, sys.executable, "app.py", os.environ)
    except Exception as e:
        print(f"🔴 Failed to execute app.py: {e}")
        # Terminate the container if the main script fails to launch
        sys.exit(1)


# --- Deployment Logic ---
if __name__ == "__main__":
    print("🚀 Deploying Persistent Service...")
    
    # MODIFIED: Use app.serve() to deploy a long-running service 
    # instead of app.deploy() and run_app.spawn().
    app.serve() 
    
    print("✅ Deployment and remote launch complete.")
