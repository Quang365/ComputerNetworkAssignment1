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
import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

BASE_DIR = ""

class Response():   
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    :class:`Response <Response>` object encapsulates headers, content, 
    status code, cookies, and metadata related to the request-response cycle.
    It is used to construct and serve HTTP responses in a custom web server.

    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrsencoding (str): encoding used for decoding response content.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.

    Usage::

      >>> import Response
      >>> resp = Response()
      >>> resp.build_response(req)
      >>> resp
      <Response>
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.

        : params request : The originating request object.
        """

        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-type']`` will return the
        #: value of a ``'Content-Type'`` response header.
        self.headers = CaseInsensitiveDict()

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None

    def set_header(self, key, value):
        """
        Helper function to set a specific header in the response.
        """
        self.headers[key] = value

    def build_custom_response(self, content_data):
        """
        Builds a complete HTTP response from custom data (Task 1/Hook logic).
        """
        content_bytes = content_data.encode('utf-8') if isinstance(content_data, str) else content_data
        
        # Đảm bảo Content-Length được set cho custom response
        self.set_header("Content-Length", str(len(content_bytes)))
        
        # Đảm bảo Content-Type được set nếu chưa có
        if not self.headers.get('Content-Type'):
            self.set_header("Content-Type", "text/html") 
            
        if self.status_code is None:
            self.status_code = 200

        header_bytes = self.build_response_header(self.request)
        return header_bytes + content_bytes

    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.

        "params path (str): Path to the file.

        :rtype str: MIME type string (e.g., 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'


    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.

        :params mime_type (str): MIME type of the requested resource.

        :rtype str: Base directory path for locating the resource.

        :raises ValueError: If the MIME type is unsupported.
        """
        
        base_dir = ""

        # Processing mime_type based on main_type and sub_type
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type,sub_type))
        if main_type == 'text':
            self.headers['Content-Type']='text/{}'.format(sub_type)
            if sub_type == 'plain' or sub_type == 'css':
                base_dir = BASE_DIR+"static/"
            elif sub_type == 'html':
                base_dir = BASE_DIR+"www/"
            else:
                pass
        elif main_type == 'image':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application':
            self.headers['Content-Type']='application/{}'.format(sub_type)
            base_dir = BASE_DIR+"www/"
        elif main_type == 'video' or main_type == 'audio' or main_type == 'font':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']=mime_type
        else:
            raise ValueError("Invalid MIME type: main_type={} sub_type={}".format(main_type,sub_type))

        return base_dir


    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.

        :params path (str): relative path to the file.
        :params base_dir (str): base directory where the file is located.

        :rtype tuple: (int, bytes) representing content length and content data.
        """

        filepath = os.path.join(base_dir, path.lstrip('/'))

        print("[Response] serving the object at location {}".format(filepath))
            #
            #  TODO: implement the step of fetch the object file
            #        store in the return value of content
            #
        try:
        # Check if file exists
            if not os.path.exists(filepath):
                print(f"[Response] File not found: {filepath}")
                return 0, b""
        
        # Read file content
            with open(filepath, 'rb') as file:
                content = file.read()
            
            print(f"[Response] Successfully loaded {len(content)} bytes from {filepath}")

        except Exception as e:
            print(f"[Response] Error reading file {filepath}: {e}")
            content = b""

        return len(content), content


    def build_response_header(self, request):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.

        :rtypes bytes: encoded HTTP response header.
        """
        reqhdr = request.headers

        #Build dynamic headers
        headers = {
                "Accept": "{}".format(reqhdr.get("Accept", "application/json")),
                "Accept-Language": "{}".format(reqhdr.get("Accept-Language", "en-US,en;q=0.9")),
                "Authorization": "{}".format(reqhdr.get("Authorization", "")), 
                "Cache-Control": "no-cache",
                "Content-Type": "{}".format(self.headers.get('Content-Type', 'text/html')),
                "Content-Length": "{}".format(self.headers.get('Content-Length', '0')), 
                "Date": "{}".format(datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")),
                "Max-Forward": "10",
                "Pragma": "no-cache",
                "Warning": "199 Miscellaneous warning",
                "User-Agent": "{}".format(reqhdr.get("User-Agent", "WeApRous/1.0")),
        }

        # Header text alignment
            #
            #  TODO: implement the header building to create formated
            #        header from the provied headers
            #
        for key, value in self.headers.items():
            if key not in headers and key != 'Content-Length': 
                 headers[key] = value
        header_lines = []
    
        # Add status line
        status_code = self.status_code if self.status_code else 200
        status_reason = "OK"
        if status_code == 404: status_reason = "Not Found"
        if status_code == 401: status_reason = "Unauthorized"
        
        header_lines.append(f"HTTP/1.1 {status_code} {status_reason}")
    
        # Add all headers
        for key, value in headers.items():
            if value and value != "None":  # Only add if value is not empty or "None"
                header_lines.append(f"{key}: {value}")
    
        # Add empty line to separate headers from body
        header_lines.append("")
        header_lines.append("")
    
        fmt_header = "\r\n".join(header_lines)
        #
        # TODO prepare the request authentication
        #
	    # Set up authentication object for the response
        # This can be used for session management or further auth processing
        self.auth = {
            'authenticated': False,
            'username': None,
            'auth_type': None
        }
    
        return str(fmt_header).encode('utf-8')


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """
        self.status_code = 404
        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 13\r\n"
                "Cache-Control: max-age=86000\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')


    def build_response(self, request):
        """
        Builds a full HTTP response including headers and content based on the request.

        :params request (class:`Request <Request>`): incoming request object.

        :rtype bytes: complete HTTP response using prepared headers and content.
        """

        self.request = request
        path = request.path

        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""

        #If HTML, parse and serve embedded objects
        # if path.endswith('.html') or mime_type == 'text/html':
        #     base_dir = self.prepare_content_type(mime_type = 'text/html')
        # elif mime_type == 'text/css':
        #     base_dir = self.prepare_content_type(mime_type = 'text/css')
        # #
        # # TODO: add support objects
        # #

        # c_len, self._content = self.build_content(path, base_dir)
        # self._header = self.build_response_header(request)

        if path == '/' or path == '/index.html':
             mime_type = 'text/html'
             path = '/index.html' # Đảm bảo path là /index.html
             
        base_dir = self.prepare_content_type(mime_type)

        # Try to load content
        c_len, self._content = self.build_content(path, base_dir)
        
        if c_len == 0 and not self._content:
             return self.build_notfound()
        
        # Set Content-Length cho header tĩnh
        self.set_header('Content-Length', str(c_len))
        self.status_code = 200

        self._header = self.build_response_header(request)

        return self._header + self._content
