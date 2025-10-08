import os
import re
import shutil
import subprocess
import requests
from flask import Flask, jsonify
import json
import time
import base64

app = Flask(__name__)

# --- Environment Variables ---
FILE_PATH = os.environ.get('FILE_PATH', './tmp')
# 自动访问功能在 Modal 中通常不需要，因为 Modal 是按需启动的，但保留变量
PROJECT_URL = os.environ.get('URL', '') 
INTERVAL_SECONDS = int(os.environ.get("TIME", 120))
UUID = os.environ.get('UUID', '7ef14791-3877-4524-a3e7-a320ee2dc048')
NEZHA_SERVER = os.environ.get('NEZHA_SERVER', 'a.holoy.dpdns.org:36958')
NEZHA_PORT = os.environ.get('NEZHA_PORT', '')
NEZHA_KEY = os.environ.get('NEZHA_KEY', 'NwxKJwM9UKRCX5TBPaBm0IrjNCSyflif')
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', 'modal.holoy.qzz.io')
ARGO_AUTH = os.environ.get('ARGO_AUTH', 'eyJhIjoiYjNiMmRhZjE1YjIzYmQ2ZmIzNzZlNGViYTRhYzczYTEiLCJ0IjoiNWYwMjQ1MjItNjE1My00NTc3LThkMjgtODU4NjViZTQ1MThhIiwicyI6IllqZGpZelkxWWpjdE56WmlaQzAwTVRGaUxUazFNR010T1dRMU1tWmpPV1U1TmpNMSJ9')
# ARGO_PORT 更改为 Modal 推荐的 8000
ARGO_PORT = int(os.environ.get('ARGO_PORT', 8001)) 
CFIP = os.environ.get('CFIP', 'www.visa.com.tw')
CFPORT = int(os.environ.get('CFPORT', 443))
NAME = os.environ.get('NAME', 'modal')
# --- END Environment Variables ---

# Create directory if it doesn't exist
if not os.path.exists(FILE_PATH):
    os.makedirs(FILE_PATH)
    print(f"{FILE_PATH} has been created")
else:
    print(f"{FILE_PATH} already exists")

# Clean old files (keep logic)
paths_to_delete = ['boot.log', 'list.txt','sub.txt', 'npm', 'web', 'bot', 'tunnel.yml', 'tunnel.json', 'config.json']
for file in paths_to_delete:
    file_path = os.path.join(FILE_PATH, file)
    try:
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.unlink(file_path)
        print(f"{file_path} has been deleted")
    except Exception as e:
        # print(f"Skip Delete {file_path}")
        pass # Silence known file deletion errors

# Generate xr-ay config file (keep logic)
def generate_config():
    # ... (config generation logic remains the same)
    config ={"log":{"access":"/dev/null","error":"/dev/null","loglevel":"none",},"inbounds":[{"port":ARGO_PORT ,"protocol":"vless","settings":{"clients":[{"id":UUID ,"flow":"xtls-rprx-vision",},],"decryption":"none","fallbacks":[{"dest":3001 },{"path":"/vless-argo","dest":3002 },{"path":"/vmess-argo","dest":3003 },{"path":"/trojan-argo","dest":3004 },],},"streamSettings":{"network":"tcp",},},{"port":3001 ,"listen":"127.0.0.1","protocol":"vless","settings":{"clients":[{"id":UUID },],"decryption":"none"},"streamSettings":{"network":"ws","security":"none"}},{"port":3002 ,"listen":"127.0.0.1","protocol":"vless","settings":{"clients":[{"id":UUID ,"level":0 }],"decryption":"none"},"streamSettings":{"network":"ws","security":"none","wsSettings":{"path":"/vless-argo"}},"sniffing":{"enabled":True ,"destOverride":["http","tls","quic"],"metadataOnly":False }},{"port":3003 ,"listen":"127.0.0.1","protocol":"vmess","settings":{"clients":[{"id":UUID ,"alterId":0 }]},"streamSettings":{"network":"ws","wsSettings":{"path":"/vmess-argo"}},"sniffing":{"enabled":True ,"destOverride":["http","tls","quic"],"metadataOnly":False }},{"port":3004 ,"listen":"127.0.0.1","protocol":"trojan","settings":{"clients":[{"password":UUID },]},"streamSettings":{"network":"ws","security":"none","wsSettings":{"path":"/trojan-argo"}},"sniffing":{"enabled":True ,"destOverride":["http","tls","quic"],"metadataOnly":False }},],"dns":{"servers":["https+local://8.8.8.8/dns-query"]},"outbounds":[{"protocol":"freedom","tag": "direct" },{"protocol":"blackhole","tag":"block"}]}
    with open(os.path.join(FILE_PATH, 'config.json'), 'w', encoding='utf-8') as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)

