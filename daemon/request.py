from .dictionary import CaseInsensitiveDict

class Request():
    def __init__(self):
        self.method = None
        self.path = None
        self.version = None
        self.headers = CaseInsensitiveDict()
        self.cookies = {}
        self.body = ""
        self.hook = None

    def prepare(self, raw_request, routes=None):
        if not raw_request:
            return

        # Tách header và body
        parts = raw_request.split('\r\n\r\n', 1)
        header_part = parts[0]
        self.body = parts[1] if len(parts) > 1 else ""

        # Parse Request Line
        lines = header_part.splitlines()
        if len(lines) > 0:
            req_line = lines[0].split()
            if len(req_line) >= 2:
                self.method = req_line[0].upper()
                self.path = req_line[1]
                if len(req_line) > 2: self.version = req_line[2]

        # Parse Headers
        for line in lines[1:]:
            if ': ' in line:
                k, v = line.split(': ', 1)
                self.headers[k] = v

        # Parse Cookies
        self.parse_cookies()

    def parse_cookies(self):
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            items = cookie_header.split(';')
            for item in items:
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    self.cookies[k] = v
