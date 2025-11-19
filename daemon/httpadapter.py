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
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict
import base64
import socket
import json

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def _read_full_request(self, conn):
        """Helper to read the entire HTTP request from the socket safely."""
        conn.settimeout(3.0) 
        msg = b""
        
        while True:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                msg += chunk
                # Dừng lại khi kết thúc Header
                if b'\r\n\r\n' in msg:
                    return msg.decode('utf-8', errors='ignore')
            except socket.timeout:
                break
            except Exception:
                break
        
        return msg.decode('utf-8', errors='ignore') if msg else None

    def handle_client(self, conn, addr, routes):
        """
        Handle an incoming client connection.

        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        # Handle the request
        msg_decoded = self._read_full_request(conn)
        if not msg_decoded:
            conn.close()
            return
            
        req.prepare(msg_decoded, routes)

         # DEBUG LOGGING
        print(f"\n[HTTP Adapter] --- Request from {addr} ---")
        print(f"Method: {req.method}, Path: {req.path}")
        print("Headers:", dict(req.headers))
        print("Body:", req.body)
        print("----------------------------------\n")

        if routes and req.method in routes and req.path in routes[req.method]:
            print(f"[Router] Using backend handler for {req.method} {req.path}")
            
            handler = routes[req.method][req.path]

            # Handler trả về response bytes
            response = handler(req)

            conn.sendall(response)
            conn.close()
            return
        
        response_data = None 
        resp.request = req
        resp.status_code = None 

        if req.method == 'POST' and req.path == '/login':
            body_str = req.body if req.body else ""
            username, password = None, None
            
            # Giả lập parse credentials
            try:
                data = json.loads(body_str) 
                username = data.get('username')
                password = data.get('password')
            except Exception:
                if "username=admin" in body_str and "password=password" in body_str:
                    username = "admin"
                    password = "password"

            if username == "admin" and password == "password":
                resp.set_header("Set-Cookie", "auth=true; Path=/; HttpOnly")
                resp.status_code = 200
                response_data = "<html><h1>Login Success! Welcome back, Admin.</h1></html>"
                print("[Backend] Login Success.")
            else:
                resp.status_code = 401
                response_data = "401 Unauthorized - Invalid Credentials"
                print("[Backend] Login Failed.")
                
        elif req.method == 'GET' and (req.path == '/index.html' or req.path == '/'):
            cookies = req.cookies 
            if cookies.get('auth') == 'true':
                print("[Backend] Cookie Valid - Access Granted to index.")
                pass 
            else:
                resp.status_code = 401
                response_data = "401 Unauthorized - Login Required"
                print("[Backend] Access Denied - Cookie missing.")

        # Handle request hook (Cho WebApp/WeApRous)
        if req.hook and resp.status_code is None: 
            print(f"[HttpAdapter] Calling WebApp hook: {req.hook.__name__}")
            
            actual_headers = req.headers
            actual_body = req.body
            
            # Call the hook
            hook_result = req.hook(headers=actual_headers, body=actual_body)

            if hook_result is not None:
                resp.status_code = resp.status_code if resp.status_code else 200
                
                if isinstance(hook_result, dict):
                    resp.set_header("Content-Type", "application/json")
                    response_data = json.dumps(hook_result)
                else: 
                    resp.set_header("Content-Type", "text/plain")
                    response_data = str(hook_result)

        if response_data is not None:
            content_bytes = response_data.encode('utf-8') if isinstance(response_data, str) else response_data
            
            resp.set_header("Content-Length", str(len(content_bytes)))
            resp.set_header("Connection", "close")
            
            final_header = resp.build_response_header(req)
            response = final_header + content_bytes
        else:
            resp.status_code = resp.status_code if resp.status_code else 200
            response = resp.build_response(req)


        conn.sendall(response)
        conn.close()

    @property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        # cookies = {}
        # for header in self.headers:
        #     if header.startswith("Cookie:"):
        #         cookie_str = header.split(":", 1)[1].strip()
        #         for pair in cookie_str.split(";"):
        #             key, value = pair.strip().split("=")
        #             cookies[key] = value
        # return cookies
        cookies = {}
        if hasattr(req, 'cookies'):
            return dict(req.cookies) 
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        # response = Response()

        # # Set encoding.
        # response.encoding = self.get_encoding_from_headers(response.headers)
        # response.raw = resp
        # response.reason = response.raw.reason

        # if isinstance(req.url, bytes):
        #     response.url = req.url.decode("utf-8")
        # else:
        #     response.url = req.url

        # # Add new cookies from the server.
        # response.cookies = self.extract_cookies(req)

        # # Give the Response some context.
        # response.request = req
        # response.connection = self

        # return response
        return resp.build_response(req)

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        username, password = ("user1", "password")
        if username and password:
        # Encode username and password in Base64 for Basic Authentication
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            headers["Proxy-Authorization"] = f"Basic {encoded_credentials}"
    
        # Add other common proxy headers
        headers["Proxy-Connection"] = "Keep-Alive"

        if username:
            headers["Proxy-Authorization"] = (username, password)

        return headers
