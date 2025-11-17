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
        self.headers = {}

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
                handle_text_other(sub_type)
        elif main_type == 'image':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='image/{}'.format(sub_type)
        elif main_type == 'application':
            base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type']='application/{}'.format(sub_type)
        #
        #  TODO: process other mime_type
        #        application/xml       
        #        application/zip
        #        ...
        #        text/csv
        #        text/xml
        #        ...
        #        video/mp4 
        #        video/mpeg
        #        ...
        #
		elif main_type == 'application':
        if sub_type in ['xml', 'json', 'zip', 'pdf']:
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type'] = f'application/{sub_type}'
        else:
            base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type'] = f'application/{sub_type}'
    elif main_type == 'text':
        if sub_type in ['csv', 'xml', 'javascript']:
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type'] = f'text/{sub_type}'
    elif main_type == 'video':
        base_dir = BASE_DIR+"static/"
        self.headers['Content-Type'] = f'video/{sub_type}'
    elif main_type == 'audio':
        base_dir = BASE_DIR+"static/"
        self.headers['Content-Type'] = f'audio/{sub_type}'
    elif main_type == 'font':
        base_dir = BASE_DIR+"static/"
        self.headers['Content-Type'] = f'font/{sub_type}'
        else:
            raise ValueError("Invalid MEME type: main_type={} sub_type={}".format(main_type,sub_type))

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
        rsphdr = self.headers

        #Build dynamic headers
        headers = {
                "Accept": "{}".format(reqhdr.get("Accept", "application/json")),
                "Accept-Language": "{}".format(reqhdr.get("Accept-Language", "en-US,en;q=0.9")),
                "Authorization": "{}".format(reqhdr.get("Authorization", "Basic <credentials>")),
                "Cache-Control": "no-cache",
                "Content-Type": "{}".format(self.headers['Content-Type']),
                "Content-Length": "{}".format(len(self._content)),
#                "Cookie": "{}".format(reqhdr.get("Cookie", "sessionid=xyz789")), #dummy cooki
        #
        # TODO prepare the request authentication
        #
		auth_header = reqhdr.get("Authorization", "")
    if auth_header.startswith("Basic "):
        # Extract and validate Basic Auth credentials
        import base64
        try:
            encoded_credentials = auth_header[6:]  # Remove "Basic " prefix
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)
            # Here you can validate credentials against your user database
            # For now, we'll just acknowledge the authentication attempt
            print(f"[Response] Authentication attempt: username={username}")
        except Exception as e:
            print(f"[Response] Auth parsing error: {e}")
		
	# self.auth = ...
                "Date": "{}".format(datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")),
                "Max-Forward": "10",
                "Pragma": "no-cache",
                "Proxy-Authorization": "Basic dXNlcjpwYXNz",  # example base64
                "Warning": "199 Miscellaneous warning",
                "User-Agent": "{}".format(reqhdr.get("User-Agent", "Chrome/123.0.0.0")),
            }

        # Header text alignment
            #
            #  TODO: implement the header building to create formated
            #        header from the provied headers
            #
		 header_lines = []
    
    # Add status line
    status_reason = "OK" if self.status_code == 200 else "Not Found"
    if hasattr(self, 'status_code') and self.status_code:
        status_reason = "OK" if self.status_code == 200 else "Not Found"
        header_lines.append(f"HTTP/1.1 {self.status_code} {status_reason}")
    else:
        header_lines.append("HTTP/1.1 200 OK")
    
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
    
    # Check if we have valid authentication from the request
    if 'Authorization' in reqhdr:
        self.auth['auth_type'] = 'Basic'
        # You can set authenticated to True if credentials are valid
        # For now, we'll mark it based on presence of auth header
        self.auth['authenticated'] = True
        
    # Check for session cookies for cookie-based auth
    if 'Cookie' in reqhdr and 'auth=true' in reqhdr['Cookie']:
        self.auth['auth_type'] = 'Cookie'
        self.auth['authenticated'] = True
        self.auth['username'] = 'authenticated_user'  # Extract from session if available
	# self.auth = ...
        return str(fmt_header).encode('utf-8')


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """

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

        path = request.path

        mime_type = self.get_mime_type(path)
        print("[Response] {} path {} mime_type {}".format(request.method, request.path, mime_type))

        base_dir = ""

        #If HTML, parse and serve embedded objects
        if path.endswith('.html') or mime_type == 'text/html':
            base_dir = self.prepare_content_type(mime_type = 'text/html')
        elif mime_type == 'text/css':
            base_dir = self.prepare_content_type(mime_type = 'text/css')
        #
        # TODO: add support objects
        #
	# Add support for JavaScript files
	elif mime_type == 'application/javascript' or path.endswith('.js'):
        base_dir = self.prepare_content_type(mime_type = 'application/javascript')
    
    # Add support for images
    elif mime_type.startswith('image/'):
        base_dir = self.prepare_content_type(mime_type = mime_type)
    
    # Add support for JSON files
    elif mime_type == 'application/json' or path.endswith('.json'):
        base_dir = self.prepare_content_type(mime_type = 'application/json')
    
    # Add support for plain text files
    elif mime_type == 'text/plain' or path.endswith('.txt'):
        base_dir = self.prepare_content_type(mime_type = 'text/plain')
    
    # Add support for PDF files
    elif mime_type == 'application/pdf' or path.endswith('.pdf'):
        base_dir = self.prepare_content_type(mime_type = 'application/pdf')
    
    # Add support for XML files
    elif mime_type == 'application/xml' or path.endswith('.xml'):
        base_dir = self.prepare_content_type(mime_type = 'application/xml')
    
    # Add support for ZIP files
    elif mime_type == 'application/zip' or path.endswith('.zip'):
        base_dir = self.prepare_content_type(mime_type = 'application/zip')
        else:
            return self.build_notfound()

        c_len, self._content = self.build_content(path, base_dir)
        self._header = self.build_response_header(request)

        return self._header + self._content
