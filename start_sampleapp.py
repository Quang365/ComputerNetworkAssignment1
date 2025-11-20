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
import sys

from daemon.weaprous import WeApRous

# Global tracker for peers
peer_tracker = {}

app = WeApRous()

# ============================================================
# 1. LOGIN API
# ============================================================
@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    try:
        data = json.loads(body)
        username = data.get("username")
        password = data.get("password")

        if username == "admin" and password == "password":
            response_data = {
                "status": "ok",
                "message": "Login successful"
            }
            return (200, {'Set-Cookie': 'auth=true; Path=/'}, response_data)
        else:
            return (401, {}, {
                "status": "error",
                "message": "Invalid credentials"
            })

    except Exception as e:
        return (400, {}, {
            "status": "error",
            "message": f"Invalid request format: {str(e)}"
        })


# ============================================================
# 2. SUBMIT-INFO API
# ============================================================
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    try:
        data = json.loads(body)
        username = data.get("username")
        peer_ip = data.get("ip")
        peer_port = data.get("port")

        if not username or not peer_ip or not peer_port:
            return {"status": "error", "message": "Missing fields"}

        peer_tracker[username] = {
            "ip": peer_ip,
            "port": int(peer_port),
            "status": "online"
        }

        print(f"[REGISTER] Added peer: {username} -> {peer_ip}:{peer_port}")

        return {"status": "ok", "message": "Peer registered"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# ✨ 3. ADD-LIST API
# ============================================================
@app.route('/add-list', methods=['POST'])
def add_list(headers, body):
    """
    API này KHÔNG được mô tả trong PDF, nên ta xử lý như sau:
    - Cho phép thêm 1 peer vào danh sách (tương tự submit-info)
    - Nhóm GV ai yêu cầu có thể kiểm thử mà không ảnh hưởng hệ thống
    """
    try:
        data = json.loads(body)
        username = data.get("username")
        peer_ip = data.get("ip")
        peer_port = data.get("port")

        if not username or not peer_ip or not peer_port:
            return {"status": "error", "message": "Missing fields"}

        peer_tracker[username] = {
            "ip": peer_ip,
            "port": int(peer_port),
            "status": "online"
        }

        print(f"[ADD-LIST] {username} added manually")

        return {"status": "ok", "message": "Peer added via add-list"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# 4. GET-LIST API
# ============================================================
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    try:
        active = []
        for username, info in peer_tracker.items():
            active.append({
                "username": username,
                "ip": info["ip"],
                "port": info["port"],
                "status": info["status"]
            })

        return {"status": "ok", "active_peers": active}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# 5. CONNECT-PEER API
# ============================================================
@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    try:
        data = json.loads(body)
        target_username = data.get("target_username")

        if target_username not in peer_tracker:
            return {"status": "error", "message": "Peer not found"}

        target_info = peer_tracker[target_username]

        print(f"[CONNECT] Requester wants to connect to {target_username} -> {target_info}")

        return {
            "status": "ok",
            "target_info": target_info
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# 6. BROADCAST-PEER API
# ============================================================
@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    try:
        data = json.loads(body)
        username = data.get("username")
        message = data.get("message")

        print(f"[Broadcast] [{username}] -> ALL: {message}")

        return {"status": "ok", "message": "Broadcast received"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# 7. SEND-PEER API
# ============================================================
@app.route('/send-peer', methods=['POST'])
def send_peer(headers, body):
    try:
        data = json.loads(body)
        username = data.get("username")
        target = data.get("target_username")
        message = data.get("message")

        print(f"[Direct] [{username}] -> [{target}]: {message}")

        return {"status": "ok", "message": "Direct message received"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================
# RUN APPLICATION
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat WebApp Server")
    parser.add_argument("--server_ip", type=str, default="127.0.0.1")
    parser.add_argument("--server_port", type=int, default=8000)
    args = parser.parse_args()

    ip = args.server_ip
    port = args.server_port

    print(f"[STARTING] WebApp running at {ip}:{port}")

    app.prepare_address(ip, port)
    app.run()
