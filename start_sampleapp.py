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

PORT = 8000  # Default port

app = WeApRous()

@app.route('/login', methods=['POST'])
def login(headers="guest", body="anonymous"):
    """
    Handle user login via POST request.

    This route simulates a login process and prints the provided headers and body
    to the console.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or login payload.
    """
    print "[SampleApp] Logging in {} to {}".format(headers, body)

@app.route('/hello', methods=['PUT'])
def hello(headers, body):
    """
    Handle greeting via PUT request.

    This route prints a greeting message to the console using the provided headers
    and body.

    :param headers (str): The request headers or user identifier.
    :param body (str): The request body or message payload.
    """
    print "[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body)

if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application
    app.prepare_address(ip, port)
    app.run()
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    """
    Peer registration: peer submits username, IP, and port to the centralized server.
    API Example: http://IP:port/submit-info/ [cite: 258]
    """
    # Peer registration: When a new peer joins, it must submit its IP and port to the centralized server. [cite: 241]
    
    username = body.get("username")
    peer_ip = body.get("ip")
    peer_port = body.get("port")
    
    if not (username and peer_ip and peer_port):
        return (400, {"status": "error", "message": "Missing username, ip, or port in body"})

    try:
        peer_tracker[username] = {"ip": peer_ip, "port": int(peer_port), "status": "online"}
        # Tracker update: The centralized server must maintain a tracking list of active peers. [cite: 242]
        return {"status": "ok", "message": f"Peer {username} registered.", "peer_info": peer_tracker[username]}
    except ValueError:
        return (400, {"status": "error", "message": "Port must be an integer"})


@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    """
    Peer discovery: Peers can request the current list of active peers from the server. [cite: 243]
    API Example: http://IP:port/get-list/ [cite: 259]
    """
    # Return ID and Port of activatings
    # Sort out unnecessities
    peers_list = [
        {"username": user, "ip": info["ip"], "port": info["port"]} 
        for user, info in peer_tracker.items()
    ]
    return {"status": "ok", "active_peers": peers_list}

# --- P2P Communication Setup/Broadcast (Simple RESTful Placeholders) ---
# Logic of this API (connect socket, sned/receive) is in logic P2P outside RESTful
# Being triggerred by client after returning from /get-list.

@app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    """
    Connection setup: Peers use the tracking list to initiate direct P2P connections. [cite: 244]
    This endpoint can signal the intent to connect, returning the target peer's info.
    API Example: http://IP:port/connect-peer/ [cite: 260]
    """
    target_username = body.get("target_username")
    if target_username in peer_tracker:
        target_info = peer_tracker[target_username]
        return {"status": "ok", "message": f"Connecting to {target_username}", "target_info": target_info}
    else:
        return (404, {"status": "error", "message": "Target peer not found"})

@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers, body):
    """
    Broadcast connection: A peer must broadcast messages to all connected peers. [cite: 245]
    In a RESTful context, this would trigger the server to execute the P2P broadcast logic.
    API Example: http://IP:port/broadcast-peer/ [cite: 261]
    """
    # Logic thực tế: Lấy message từ body, gửi qua socket tới các peer đã kết nối
    message = body.get("message")
    sender = body.get("username", "Unknown")
    # Giả định logic socket đã thành công
    print(f"[{sender}] Broadcasting message: {message}")
    return {"status": "ok", "message": "Broadcast signal sent (P2P logic assumed working)"}


@app.route('/send-peer', methods=['POST'])
def send_peer(headers, body):
    """
    Direct peer communication: Peers exchange messages without routing through the centralized server. [cite: 246]
    This RESTful endpoint acts as a trigger/wrapper for the P2P direct send.
    API Example: http://IP:port/send-peer/ [cite: 262]
    """
    target = body.get("target_username")
    message = body.get("message")
    sender = body.get("username", "Unknown")
    
    # Logic thực tế: Gửi message trực tiếp qua socket đến target
    print(f"[{sender}] Sending message to [{target}]: {message}")
    return {"status": "ok", "message": f"Direct send signal to {target} sent (P2P logic assumed working)"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='SampleApp', description='Start sample WeApRous app')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port
    app.prepare_address(ip, port)
    
    # In ra các route đã đăng ký để kiểm tra
    print("Registered Routes:")
    for (method, path), func in app.routes.items():
        print(f"  [{method}] {path} -> {func.__name__}")
        
    app.run()
