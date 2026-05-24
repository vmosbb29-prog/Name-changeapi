from flask import Flask, request, jsonify
import requests
import time
import base64
import json
import urllib3
from urllib.parse import parse_qs, urlparse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import data_pb2
    import my_pb2
    import output_pb2
except ImportError as e:
    import sys
    sys.exit(1)

app = Flask(__name__)
app.json.sort_keys = False

SECRET_KEY = b'Yg&tc%DEuh6%Zc^8'
SECRET_IV = b'6oyZDr22E3ychjM%'

TARGET_URL = "https://loginbp.ggpolarbear.com/MajorModifyNickname"
MAJOR_LOGIN_URL = "https://loginbp.ggblueshark.com/MajorLogin"

GAME_VERSION = "OB53"
UNITY_VERSION = "2018.4.11f1"
USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 11; SM-A305F Build/RP1A.200720.012)"
DEVELOPERS = "@STAR_GMR"

def generate_error_payload(reason, http_status, extra_data=None):
    payload = {
        "metadata": {
            "author": DEVELOPERS,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        },
        "response_status": "ERROR",
        "error_message": reason
    }
    if extra_data:
        payload["diagnostic_details"] = extra_data
    return jsonify(payload), http_status

def encrypt_message(plaintext):
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, SECRET_IV)
    return cipher.encrypt(pad(plaintext, AES.block_size))

def decode_ff_name(b64_str):
    try:
        key = b"1e5898ccb8dfdd921f9bdea848768b64a201"
        b64_str = b64_str.strip()
        b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
        
        encrypted_bytes = base64.b64decode(b64_str)
        decrypted_bytes = bytearray()
        
        for i, byte in enumerate(encrypted_bytes):
            key_byte = key[i % len(key)]
            decrypted_bytes.append(byte ^ key_byte)
            
        return decrypted_bytes.decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Error decoding: {str(e)}"

def extract_jwt_info(jwt_token):
    try:
        payload_b64 = jwt_token.split('.')[1]
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        decoded_token = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
        
        account_id = decoded_token.get("account_id")
        enc_nickname = decoded_token.get("nickname")
        old_name = decode_ff_name(enc_nickname) if enc_nickname else "Unknown"
        region = decoded_token.get("lock_region", "Unknown")
        release_version = decoded_token.get("release_version", "Unknown")
        
        return account_id, old_name, region, release_version
    except Exception:
        return None, "Unknown", "Unknown", "Unknown"

