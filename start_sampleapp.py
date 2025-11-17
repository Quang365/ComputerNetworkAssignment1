#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import socket
import argparse

from daemon.weaprous import WeApRous

PORT = 8000 # Default port

# KHAI BÁO BIẾN TOÀN CỤC BỔ SUNG: peer_tracker
# Đây là nơi Server/Tracker lưu trữ thông tin các Peer đang hoạt động (username, ip, port)
peer_tracker = {}

app = WeApRous()

# --- 1. LOGIN (Cần sửa để đáp ứng Task 1A) ---
@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user login via POST request, implementing Task 1A.
    Nếu thành công, trả về Set-Cookie: auth=true và trang index.
    """
    
    # Giả định body đã được parse thành dictionary chứa 'username' và 'password'
    # (Nếu body là string, cần parse ở đây hoặc trong HttpAdapter)
    
    # Kiểm tra điều kiện xác thực (Task 1A) [cite: 172]
    # Ví dụ: Giả sử body là JSON đã parse. Nếu body là string, bạn cần parse nó.
    
    # Nếu body là chuỗi JSON, bạn cần parse nó.
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return (400, {"status": "error", "message": "Invalid JSON in body"})

    username = data.get("username")
    password = data.get("password")
    
    # Xác thực cứng theo yêu cầu đề bài: username=admin, password=password [cite: 172]
    if username == "admin" and password == "password":
        # Thành công: Cần trả về response code 200/OK và Set-Cookie [cite: 173]
        
        # Ghi chú: Logic Set-Cookie (thêm header) sẽ cần được thực hiện trong daemon/response.py
        # Ở đây, ta chỉ trả về dữ liệu và HttpAdapter/Response sẽ lo phần header.
        response_data = {"status": "ok", "message": "Login successful"}
        
        # Trả về status code (200) và dữ liệu. 
        # Cần một cơ chế để WebApRous/Backend biết để thêm cookie 'auth=true'.
        # Một cách là trả về một tuple (code, headers_dict, body)
        return (200, {'Set-Cookie': 'auth=true; Path=/'}, response_data)
        
    else:
        # Thất bại: Trả về 401 Unauthorized [cite: 174]
        return (401, {"status": "error", "message": "Invalid credentials"})


@app.route('/hello', methods=['PUT'])
def hello(headers, body):
    """
    Handle greeting via PUT request.
    """
    print "[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body)


# --- 2. CLIENT-SERVER (Peer Management) ---

@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    Peer registration: peer submits username, IP, and port to the centralized server. [cite: 241]
    API Example: http://IP:port/submit-info/ [cite: 258]
    """
    # Parse body
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return (400, {"status": "error", "message": "Invalid JSON in body"})

    username = data.get("username")
    peer_ip = data.get("ip")
    peer_port_str = data.get("port")
    
    if not (username and peer_ip and peer_port_str):
        return (400, {"status": "error", "message": "Missing username, ip, or port in body"})

    try:
        peer_port = int(peer_port_str)
        # Tracker update: The centralized server must maintain a tracking list of active peers. [cite: 242]
        global peer_tracker # Dùng global để cập nhật biến toàn cục
        peer_tracker[username] = {"ip": peer_ip, "port": peer_port, "status": "online"}
        
        return {"status": "ok", "message": f"Peer {username} registered.", "peer_info": peer_tracker[username]}
    except ValueError:
        return (400, {"status": "error", "message": "Port must be an integer"})


@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """
    Peer discovery: Peers can request the current list of active peers from the server. [cite: 243]
    API Example: http://IP:port/get-list/ [cite: 259]
    """
    peers_list = [
        {"username": user, "ip": info["ip"], "port": info["port"]} 
        for user, info in peer_tracker.items()
    ]
    return {"status": "ok", "active_peers": peers_list}

# --- 3. P2P Communication Triggers (Giả lập) ---

@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    """
    Connection setup: Peers use the tracking list to initiate direct P2P connections. [cite: 244]
    API Example: http://IP:port/connect-peer/ [cite: 260]
    """
    try:
        data = json.loads(body)
        target_username = data.get("target_username")
    except (json.JSONDecodeError, AttributeError):
        return (400, {"status": "error", "message": "Invalid body format"})
        
    if target_username in peer_tracker:
        target_info = peer_tracker[target_username]
        return {"status": "ok", "message": f"Connecting to {target_username}", "target_info": target_info}
    else:
        return (404, {"status": "error", "message": "Target peer not found"})

@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    """
    Broadcast connection: A peer must broadcast messages to all connected peers. [cite: 245]
    API Example: http://IP:port/broadcast-peer/ [cite: 261]
    """
    try:
        data = json.loads(body)
        message = data.get("message")
        sender = data.get("username", "Unknown")
    except (json.JSONDecodeError, AttributeError):
        return (400, {"status": "error", "message": "Invalid body format"})
        
    print(f"[{sender}] Broadcasting message: {message}")
    return {"status": "ok", "message": "Broadcast signal sent (P2P logic assumed working)"}


@app.route('/send-peer', methods=['POST'])
def send_peer(headers, body):
    """
    Direct peer communication: Peers exchange messages without routing through the centralized server. [cite: 246]
    API Example: http://IP:port/send-peer/ [cite: 262]
    """
    try:
        data = json.loads(body)
        target = data.get("target_username")
        message = data.get("message")
        sender = data.get("username", "Unknown")
    except (json.JSONDecodeError, AttributeError):
        return (400, {"status": "error", "message": "Invalid body format"})
        
    print(f"[{sender}] Sending message to [{target}]: {message}")
    return {"status": "ok", "message": f"Direct send signal to {target} sent (P2P logic assumed working)"}


# --- 4. KHỐI KHỞI ĐỘNG CHÍNH (CHỈ GIỮ MỘT LẦN) ---
if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='SampleApp', description='Start sample WeApRous app')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port
    
    # Chuẩn bị và khởi động ứng dụng
    app.prepare_address(ip, port)
    
    print("Registered Routes:")
    # Vì WeApRous lưu routes là dictionary, bạn có thể in ra để kiểm tra
    if hasattr(app, 'routes'):
        for (method, path), func in app.routes.items():
            print(f"  [{method}] {path} -> {func.__name__}")
    
    app.run()
