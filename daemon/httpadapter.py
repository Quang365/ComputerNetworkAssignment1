import json
import urllib.parse
from .dictionary import CaseInsensitiveDict

CRLF = "\r\n"

class HttpAdapter:
    def __init__(self, ip, port, conn, connaddr, routes):
        self.ip = ip
        self.port = port
        self.conn = conn
        self.connaddr = connaddr
        self.routes = routes or {}

    def _recv_all(self, conn, buf=4096):
        # 1. Read headers (until \r\n\r\n)
        data = b""
        header_end = -1
        conn.settimeout(5.0) # Tăng timeout lên 5s để ổn định hơn
        try:
            while header_end == -1:
                chunk = conn.recv(buf)
                if not chunk:
                    break
                data += chunk
                header_end = data.find(b"\r\n\r\n")

            if header_end == -1:
                return data # Trả về dữ liệu nếu không tìm thấy header end

            # 2. Extract Content-Length
            header_part = data[:header_end].decode(errors="ignore")
            content_length = 0
            
            for line in header_part.splitlines():
                if line.lower().startswith("content-length:"):
                    try:
                        content_length = int(line.split(":",1)[1].strip())
                        break
                    except Exception:
                        pass
            
            # 3. Read the rest of the body based on Content-Length
            if content_length > 0:
                body_start = header_end + 4 # 4 bytes for \r\n\r\n
                body_read = len(data) - body_start
                
                # Nếu body chưa đọc đủ, tiếp tục đọc cho đến khi đủ Content-Length
                while body_read < content_length:
                    remaining = content_length - body_read
                    chunk = conn.recv(min(buf, remaining)) # Đọc lượng còn thiếu
                    if not chunk:
                        # Client đóng kết nối giữa chừng
                        break
                    data += chunk
                    body_read += len(chunk)

        except Exception:
            # timeout or socket closed
            pass
        
        return data

    def _parse_request(self, raw_bytes):
        text = raw_bytes.decode("utf-8", errors="ignore")
        parts = text.split("\r\n\r\n", 1)
        header_block = parts[0]
        body = parts[1] if len(parts) > 1 else ""
        lines = header_block.splitlines()
        request_line = lines[0] if lines else ""
        method, path, proto = ("", "", "")
        try:
            method, path, proto = request_line.split()
        except ValueError:
            # malformed
            pass
        headers = CaseInsensitiveDict()
        for h in lines[1:]:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()
        return method.upper(), path, proto, headers, body

    def _parse_cookies(self, headers):
        cookies = {}
        cookie_hdr = None
        # CaseInsensitiveDict supports .get
        cookie_hdr = headers.get("Cookie") or headers.get("cookie")
        if cookie_hdr:
            parts = cookie_hdr.split(";")
            for p in parts:
                if "=" in p:
                    k, v = p.split("=", 1)
                    cookies[k.strip()] = v.strip()
        return cookies

    def _parse_body(self, content_type, body_text):
        # handle application/x-www-form-urlencoded and application/json
        if not body_text:
            return {}
        if content_type:
            ct = content_type.split(";")[0].strip().lower()
        else:
            ct = ""
        if ct == "application/x-www-form-urlencoded":
            return dict(urllib.parse.parse_qsl(body_text))
        if ct == "application/json":
            try:
                return json.loads(body_text)
            except Exception:
                return {}
        # fallback: try parse as urlencoded
        try:
            return dict(urllib.parse.parse_qsl(body_text))
        except Exception:
            return {"body": body_text}

    def _build_response(self, status_code=200, reason="OK", body=b"", extra_headers=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        headers = {
            "Server": "WeApRous-Proxy",
            "Content-Length": str(len(body)),
            "Connection": "close",
        }
        if extra_headers:
            headers.update(extra_headers)
        # default content-type if not provided
        if "Content-Type" not in headers:
            headers["Content-Type"] = "text/html; charset=utf-8"
        lines = []
        lines.append(f"HTTP/1.1 {status_code} {reason}")
        for k, v in headers.items():
            lines.append(f"{k}: {v}")
        head = CRLF.join(lines) + CRLF + CRLF
        return head.encode("utf-8") + body

    def handle_client(self, conn, addr, routes):
        """
        Main entry point to handle a connection.
        - parse request
        - check cookie auth for GET /
        - handle POST /login
        - dispatch to registered route if exists
        - else: return 404
        """
        try:
            raw = self._recv_all(conn)
            if not raw:
                conn.close()
                return
            method, path, proto, headers, body = self._parse_request(raw)
            cookies = self._parse_cookies(headers)
            content_type = headers.get("Content-Type") or headers.get("content-type") or ""
            parsed_body = self._parse_body(content_type, body)

            # Normalize path (ignore query string)
            path_only = path.split("?", 1)[0]

            # --- COOKIE AUTH: GET /
            if method == "GET" and path_only == "/":
                if cookies.get("auth") == "true":
                    # serve simple index page (could be read from static file)
                    html = (
                        "<html><head><title>Index</title></head>"
                        "<body><h1>Welcome — authenticated</h1>"
                        "<p>You are logged in (cookie auth=true)</p>"
                        "</body></html>"
                    )
                    resp = self._build_response(200, "OK", html, {"Content-Type": "text/html; charset=utf-8"})
                    conn.sendall(resp)
                    conn.close()
                    return
                else:
                    body401 = "<html><body><h1>401 Unauthorized</h1><p>Please login</p></body></html>"
                    resp = self._build_response(401, "Unauthorized", body401, {"Content-Type":"text/html; charset=utf-8"})
                    conn.sendall(resp)
                    conn.close()
                    return

            # --- LOGIN: POST /login
            if method in ("POST", "PUT") and path_only == "/login":
                # accept JSON or form
                username = parsed_body.get("username") or parsed_body.get("user") or ""
                password = parsed_body.get("password") or parsed_body.get("pass") or ""

                # accept body raw "username=...&password=..." or JSON
                if username == "admin" and password == "password":
                    # success -> set cookie
                    html = "<html><body><h1>Login success</h1><p>Cookie set.</p></body></html>"
                    headers_out = {
                        "Set-Cookie": "auth=true; Path=/; HttpOnly",
                        "Content-Type": "text/html; charset=utf-8"
                    }
                    resp = self._build_response(200, "OK", html, headers_out)
                    conn.sendall(resp)
                    conn.close()
                    return
                else:
                    body401 = "<html><body><h1>401 Unauthorized</h1><p>Invalid credentials</p></body></html>"
                    resp = self._build_response(401, "Unauthorized", body401, {"Content-Type":"text/html; charset=utf-8"})
                    conn.sendall(resp)
                    conn.close()
                    return

            # --- Route dispatch to app handlers (WeApRous)
            key = (method.upper(), path_only)
            if key in (routes or {}):
                handler = routes[key]
                # call handler; allow handler to return dict/string/tuple(status, body, headers)
                try:
                    result = handler(headers, parsed_body)
                except TypeError:
                    # handler might expect different signature (body only)
                    try:
                        result = handler(parsed_body)
                    except Exception as e:
                        result = {"error": str(e)}
                # Interpret result
                status = 200
                extra = {}
                body_out = b""
                if result is None:
                    body_out = b""
                    extra["Content-Type"] = "text/plain; charset=utf-8"
                elif isinstance(result, tuple) and len(result) >= 2:
                    # (status, payload) or (status, payload, headers)
                    status = int(result[0])
                    payload = result[1]
                    if isinstance(payload, (dict, list)):
                        body_out = json.dumps(payload).encode("utf-8")
                        extra["Content-Type"] = "application/json; charset=utf-8"
                    elif isinstance(payload, bytes):
                        body_out = payload
                    else:
                        body_out = str(payload).encode("utf-8")
                    if len(result) == 3 and isinstance(result[2], dict):
                        extra.update(result[2])
                elif isinstance(result, (dict, list)):
                    body_out = json.dumps(result).encode("utf-8")
                    extra["Content-Type"] = "application/json; charset=utf-8"
                elif isinstance(result, bytes):
                    body_out = result
                else:
                    body_out = str(result).encode("utf-8")
                    extra["Content-Type"] = "text/plain; charset=utf-8"

                resp = self._build_response(status, "OK", body_out, extra)
                conn.sendall(resp)
                conn.close()
                return

            # --- If reaches here: not found
            body404 = "<html><body><h1>404 Not Found</h1><p>Resource not found</p></body></html>"
            resp = self._build_response(404, "Not Found", body404, {"Content-Type":"text/html; charset=utf-8"})
            conn.sendall(resp)
            conn.close()
        except Exception as e:
            try:
                body500 = "<html><body><h1>500 Internal Server Error</h1><pre>{}</pre></body></html>".format(str(e))
                resp = self._build_response(500, "Internal Error", body500, {"Content-Type":"text/html; charset=utf-8"})
                conn.sendall(resp)
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
