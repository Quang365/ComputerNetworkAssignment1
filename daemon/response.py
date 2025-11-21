#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist 
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests. 

The current version supports MIME type detection, content loading and header formatting
"""
# daemon/response.py

import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

# Đặt đường dẫn gốc là thư mục hiện tại nơi chạy file start_*.py
BASE_DIR = os.getcwd()

class Response():   
    def __init__(self, request=None):
        self._content = b""
        self.status_code = 200
        self.headers = CaseInsensitiveDict()
        self.request = request
        self.encoding = 'utf-8'

    def set_header(self, key, value):
        self.headers[key] = value

    def get_mime_type(self, path):
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type or 'application/octet-stream'

    def prepare_content_type(self, mime_type='text/html'):
        """
        Xác định thư mục dựa trên mime_type
        """
        base_dir = os.path.join(BASE_DIR, "www") # Mặc định
        
        if mime_type.startswith('text/html'):
             self.headers['Content-Type'] = mime_type
             base_dir = os.path.join(BASE_DIR, "www")
        elif mime_type.startswith('image'):
             self.headers['Content-Type'] = mime_type
             base_dir = os.path.join(BASE_DIR, "static", "images")
        elif mime_type == 'text/css':
             self.headers['Content-Type'] = mime_type
             base_dir = os.path.join(BASE_DIR, "static", "css")
        elif mime_type == 'application/javascript' or mime_type.endswith('javascript'):
             self.headers['Content-Type'] = mime_type
             base_dir = os.path.join(BASE_DIR, "static", "js")
        else:
             self.headers['Content-Type'] = mime_type
             base_dir = os.path.join(BASE_DIR, "static") # Fallback

        return base_dir

    def build_content(self, path, base_dir):
        """
        Đọc file từ ổ cứng
        """
        # Loại bỏ dấu / ở đầu để os.path.join hoạt động đúng
        clean_path = path.lstrip('/')
        # Nếu path là images/abc.png mà base_dir đã là static/images, ta chỉ lấy tên file
        filename = os.path.basename(clean_path)
        
        filepath = os.path.join(base_dir, filename)
        
        # Fallback: Nếu không tìm thấy ở base_dir cụ thể, thử tìm ở root/path
        if not os.path.exists(filepath):
             filepath = os.path.join(BASE_DIR, clean_path)

        print(f"[Response] Reading file: {filepath}")

        if os.path.exists(filepath) and os.path.isfile(filepath):
            try:
                with open(filepath, 'rb') as f:
                    content = f.read()
                return len(content), content
            except Exception as e:
                print(f"[Response] Read Error: {e}")
                return 0, b""
        else:
            return 0, b""

    def build_response_header(self, request):
        # Header cơ bản
        status_text = {
            200: "OK",
            401: "Unauthorized",
            404: "Not Found",
            400: "Bad Request"
        }.get(self.status_code, "OK")

        header_lines = [f"HTTP/1.1 {self.status_code} {status_text}"]
        
        # Thêm các header mặc định nếu chưa có
        if 'Date' not in self.headers:
            self.headers['Date'] = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        if 'Server' not in self.headers:
            self.headers['Server'] = "WeApRous/1.0"
        if 'Connection' not in self.headers:
            self.headers['Connection'] = "close"

        for key, value in self.headers.items():
            header_lines.append(f"{key}: {value}")
        
        header_lines.append("\r\n") # Dòng trống kết thúc header
        return "\r\n".join(header_lines).encode('utf-8')

    def build_notfound(self):
        self.status_code = 404
        content = b"<h1>404 Not Found</h1>"
        self.headers['Content-Type'] = 'text/html'
        self.headers['Content-Length'] = str(len(content))
        return self.build_response_header(self.request) + content

    def build_response(self, request):
        self.request = request
        path = request.path

        # Xử lý trang chủ mặc định
        if path == '/' or path == '/index.html':
            path = 'index.html'
            mime_type = 'text/html'
        else:
            mime_type = self.get_mime_type(path)

        base_dir = self.prepare_content_type(mime_type)
        c_len, self._content = self.build_content(path, base_dir)

        if c_len == 0 and self._content == b"":
            return self.build_notfound()

        self.status_code = 200
        self.headers['Content-Length'] = str(c_len)
        
        header_bytes = self.build_response_header(request)
        return header_bytes + self._content
