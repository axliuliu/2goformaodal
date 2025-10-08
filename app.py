import os
import re
import json
import time
import base64
import shutil
import requests
import platform
import subprocess
import threading # <-- 关键修复：确保 threading 模块被导入和使用
from threading import Thread 
from flask import Flask, Response, abort 

# 实例化 Flask 应用
app = Flask(__name__)

# --- 环境变量 ---
UPLOAD_URL = os.environ.get('UPLOAD_URL', '')      
PROJECT_URL = os.environ.get('PROJECT_URL', '')    
AUTO_ACCESS = os.environ.get('AUTO_ACCESS', 'false').lower() == 'false'
FILE_PATH = os.environ.get('FILE_PATH', './.cache') 
SUB_PATH = os.environ.get('SUB_PATH', 'sub')        
UUID = os.environ.get('UUID', '7ef14791-3877-4524-a3e7-a320ee2dc048')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'a.holoy.dpdns.org:36958')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')      
NEZHA_KEY = os.environ.get('NEZHA_KEY', 'NwxKJwM9UKRCX5TBPaBm0IrjNCSyflif')
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', 'modal.holoy.qzz.io')
ARGO_AUTH = os.environ.get('ARGO_AUTH', 'eyJhIjoiYjNiMmRhZjE1YjIzYmQ2ZmIzNzZlNGViYTRhYzczYTEiLCJ0IjoiNWYwMjQ1MjItNjE1My00NTc3LThkMjgtODU4NjViZTQ1MThhIiwicyI6IllqZGpZelkxWWpjdE56WmlaQzAwTVRGaUxUazFNR010T1dRMU1tWmpPV1U1TmpNMSJ9')
ARGO_PORT = int(os.environ.get('ARGO_PORT', '8000'))
CFIP = os.environ.get('CFIP', 'www.visa.com.tw')
CFPORT = int(os.environ.get('CFPORT', '443'))
NAME = os.environ.get('NAME', 'modal.com')
CHAT_ID = os.environ.get('CHAT_ID', '7627328147')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8337759907:AAGvmCiBeS2G_RXiNEUHYa4cdxn119nzV44')
SERVER_PORT = int(os.environ.get('SERVER_PORT') or os.environ.get('PORT') or 8000) 
# --- 环境变量结束 ---

# 全局文件路径
npm_path = os.path.join(FILE_PATH, 'npm')
php_path = os.path.join(FILE_PATH, 'php')
web_path = os.path.join(FILE_PATH, 'web')
bot_path = os.path.join(FILE_PATH, 'bot')
sub_path = os.path.join(FILE_PATH, 'sub.txt')
list_path = os.path.join(FILE_PATH, 'list.txt')
boot_log_path = os.path.join(FILE_PATH, 'boot.log')
config_path = os.path.join(FILE_PATH, 'config.json')

# --- 辅助函数 ---

def create_directory():
    if not os.path.exists(FILE_PATH):
        os.makedirs(FILE_PATH)
        print(f"Directory {FILE_PATH} created.")
    else:
        print(f"Directory {FILE_PATH} already exists.")

def exec_cmd(command):
    """使用 Popen 启动命令，非阻塞，适用于 Modal."""
    try:
        subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
        return True
    except Exception as e:
        print(f"Error executing command: {e}")
        return False

def run_blocking_cmd(command):
    """使用阻塞的 subprocess.run 运行命令，适用于 Cloudflare Tunnel."""
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Blocking command failed: {e}")
    except Exception as e:
        print(f"Error running blocking command: {e}")

def delete_nodes():
    try:
        if not UPLOAD_URL or not os.path.exists(sub_path):
            return
        with open(sub_path, 'r') as file:
            file_content = file.read()
        decoded = base64.b64decode(file_content).decode('utf-8')
        nodes = [line for line in decoded.split('\n') if any(protocol in line for protocol in ['vless://', 'vmess://', 'trojan://', 'hysteria2://', 'tuic://'])]
        if not nodes:
            return
        requests.post(f"{UPLOAD_URL}/api/delete-nodes",  
                      data=json.dumps({"nodes": nodes}),
                      headers={"Content-Type": "application/json"})
    except Exception as e:
        print(f"Error in delete_nodes: {e}")

