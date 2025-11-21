"""
daemon.proxy
~~~~~~~~~~~~~~~~~
Module này triển khai proxy server đơn giản sử dụng socket và threading.
"""

import socket
import threading

# Biến toàn cục để theo dõi round-robin
g_round_robin_index = {}

def forward_request(host, port, request_data):
    """
    Gửi request tới backend và nhận toàn bộ response.
    """
    backend = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        backend.connect((host, int(port)))
        backend.sendall(request_data.encode('utf-8'))
        
        response = b""
        while True:
            chunk = backend.recv(4096)
            if not chunk:
                break
            response += chunk
            
        backend.close()
        return response
    except socket.error as e:
        print(f"[Proxy] Error forwarding to {host}:{port} - {e}")
        return (
            "HTTP/1.1 502 Bad Gateway\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "Content-Length: 15\r\n"
            "\r\n"
            "502 Bad Gateway"
        ).encode('utf-8')

def resolve_routing_policy(hostname, routes):
    """
    Xác định backend dựa trên hostname và policy.
    """
    target = routes.get(hostname)
    
    # Fallback nếu không tìm thấy
    if not target:
        # Fallback về localhost:9000 nếu không match
        return '127.0.0.1', 9000

    proxy_map, policy = target
    
    proxy_host = '127.0.0.1'
    proxy_port = 9000

    # Xử lý list (proxy_pass)
    if isinstance(proxy_map, list) and len(proxy_map) > 0:
        if len(proxy_map) == 1:
            url = proxy_map[0]
            if ":" in url:
                proxy_host, proxy_port = url.split(":", 1)
            else:
                proxy_host = url
                proxy_port = 80
        else:
            # Round Robin
            global g_round_robin_index
            if hostname not in g_round_robin_index:
                g_round_robin_index[hostname] = 0
            
            idx = g_round_robin_index[hostname]
            url = proxy_map[idx]
            
            if ":" in url:
                proxy_host, proxy_port = url.split(":", 1)
            else:
                proxy_host = url
                proxy_port = 80
            
            g_round_robin_index[hostname] = (idx + 1) % len(proxy_map)
            
    elif isinstance(proxy_map, str):
         if ":" in proxy_map:
                proxy_host, proxy_port = proxy_map.split(":", 1)

    return proxy_host, int(proxy_port)

def handle_client(ip, port, conn, addr, routes):
    """
    Xử lý kết nối từ Client tới Proxy.
    """
    try:
        request = conn.recv(4096).decode('utf-8', errors='ignore')
        if not request:
            conn.close()
            return

        # 1. Tách Host Header
        hostname = ""
        for line in request.splitlines():
            if line.lower().startswith('host:'):
                hostname = line.split(':', 1)[1].strip()
                break
        
        if not hostname:
            hostname = "127.0.0.1"

        # 2. [QUAN TRỌNG] Loại bỏ Port khỏi Hostname (ví dụ localhost:8080 -> localhost)
        # Để khớp với key trong file config
        if ':' in hostname:
            hostname = hostname.split(':')[0]

        print(f"[Proxy] Request from {addr} -> Host: {hostname}")

        # 3. Tìm địa chỉ Backend
        resolved_host, resolved_port = resolve_routing_policy(hostname, routes)
        
        print(f"[Proxy] Routing {hostname} ===> {resolved_host}:{resolved_port}")
        
        # 4. Forward
        response = forward_request(resolved_host, resolved_port, request)
        conn.sendall(response)

    except Exception as e:
        print(f"[Proxy] Handle Client Error: {e}")
    finally:
        conn.close()

def run_proxy(ip, port, routes):
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        proxy.bind((ip, port))
        proxy.listen(50)
        print(f"[Proxy] Listening on {ip}:{port}")
        
        while True:
            conn, addr = proxy.accept()
            client_thread = threading.Thread(
                target=handle_client, 
                args=(ip, port, conn, addr, routes)
            )
            client_thread.daemon = True
            client_thread.start()
            
    except socket.error as e:
        print(f"Socket error: {e}")
    finally:
        proxy.close()

def create_proxy(ip, port, routes):
    run_proxy(ip, port, routes)