def fetch_open_id(access_token):
    try:
        uid_url = "https://prod-api.reward.ff.garena.com/redemption/api/auth/inspect_token/"
        uid_headers = {
            "authority": "prod-api.reward.ff.garena.com",
            "method": "GET",
            "path": "/redemption/api/auth/inspect_token/",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "access-token": access_token,
            "cookie": "_gid=GA1.2.444482899.1724033242; _ga_XB5PSHEQB4=GS1.1.1724040177.1.1.1724040732.0.0.0; token_session=cb73a97aaef2f1c7fd138757dc28a08f92904b1062e66c; _ga_KE3SY7MRSD=GS1.1.1724041788.0.0.1724041788.0; _ga_RF9R6YT614=GS1.1.1724041788.0.0.1724041788.0; _ga=GA1.1.1843180339.1724033241; apple_state_key=817771465df611ef8ab00ac8aa985783; _ga_G8QGMJPWWV=GS1.1.1724049483.1.1.1724049880.0.0; datadome=HBTqAUPVsbBJaOLirZCUkN3rXjf4gRnrZcNlw2WXTg7bn083SPey8X~ffVwr7qhtg8154634Ee9qq4bCkizBuiMZ3Qtqyf3Isxmsz6GTH_b6LMCKWF4Uea_HSPk;",
            "origin": "https://reward.ff.garena.com",
            "referer": "https://reward.ff.garena.com/",
            "sec-ch-ua": '"Not.A/Brand";v="99", "Chromium";v="124"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        uid_res = requests.get(uid_url, headers=uid_headers, verify=False, timeout=10)
        uid_data = uid_res.json()
        uid = uid_data.get("uid")

        if not uid:
            return None

        openid_url = "https://topup.pk/api/auth/player_id_login"
        openid_headers = { 
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-MM,en-US;q=0.9,en;q=0.8",
            "Content-Type": "application/json",
            "Origin": "https://topup.pk",
            "Referer": "https://topup.pk/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Android WebView";v="138"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Linux; Android 15; RMX5070 Build/UKQ1.231108.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.7204.157 Mobile Safari/537.36",
            "X-Requested-With": "mark.via.gp",
            "Cookie": "source=mb; region=PK; mspid2=13c49fb51ece78886ebf7108a4907756; _fbp=fb.1.1753985808817.794945392376454660; language=en; datadome=WQaG3HalUB3PsGoSXY3TdcrSQextsSFwkOp1cqZtJ7Ax4YkiERHUgkgHlEAIccQO~w8dzTGM70D9SzaH7vymmEqOrVeX5pIsPVE22Uf3TDu6W3WG7j36ulnTg2DltRO7; session_key=hq02g63z3zjcumm76mafcooitj7nc79y",
        }
        payload = {"app_id": 100067, "login_id": str(uid)}
        openid_res = requests.post(openid_url, headers=openid_headers, json=payload, verify=False, timeout=10)
        open_id = openid_res.json().get("open_id")

        return open_id
    except Exception:
        return None

def perform_majorlogin(access_token, open_id):
    platforms = [8, 3, 4, 6]  

    for platform_type in platforms:
        game_data = my_pb2.GameData()
        game_data.timestamp = "2024-12-05 18:15:32"
        game_data.game_name = "free fire"
        game_data.game_version = 1
        game_data.version_code = "1.108.3"
        game_data.os_info = "Android OS 9 / API-28 (PI/rel.cjw.20220518.114133)"
        game_data.device_type = "Handheld"
        game_data.network_provider = "Verizon Wireless"
        game_data.connection_type = "WIFI"
        game_data.screen_width = 1280
        game_data.screen_height = 960
        game_data.dpi = "240"
        game_data.cpu_info = "ARMv7 VFPv3 NEON VMH | 2400 | 4"
        game_data.total_ram = 5951
        game_data.gpu_name = "Adreno (TM) 640"
        game_data.gpu_version = "OpenGL ES 3.0"
        game_data.user_id = "Google|74b585a9-0268-4ad3-8f36-ef41d2e53610"
        game_data.ip_address = "172.190.111.97"
        game_data.language = "en"
        game_data.open_id = open_id
        game_data.access_token = access_token
        game_data.platform_type = platform_type
        game_data.field_99 = str(platform_type)
        game_data.field_100 = str(platform_type)

        encrypted_data = encrypt_message(game_data.SerializeToString())

        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": UNITY_VERSION,
            "X-GA": "v1 1",
            "ReleaseVersion": GAME_VERSION
        }

        try:
            response = requests.post(MAJOR_LOGIN_URL, data=encrypted_data, headers=headers, verify=False, timeout=5)

            if response.status_code == 200:
                try:
                    example_msg = output_pb2.Garena_420()
                    example_msg.ParseFromString(response.content)
                    token_value = getattr(example_msg, "token", None)
                    if token_value:
                        return token_value 
                except Exception:
                    continue 
        except requests.RequestException:
            continue  
            
    return None