def cleanup_old_files():
    paths_to_delete = ['web', 'bot', 'npm', 'php', 'boot.log', 'list.txt', 'tunnel.yml', 'tunnel.json', 'config.json', 'config.yaml']
    for file in paths_to_delete:
        file_path = os.path.join(FILE_PATH, file)
        try:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
            
def get_system_architecture():
    architecture = platform.machine().lower()
    if 'arm' in architecture or 'aarch64' in architecture:
        return 'arm'
    else:
        return 'amd'

def download_file(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    try:
        response = requests.get(file_url, stream=True)
        response.raise_for_status()
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Download {file_name} successfully")
        return True
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        print(f"Download {file_name} failed: {e}")
        return False

def get_files_for_architecture(architecture):
    if architecture == 'arm':
        base_files = [
            {"fileName": "web", "fileUrl": "https://arm64.ssss.nyc.mn/web"},
            {"fileName": "bot", "fileUrl": "https://arm64.ssss.nyc.mn/2go"}
        ]
    else:
        base_files = [
            {"fileName": "web", "fileUrl": "https://amd64.ssss.nyc.mn/web"},
            {"fileName": "bot", "fileUrl": "https://amd64.ssss.nyc.mn/2go"}
        ]
    if NEZHA_SERVER and NEZHA_KEY:
        if NEZHA_PORT:
            npm_url = "https://arm64.ssss.nyc.mn/agent" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/agent"
            base_files.insert(0, {"fileName": "npm", "fileUrl": npm_url})
        else:
            php_url = "https://arm64.ssss.nyc.mn/v1" if architecture == 'arm' else "https://amd64.ssss.nyc.mn/v1"
            base_files.insert(0, {"fileName": "php", "fileUrl": php_url})
    return base_files

def authorize_files(file_paths):
    for relative_file_path in file_paths:
        absolute_file_path = os.path.join(FILE_PATH, relative_file_path)
        if os.path.exists(absolute_file_path):
            try:
                os.chmod(absolute_file_path, 0o775)
                print(f"Empowerment success for {absolute_file_path}: 775")
            except Exception as e:
                print(f"Empowerment failed for {absolute_file_path}: {e}")

def argo_type():
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH variable is empty, use quick tunnels")
        return
    if "TunnelSecret" in ARGO_AUTH:
        try:
            auth_data = json.loads(ARGO_AUTH)
            tunnel_id = auth_data.get("TunnelID")
        except json.JSONDecodeError:
            print("ARGO_AUTH is not valid JSON, cannot set up fixed tunnel.")
            return
        with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as f:
            f.write(ARGO_AUTH)
        tunnel_yml = f"""
tunnel: {tunnel_id}
credentials-file: {os.path.join(FILE_PATH, 'tunnel.json')}
protocol: http2

ingress:
  - hostname: {ARGO_DOMAIN}
    service: http://localhost:{ARGO_PORT}
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"""
        with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as f:
            f.write(tunnel_yml)
        print("Fixed Argo tunnel configuration generated.")
    else:
        print("Use token connect to tunnel, please set the {ARGO_PORT} in cloudflare")

def upload_nodes():
    if UPLOAD_URL and PROJECT_URL:
        subscription_url = f"{PROJECT_URL}/{SUB_PATH}"
        json_data = {"subscription": [subscription_url]}
        try:
            requests.post(f"{UPLOAD_URL}/api/add-subscriptions", json=json_data, headers={"Content-Type": "application/json"})
            print('Subscription uploaded successfully')
        except Exception as e:
            print(f"Error uploading subscription: {e}")
            
    elif UPLOAD_URL:
        if not os.path.exists(list_path):
            return
        with open(list_path, 'r') as f:
            content = f.read()
        nodes = [line for line in content.split('\n') if any(protocol in line for protocol in ['vless://', 'vmess://', 'trojan://', 'hysteria2://', 'tuic://'])]
        if not nodes:
            return
        json_data = json.dumps({"nodes": nodes})
        try:
            requests.post(f"{UPLOAD_URL}/api/add-nodes", data=json_data, headers={"Content-Type": "application/json"})
            print('Nodes uploaded successfully')
        except Exception as e:
            print(f"Error uploading nodes: {e}")

def send_telegram():
    if not BOT_TOKEN or not CHAT_ID or not os.path.exists(sub_path):
        return
    try:
        with open(sub_path, 'r') as f:
            message = f.read()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        escaped_name = re.sub(r'([_*\[\]()~>#+=|{}.!\-])', r'\\\1', NAME)
        params = {
            "chat_id": CHAT_ID,
            "text": f"**{escaped_name}节点推送通知**\n{message}",
            "parse_mode": "MarkdownV2"
        }
        requests.post(url, params=params)
        print('Telegram message sent successfully')
    except Exception as e:
        print(f'Failed to send Telegram message: {e}')

def add_visit_task():
    if not AUTO_ACCESS or not PROJECT_URL:
        print("Skipping adding automatic access task")
        return
    try:
        requests.post(
            'https://keep.gvrander.eu.org/add-url',
            json={"url": PROJECT_URL},
            headers={"Content-Type": "application/json"}
        )
        print('automatic access task added successfully')
    except Exception as e:
        print(f'Failed to add URL: {e}')

def generate_links(argo_domain):
    meta_info = subprocess.run(['curl', '-s', 'https://speed.cloudflare.com/meta'], capture_output=True, text=True)
    meta_info_stdout = meta_info.stdout
    ISP = "UNKNOWN_LOCATION"
    if meta_info_stdout and meta_info.returncode == 0:
        try:
            meta_info_json = json.loads(meta_info_stdout)
            ISP = f"{meta_info_json.get('asn', '')}-{meta_info_json.get('colo', '')}".replace(' ', '_').strip()
        except Exception:
            pass
            
    time.sleep(2)
    VMESS = {"v": "2", "ps": f"{NAME}-{ISP}", "add": CFIP, "port": CFPORT, "id": UUID, "aid": "0", "scy": "none", "net": "ws", "type": "none", "host": argo_domain, "path": "/vmess-argo?ed=2560", "tls": "tls", "sni": argo_domain, "alpn": "", "fp": "chrome"}
    
    list_txt = f"""
vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&fp=chrome&type=ws&host={argo_domain}&path=%2Fvless-argo%3Fed%3D2560#{NAME}-{ISP}
 
vmess://{ base64.b64encode(json.dumps(VMESS).encode('utf-8')).decode('utf-8')}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&fp=chrome&type=ws&host={argo_domain}&path=%2Ftrojan-argo%3Fed%3D2560#{NAME}-{ISP}
    """
    
    with open(list_path, 'w', encoding='utf-8') as list_file:
        list_file.write(list_txt)

    sub_txt = base64.b64encode(list_txt.encode('utf-8')).decode('utf-8')
    with open(sub_path, 'w', encoding='utf-8') as sub_file:
        sub_file.write(sub_txt)
        
    print(f"\n--- Base64 Subscription Content ---\n{sub_txt}")
    print(f"{sub_path} saved successfully")
    
    send_telegram()
    upload_nodes()
    
    return sub_txt    

def extract_domains():
    argo_domain = None
    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        print(f'ARGO_DOMAIN: {argo_domain}')
        generate_links(argo_domain)
        return

    # Check for temporary tunnel domain in log
    for attempt in range(3):
        time.sleep(2 + attempt * 2)
        try:
            with open(boot_log_path, 'r') as f:
                file_content = f.read()
            match = re.search(r'https?://([^ ]*trycloudflare\.com)/?', file_content)
            if match:
                argo_domain = match.group(1)
                print(f'ArgoDomain: {argo_domain}')
                generate_links(argo_domain)
                return
            
            print(f'ArgoDomain not found in log (Attempt {attempt+1}), retrying...')
            if attempt < 2:
                run_blocking_cmd('pkill -f "[b]ot"')
                if os.path.exists(boot_log_path):
                     os.remove(boot_log_path)
                
                args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {boot_log_path} --loglevel info --url http://localhost:{ARGO_PORT}"
                exec_cmd(f"{bot_path} {args}")
                
        except Exception as e:
            print(f'Error reading boot.log: {e}')
            
    print("Failed to obtain ArgoDomain after multiple attempts.")


# --- Service Startup (As Threads) ---

def run_nezha_thread():
    if not (NEZHA_SERVER and NEZHA_KEY): return

    if NEZHA_PORT:
        # v0 mode
        tls_ports = ['443', '8443', '2096', '2087', '2083', '2053']
        nezha_tls = '--tls' if NEZHA_PORT in tls_ports else ''
        command = f"{npm_path} -s {NEZHA_SERVER}:{NEZHA_PORT} -p {NEZHA_KEY} {nezha_tls}"
        print('Starting npm (Nezha V0)...')
    else:
        # v1 mode
        config_yaml_path = os.path.join(FILE_PATH, 'config.yaml')
        config_yaml = f"""
client_secret: {NEZHA_KEY}
server: {NEZHA_SERVER}
tls: {"true" if "443" in NEZHA_SERVER.split(":")[-1] else "false"}
uuid: {UUID}"""
        with open(config_yaml_path, 'w') as f:
            f.write(config_yaml)
        command = f"{php_path} -c \"{config_yaml_path}\""
        print('Starting php (Nezha V1)...')

    # NOTE: These services are launched non-blocking but WILL BE KILLED by Modal.
    exec_cmd(command)

def run_web_thread():
    command = f"{web_path} -c {config_path}"
    print('Starting web (Xray/SingBox)...')
    # NOTE: This service is launched non-blocking but WILL BE KILLED by Modal.
    exec_cmd(command)

def run_argo_thread():
    # This thread runs the ARGO Tunnel (bot) as the main blocking process, keeping the container alive.
    if not os.path.exists(bot_path):
        print("Cloudflare Tunnel binary 'bot' not found. Cannot start tunnel.")
        return
        
    if ARGO_AUTH and ARGO_DOMAIN and ("TunnelSecret" in ARGO_AUTH or re.match(r'^[A-Z0-9a-z=]{120,250}$', ARGO_AUTH)):
        if "TunnelSecret" in ARGO_AUTH:
            args = f"tunnel --edge-ip-version auto --config {os.path.join(FILE_PATH, 'tunnel.yml')} run"
        else:
            args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 run --token {ARGO_AUTH}"
    else:
        args = f"tunnel --edge-ip-version auto --no-autoupdate --protocol http2 --logfile {boot_log_path} --loglevel info --url http://localhost:{ARGO_PORT}"
        
    command = f"{bot_path} {args}"
    
    print(f"Starting Cloudflare Tunnel (Main Process): {command}")
    
    # Run blocking command to keep the Modal container alive indefinitely
    run_blocking_cmd(command)


# --- Flask Web Interface ---
@app.route('/')
def index_route():
    return f"Modal app is running. Access subscription at /{SUB_PATH}"

@app.route(f'/{SUB_PATH}')
def sub_route():
    if not os.path.exists(sub_path):
        return "Subscription file not found.", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    
    try:
        with open(sub_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return f"Error reading subscription: {e}", 500, {'Content-Type': 'text/plain; charset=utf-8'}


# --- Main Orchestration ---

def clean_files():
    def _cleanup():
        time.sleep(90)
        cleanup_old_files()
        
        print('\033c', end='')
        print('App is running')
        print('Thank you for using this script, enjoy!')
        
    threading.Thread(target=_cleanup, daemon=True).start()

def setup_and_run():
    """执行所有设置，启动后台服务，并运行 ARGO 隧道作为主进程。"""
    
    # 设置步骤 (同步)
    delete_nodes()
    cleanup_old_files()
    create_directory()
    argo_type()
    
    # 下载文件 (同步)
    architecture = get_system_architecture()
    files_to_download = get_files_for_architecture(architecture)
    
    if any(not download_file(f["fileName"], f["fileUrl"]) for f in files_to_download):
        print("FATAL: Critical download error. Exiting setup.")
        return

    files_to_authorize = [f["fileName"] for f in files_to_download]
    authorize_files(files_to_authorize)

    # 启动非关键服务作为单独线程 (会被 Modal 杀死)
    Thread(target=run_nezha_thread, daemon=True).start()
    Thread(target=run_web_thread, daemon=True).start()
    
    # 等待 Xray/SingBox 启动和配置文件可用
    time.sleep(5) 
    
    # 提取域名并生成 sub.txt
    extract_domains()
    
    # 添加自保活任务
    add_visit_task()
    
    # 启动清理定时器
    clean_files()
    
    # 启动 Flask 服务器作为单独线程 (必须监听 ARGO_PORT)
    Thread(target=lambda: app.run(host='0.0.0.0', port=ARGO_PORT, debug=False, use_reloader=False), daemon=True).start()
    
    # 给 Flask 一点时间启动
    time.sleep(1)

    # 启动 Cloudflare Tunnel 作为主阻塞进程
    run_argo_thread()


# ----------------------------------------------------------------------
# 最终执行块 (Modal 兼容)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    setup_and_run()