generate_config()

# Determine system architecture (keep logic)
def get_system_architecture():
    arch = os.uname().machine
    if 'arm' in arch or 'aarch64' in arch or 'arm64' in arch:
        return 'arm'
    else:
        return 'amd'

# Download file (keep logic)
def download_file(file_name, file_url):
    file_path = os.path.join(FILE_PATH, file_name)
    with requests.get(file_url, stream=True) as response, open(file_path, 'wb') as file:
        response.raise_for_status() # Check for bad status code
        shutil.copyfileobj(response.raw, file)

# Download and run files (MODIFIED: Removed nohup &)
def download_files_and_run():
    architecture = get_system_architecture()
    files_to_download = get_files_for_architecture(architecture)

    if not files_to_download:
        print("Can't find a file for the current architecture")
        return

    for file_info in files_to_download:
        try:
            download_file(file_info['file_name'], file_info['file_url'])
            print(f"Downloaded {file_info['file_name']} successfully")
        except Exception as e:
            print(f"Download {file_info['file_name']} failed: {e}")

    # Authorize and run (keep logic)
    files_to_authorize = ['npm', 'web', 'bot']
    authorize_files(files_to_authorize)

    # ----------------------------------------------------
    # MODIFICATION: STARTING SERVICES AS BACKGROUND THREADS
    # ----------------------------------------------------
    
    # Run ne-zha (npm) in a non-blocking way, knowing it will be killed by Modal
    if NEZHA_SERVER and NEZHA_PORT and NEZHA_KEY:
        threading.Thread(target=run_nezha, daemon=True).start()
    else:
        print('NEZHA variable is empty, skip running npm')

    # Run xr-ay (web) in a non-blocking way, knowing it will be killed by Modal
    threading.Thread(target=run_xray, daemon=True).start()
    
    # Cloud-fared (bot) will be run as the MAIN PROCESS in start_server

def run_nezha():
    NEZHA_TLS = ''
    valid_ports = ['443', '8443', '2096', '2087', '2083', '2053']
    if NEZHA_PORT in valid_ports:
        NEZHA_TLS = '--tls'
    
    # NOTE: nezha will NOT run persistently due to Modal limitations.
    command = [f"{FILE_PATH}/npm", "-s", f"{NEZHA_SERVER}:{NEZHA_PORT}", "-p", NEZHA_KEY]
    if NEZHA_TLS:
        command.append(NEZHA_TLS)
        
    try:
        print('Attempting to start npm (Nezha)...')
        # Use subprocess.Popen to start it and immediately continue (non-blocking)
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('npm process started (will be killed by Modal shortly)')
    except Exception as e:
        print(f'npm running error: {e}')