def execute_nickname_change(jwt_token, target_name, auth_type, token_status):
    account_id, old_name, region, release_version = extract_jwt_info(jwt_token)

    msg = data_pb2.Message()
    msg.data = target_name.encode("utf-8")
    msg.timestamp = int(time.time() * 1000)
    
    encrypted_data = encrypt_message(msg.SerializeToString())

    request_headers = {
        "Expect": "100-continue",
        "Authorization": f"Bearer {jwt_token}",
        "X-Unity-Version": UNITY_VERSION,
        "X-GA": "v1 1",
        "ReleaseVersion": GAME_VERSION,
        "Content-Type": "application/octet-stream",
        "User-Agent": USER_AGENT,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }

    try:
        remote_response = requests.post(
            TARGET_URL, 
            data=encrypted_data, 
            headers=request_headers,
            verify=False
        )
        
        success_flag = remote_response.status_code == 200

        try:
            raw_text = remote_response.content.decode('utf-8', errors='ignore')
            plaintext = ''.join(char for char in raw_text if ord(char) >= 32)
        except:
            plaintext = remote_response.text

        return jsonify({
            "metadata": {
                "author": DEVELOPERS,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "response_status": "SUCCESS" if success_flag else "FAILED",
            "operation_message": "Nickname successfully changed!" if success_flag else "Failed to alter nickname. Verify server status.",
            "http_status_code": remote_response.status_code,
            "account_details": {
                "authentication_method": auth_type,
                "account_id": account_id,
                "old_name": old_name,
                "new_name": target_name,
                "region": region,
                "release_version": release_version,
                "token_lifecycle_state": token_status
            },
            "server_feedback": {
                "headers": dict(remote_response.headers),
                "raw_hexadecimal": remote_response.content.hex(),
                "plaintext_response": plaintext
            }
        }), remote_response.status_code

    except Exception as network_error:
        return generate_error_payload(
            "Internal Server Error while communicating with game servers.", 
            500, 
            str(network_error)
        )

@app.route("/", methods=["GET"])
def api_documentation():
    return jsonify({
        "system_information": {
            "application": "Free Fire Nickname Modifier API",
            "developer": DEVELOPERS,
            "game_version_target": GAME_VERSION,
            "description": "JSON API for modifying game nicknames via Guest UID or OAuth Tokens."
        },
        "usage_guide": {
            "By using UID and Password": "/guest?uid={uid}&password={password}&name={new_name}",
            "By using Access Token": "/token?access_token={access_token}&name={new_name}",
            "By using Direct JWT Token": "/token?jwt={jwt_token}&name={new_name}"
        }
    })

@app.route("/guest", methods=["GET"])
def process_guest_login():
    game_uid = request.args.get("uid")
    game_pwd = request.args.get("password")
    desired_name = request.args.get("name")

    if not all([game_uid, game_pwd, desired_name]):
        return generate_error_payload("Missing required parameters: uid, password, name", 400)

    try:
        oauth_url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        payload = {
            'uid': game_uid, 'password': game_pwd, 'response_type': "token",
            'client_type': "2", 'client_secret': "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            'client_id': "100067"
        }
        headers = {'User-Agent': "GarenaMSDK/4.0.19P9(SM-M526B ;Android 13;pt;BR;)"}

        res = requests.post(oauth_url, data=payload, headers=headers, timeout=10)
        auth_data = res.json()

        if 'access_token' not in auth_data or 'open_id' not in auth_data:
            return generate_error_payload("Authentication failed. Invalid Guest credentials.", 401, auth_data)

        jwt_token = perform_majorlogin(auth_data['access_token'], auth_data['open_id'])
        if not jwt_token:
            return generate_error_payload("Failed to generate JWT. MajorLogin rejected payload.", 401)

        return execute_nickname_change(
            jwt_token=jwt_token, 
            target_name=desired_name, 
            auth_type="UID_PASSWORD_GUEST", 
            token_status="success"
        )

    except Exception as api_error:
        return generate_error_payload("External API Error during Auth generation.", 500, str(api_error))

@app.route("/token", methods=["GET"])
def process_token_login():
    direct_jwt = request.args.get("jwt")
    access_token = request.args.get("access_token")
    desired_name = request.args.get("name")

    if not desired_name or not (direct_jwt or access_token):
        return generate_error_payload("Missing required parameters: name AND (jwt OR access_token)", 400)

    active_jwt = direct_jwt
    current_status = "direct_jwt_input"

    if access_token and not direct_jwt:
        try:
            open_id = fetch_open_id(access_token)
            if not open_id:
                return generate_error_payload("Failed to retrieve OpenID from the provided Access Token.", 401)

            active_jwt = perform_majorlogin(access_token, open_id)
            if not active_jwt:
                return generate_error_payload("Failed to convert Access Token to JWT via MajorLogin.", 401)

            current_status = "converted_from_access"

        except Exception as conversion_error:
            return generate_error_payload("External API Error during token conversion.", 500, str(conversion_error))

    return execute_nickname_change(
        jwt_token=active_jwt,
        target_name=desired_name,
        auth_type="TOKEN_BASED_AUTH",
        token_status=current_status
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)