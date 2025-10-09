# deploy.py
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
    .add_local_dir(".", remote_path="/workspace")
)

# MODIFIED: 使用新的函数名 run_app_service 替换旧的 run_app
@app.function(
    image=image,
    # 设置一个非常长的 timeout 和 keep_warm 来模拟持久运行
    timeout=86400 * 365,
    keep_warm=1, 
    allow_concurrent_runs=1,
)
def run_app_service():
    os.chdir("/workspace")
    print("🟢 Launching app.py as the main service process...")

    # 使用 os.execle() 替换当前 Python 进程
    # 这是最可靠的方式来确保 app.py 的所有输出都流向 Modal logs。
    try:
        # sys.executable 是 Python 解释器的路径
        os.execle(sys.executable, sys.executable, "app.py", os.environ)
    except Exception as e:
        print(f"🔴 Failed to execute app.py: {e}")
        # Terminate the container if the main script fails to launch
        sys.exit(1)


# --- Deployment Logic ---
if __name__ == "__main__":
    print("🚀 Deploying Persistent Service...")
    
    # 🚨 请使用 `modal deploy deploy.py` 或 `modal serve deploy.py` 命令。
    # app.serve() 是部署持久化服务的推荐方式。
    app.serve() 
    
    print("✅ Deployment and remote launch complete.")