def run_xray():
    # NOTE: xray will NOT run persistently due to Modal limitations.
    command1 = [f"{FILE_PATH}/web", "-c", f"{FILE_PATH}/config.json"]
    try:
        print('Attempting to start web (Xray)...')
        # Use subprocess.Popen to start it and immediately continue (non-blocking)
        subprocess.Popen(command1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('web process started (will be killed by Modal shortly)')
    except Exception as e:
        print(f'web running error: {e}')

# Get command line arguments for cloud-fared (keep logic)
def get_cloud_flare_args():
    # ... (logic remains the same)
    processed_auth = ARGO_AUTH
    try:
        auth_data = json.loads(ARGO_AUTH)
        if 'TunnelSecret' in auth_data and 'AccountTag' in auth_data and 'TunnelID' in auth_data:
            processed_auth = 'TunnelSecret'
    except json.JSONDecodeError:
        pass

    # Determines the condition and generates the corresponding args
    if not processed_auth and not ARGO_DOMAIN:
        # Use simple list for subprocess.run
        args = [f'{FILE_PATH}/bot', 'tunnel', '--edge-ip-version', 'auto', '--no-autoupdate', '--protocol', 'http2', '--logfile', f'{FILE_PATH}/boot.log', '--loglevel', 'info', '--url', f'http://localhost:{ARGO_PORT}']
    elif processed_auth == 'TunnelSecret':
        args = [f'{FILE_PATH}/bot', 'tunnel', '--edge-ip-version', 'auto', '--config', f'{FILE_PATH}/tunnel.yml', 'run']
    elif processed_auth and ARGO_DOMAIN and 120 <= len(processed_auth) <= 250:
        args = [f'{FILE_PATH}/bot', 'tunnel', '--edge-ip-version', 'auto', '--no-autoupdate', '--protocol', 'http2', 'run', '--token', processed_auth]
    else:
        args = [f'{FILE_PATH}/bot', 'tunnel', '--edge-ip-version', 'auto', '--no-autoupdate', '--protocol', 'http2', '--logfile', f'{FILE_PATH}/boot.log', '--loglevel', 'info', '--url', f'http://localhost:{ARGO_PORT}']

    return args

# Return file information based on system architecture (keep logic)
def get_files_for_architecture(architecture):
    # ... (logic remains the same)
    if architecture == 'arm':
        return [
            {'file_name': 'npm', 'file_url': 'https://arm64.ssss.nyc.mn/agent'},
            {'file_name': 'web', 'file_url': 'https://arm64.ssss.nyc.mn/web'},
            {'file_name': 'bot', 'file_url': 'https://arm64.ssss.nyc.mn/2go'},
        ]
    elif architecture == 'amd':
        return [
            {'file_name': 'npm', 'file_url': 'https://amd64.ssss.nyc.mn/agent'},
            {'file_name': 'web', 'file_url': 'https://amd64.ssss.nyc.mn/web'},
            {'file_name': 'bot', 'file_url': 'https://amd64.ssss.nyc.mn/2go'},
        ]
    return []

# Authorize files (keep logic)
def authorize_files(file_paths):
    new_permissions = 0o775

    for relative_file_path in file_paths:
        absolute_file_path = os.path.join(FILE_PATH, relative_file_path)
        try:
            os.chmod(absolute_file_path, new_permissions)
            print(f"Empowerment success for {absolute_file_path}: {oct(new_permissions)}")
        except Exception as e:
            print(f"Empowerment failed for {absolute_file_path}: {e}")


# Get fixed tunnel JSON and yml (keep logic)
def argo_config():
    # ... (logic remains the same)
    if not ARGO_AUTH or not ARGO_DOMAIN:
        print("ARGO_DOMAIN or ARGO_AUTH is empty, use quick Tunnels")
        return

    if 'TunnelSecret' in ARGO_AUTH:
        # NOTE: Original code was trying to parse JSON into a string and split it, which is prone to error.
        # Assuming ARGO_AUTH is a JSON string containing the necessary fields.
        try:
            auth_data = json.loads(ARGO_AUTH)
            tunnel_id = auth_data.get("TunnelID")
            if not tunnel_id:
                print("TunnelID not found in ARGO_AUTH JSON.")
                return

            with open(os.path.join(FILE_PATH, 'tunnel.json'), 'w') as file:
                file.write(ARGO_AUTH)
            tunnel_yaml = f"""
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
            with open(os.path.join(FILE_PATH, 'tunnel.yml'), 'w') as file:
                file.write(tunnel_yaml)
            print("Fixed tunnel config (tunnel.yml and tunnel.json) generated.")

        except json.JSONDecodeError:
            print("ARGO_AUTH is not valid JSON, assuming it's a token.")
            
    else:
        print("Use token connect to tunnel")

argo_config()

# Get temporary tunnel domain (keep logic, but simplified the retry part for a single execution context)
def extract_domains():
    argo_domain = ''

    if ARGO_AUTH and ARGO_DOMAIN:
        argo_domain = ARGO_DOMAIN
        print('ARGO_DOMAIN:', argo_domain)
        generate_links(argo_domain)
    else:
        # The complex retry/pkill logic is generally problematic in Modal/FaaS.
        # We assume the main Cloudflare Tunnel process (run in the main thread) 
        # is stable and its log can be read.
        time.sleep(5) # Give the bot time to start and write log
        try:
            with open(os.path.join(FILE_PATH, 'boot.log'), 'r', encoding='utf-8') as file:
                content = file.read()
                match = re.search(r'https://([^ ]+\.trycloudflare\.com)', content)
                if match:
                    argo_domain = match.group(1)
                    print('ArgoDomain:', argo_domain)
                    generate_links(argo_domain)
                else:
                    print('ArgoDomain not found in log. Check Cloudflare Tunnel logs for errors.')
        except Exception as e:
            print(f"Error reading boot.log: {e}. Cannot generate links.")


# Generate list and sub info (keep logic)
def generate_links(argo_domain):
    # ... (logic remains the same)
    
    # NOTE: subprocess.run(['curl', ...]) is allowed in Modal but needs to be synchronous here.
    meta_info = subprocess.run(['curl', '-s', 'https://speed.cloudflare.com/meta'], capture_output=True, text=True)
    meta_info_stdout = meta_info.stdout
    
    # Check if curl failed (empty output or error)
    if not meta_info_stdout or meta_info.returncode != 0:
        print("Warning: Failed to fetch Cloudflare meta info. Using default ISP/location.")
        ISP = "UNKNOWN_LOCATION"
    else:
        try:
            # Original parsing logic (assuming meta_info.stdout is the JSON string)
            meta_info_json = json.loads(meta_info_stdout)
            ISP = f"{meta_info_json.get('asn', '')}-{meta_info_json.get('colo', '')}".replace(' ', '_').strip()
        except Exception as e:
            print(f"Warning: Failed to parse Cloudflare meta info. {e}. Using default ISP/location.")
            ISP = "UNKNOWN_LOCATION"
            
    time.sleep(2)
    VMESS = {"v": "2", "ps": f"{NAME}-{ISP}", "add": CFIP, "port": CFPORT, "id": UUID, "aid": "0", "scy": "none", "net": "ws", "type": "none", "host": argo_domain, "path": "/vmess-argo?ed=2048", "tls": "tls", "sni": argo_domain, "alpn": ""}
 
    list_txt = f"""
vless://{UUID}@{CFIP}:{CFPORT}?encryption=none&security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2Fvless-argo%3Fed%3D2048#{NAME}-{ISP}
 
vmess://{ base64.b64encode(json.dumps(VMESS).encode('utf-8')).decode('utf-8')}

trojan://{UUID}@{CFIP}:{CFPORT}?security=tls&sni={argo_domain}&type=ws&host={argo_domain}&path=%2Ftrojan-argo%3Fed%3D2048#{NAME}-{ISP}
    """
     
    with open(os.path.join(FILE_PATH, 'list.txt'), 'w', encoding='utf-8') as list_file:
        list_file.write(list_txt)

    sub_txt = base64.b64encode(list_txt.encode('utf-8')).decode('utf-8')
    with open(os.path.join(FILE_PATH, 'sub.txt'), 'w', encoding='utf-8') as sub_file:
        sub_file.write(sub_txt)
        
    try:
        with open(os.path.join(FILE_PATH, 'sub.txt'), 'rb') as file:
            sub_content = file.read()
        print(f"\n--- Base64 Subscription Content ---\n{sub_content.decode('utf-8')}")
    except FileNotFoundError:
        print(f"sub.txt not found")
        
    print(f'\n{FILE_PATH}/sub.txt saved successfully')
     
    # The file cleanup logic should be done just before the script exits, 
    # but since the script will be running indefinitely (via Flask/bot), 
    # we'll skip the cleanup here to keep the sub.txt available.
    print('Skipping file cleanup to keep sub.txt for Flask route.')

    print('\033c', end='')
    print('App is running')
    print('Thank you for using this script, enjoy!')

# --- Flask Routes ---
@app.route('/')
def index():
    return f"Modal app is running. Access subscription at /{os.path.basename(FILE_PATH)}/sub.txt"

@app.route(f'/{os.path.basename(FILE_PATH)}/sub.txt')
def get_sub_txt():
    subFile = os.path.join(FILE_PATH, 'sub.txt')
    try:
        with open(subFile, 'r', encoding='utf-8') as f:
            sub_content = f.read()
        return sub_content, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except FileNotFoundError:
        return f"sub.txt file not found at: {subFile}", 404, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        return f"Error reading sub.txt: {e}", 500, {'Content-Type': 'text/plain; charset=utf-8'}

# --- Main Logic ---
def run_cloudflared_tunnel():
    """Runs the Cloudflare Tunnel as the main blocking process."""
    if not os.path.exists(os.path.join(FILE_PATH, 'bot')):
        print("Cloudflare Tunnel binary 'bot' not found. Cannot start tunnel.")
        return

    # Get command line arguments for cloud-fared
    args = get_cloud_flare_args()
    
    print(f"Starting Cloudflare Tunnel with command: {' '.join(args)}")
    
    try:
        # Run the tunnel as the main process. This call is BLOCKING.
        # It keeps the Modal container alive.
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError as e:
        print(f'Cloudflare Tunnel execution failed: {e}')
    except FileNotFoundError:
        print(f"Tunnel binary not found at: {args[0]}")
    except Exception as e:
        print(f'Error starting Cloudflare Tunnel: {e}')

def start_server():
    """Initializes and runs the services."""
    download_files_and_run()
    
    # ----------------------------------------------------
    # MODIFICATION: SEPARATE THREADS FOR FLASK AND TUNNEL
    # ----------------------------------------------------
    
    # Thread 1: Flask Web Server (needs to listen on ARGO_PORT)
    # The Flask server serves the sub.txt file for the tunnel to connect to.
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=ARGO_PORT, debug=False), daemon=True).start()
    
    # Thread 2: Auto-visit Project URL (as per original code intent)
    threading.Thread(target=auto_visit_project_page, daemon=True).start()

    # Wait for Flask to start (briefly)
    time.sleep(3) 

    # Generate links (requires tunnel to run briefly to get domain if temporary)
    # We call extract_domains/generate_links AFTER starting Flask and BEFORE running the tunnel blocking call.
    # The tunnel will be run as the blocking function to keep the container alive.
    
    # Run Cloudflare Tunnel (This is the main blocking function)
    run_cloudflared_tunnel()

# auto visit project page (keep logic, wrapped in a function for threading)
def auto_visit_project_page():
    has_logged_empty_message = False
    while True:
        try:
            if not PROJECT_URL or not INTERVAL_SECONDS:
                if not has_logged_empty_message:
                    print("URL or TIME variable is empty, Skipping visit web")
                    has_logged_empty_message = True
                time.sleep(INTERVAL_SECONDS if INTERVAL_SECONDS > 0 else 60)
                continue

            response = requests.get(PROJECT_URL)
            response.raise_for_status() 

            print(f"Page visited successfully ({PROJECT_URL})")
            time.sleep(INTERVAL_SECONDS)
        except requests.exceptions.RequestException as error:
            print(f"Error visiting project page: {error}")
            time.sleep(INTERVAL_SECONDS if INTERVAL_SECONDS > 0 else 60)

# ----------------------------------------------------------------------
# FINAL EXECUTION BLOCK: Modified to run the Modal-compatible start_server
# ----------------------------------------------------------------------

if __name__ == "__main__":
    # In the Modal environment, the main script should run the persistent process.
    # We use start_server to manage the setup and then block on run_cloudflared_tunnel.
    start_server()
