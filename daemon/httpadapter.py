from .request import Request
from .response import Response
import socket
import json
import urllib.parse

class HttpAdapter:
    def __init__(self, ip, port, conn, connaddr, routes):
        self.ip = ip
        self.port = port
        self.conn = conn
        self.connaddr = connaddr
        self.routes = routes
        self.request = Request()
        self.response = Response()

    def _read_full_request(self, conn):
        """Đọc toàn bộ request từ socket"""
        conn.settimeout(5.0)
        data = b""
        try:
            while True:
                chunk = conn.recv(4096)
                if not chunk: break
                data += chunk
                if len(chunk) < 4096: break 
        except socket.timeout:
            pass
        except Exception as e:
            print(f"Socket error: {e}")
        return data.decode('utf-8', errors='ignore')

    def handle_client(self, conn, addr, routes):
        self.conn = conn
        raw_request = self._read_full_request(conn)
        
        if not raw_request:
            conn.close()
            return

        # Prepare Request object
        self.request.prepare(raw_request, routes)
        req = self.request
        resp = self.response

        print(f"[Adapter] {req.method} {req.path}")

        handler = None
        if routes:
            handler = routes.get((req.method, req.path))

        if handler:
            print(f"[Router] Delegating to WebApp handler for {req.path}")
            try:
                # Gọi hàm handler từ start_sampleapp.py
                result = handler(headers=req.headers, body=req.body)
                
                # Xử lý kết quả trả về từ handler
                # Trường hợp 1: Handler trả về tuple (status, headers, body) - dùng trong hàm login sampleapp
                if isinstance(result, tuple) and len(result) == 3:
                    status, extra_headers, body_data = result
                    resp.status_code = status
                    
                    # Add headers từ handler vào response
                    for k, v in extra_headers.items():
                        resp.set_header(k, v)
                    
                    # Xử lý body
                    if isinstance(body_data, dict):
                        content = json.dumps(body_data).encode('utf-8')
                        resp.set_header("Content-Type", "application/json")
                    else:
                        content = str(body_data).encode('utf-8')
                        if "text/html" not in extra_headers.get("Content-Type", ""):
                             resp.set_header("Content-Type", "text/plain")

                # Trường hợp 2: Handler chỉ trả về dict (dùng trong các api submit-info...)
                elif isinstance(result, dict):
                    resp.status_code = 200
                    content = json.dumps(result).encode('utf-8')
                    resp.set_header("Content-Type", "application/json")
                
                # Trường hợp 3: Handler trả về string
                else:
                    resp.status_code = 200
                    content = str(result).encode('utf-8')
                    resp.set_header("Content-Type", "text/plain")

                # Gửi response
                resp.set_header("Content-Length", str(len(content)))
                response_bytes = resp.build_response_header(req) + content
                conn.sendall(response_bytes)

            except Exception as e:
                print(f"[Router] Handler Error: {e}")
                resp.status_code = 500
                err_msg = json.dumps({"status": "error", "message": str(e)}).encode()
                conn.sendall(resp.build_response_header(req) + err_msg)
            
            conn.close()
            return
        # ============================================================
        
        # Task 1A: Login Hardcoded
        if req.method == 'POST' and req.path == '/login':
            # Logic parse thô sơ cho trường hợp chạy backend thuần
            try:
                # Thử parse JSON
                data = json.loads(req.body)
                username = data.get("username")
                password = data.get("password")
            except:
                # Parse Form Data
                parsed = urllib.parse.parse_qs(req.body)
                username = parsed.get('username', [''])[0]
                password = parsed.get('password', [''])[0]

            if username == "admin" and password == "password":
                print("[Auth] Backend Login Successful")
                resp.status_code = 200
                resp.set_header("Set-Cookie", "auth=true; Path=/;")
                content = b"<html>Login Success</html>"
            else:
                print("[Auth] Backend Login Failed")
                resp.status_code = 401
                content = b"401 Unauthorized"
            
            resp.set_header("Content-Length", str(len(content)))
            conn.sendall(resp.build_response_header(req) + content)
            conn.close()
            return

        # Task 1B: Check Cookie cho trang chủ
        if req.method == 'GET' and (req.path == '/' or req.path == '/index.html'):
            cookies = req.cookies
            auth_cookie = cookies.get('auth')
            
            if auth_cookie != 'true':
                print("[Auth] Access Denied: Missing Cookie")
                # Redirect về login.html
                resp.status_code = 200 # Hoặc 401 tùy yêu cầu, nhưng redirect UX tốt hơn
                req.path = "/login.html" 
            else:
                print("[Auth] Access Granted")
                
            response_bytes = resp.build_response(req)
            conn.sendall(response_bytes)
            conn.close()
            return

        response_bytes = resp.build_response(req)
        conn.sendall(response_bytes)
        conn.close()
