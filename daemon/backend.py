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
daemon.backend
~~~~~~~~~~~~~~~~~

This module provides a backend object to manage and persist backend daemon. 
It implements a basic backend server using Python's socket and threading libraries.
It supports handling multiple client connections concurrently and routing requests using a
custom HTTP adapter.

Requirements:
--------------
- socket: provide socket networking interface.
- threading: Enables concurrent client handling via threads.
- response: response utilities.
- httpadapter: the class for handling HTTP requests.
- CaseInsensitiveDict: provides dictionary for managing headers or routes.


Notes:
------
- The server create daemon threads for client handling.
- The current implementation error handling is minimal, socket errors are printed to the console.
- The actual request processing is delegated to the HttpAdapter class.

Usage Example:
--------------
>>> create_backend("127.0.0.1", 9000, routes={})

"""

import socket
import threading
import argparse

from .response import *
from .httpadapter import HttpAdapter
from .dictionary import CaseInsensitiveDict

def handle_client(ip, port, conn, addr, routes):
    """
    Initializes an HttpAdapter instance and delegates the client handling logic to it.

    :param ip (str): IP address of the server.
    :param port (int): Port number the server is listening on.
    :param conn (socket.socket): Client connection socket.
    :param addr (tuple): client address (IP, port).
    :param routes (dict): Dictionary of route handlers.
    """
    daemon = HttpAdapter(ip, port, conn, addr, routes)

    # Handle client
    daemon.handle_client(conn, addr, routes)

def run_backend(ip, port, routes):
    """
    Starts the backend server, binds to the specified IP and port, and listens for incoming
    connections. Each connection is handled in a separate thread. The backend accepts incoming
    connections and spawns a thread for each client.


    :param ip (str): IP address to bind the server.
    :param port (int): Port number to listen on.
    :param routes (dict): Dictionary of route handlers.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.bind((ip, port))
        server.listen(50)
        print("[Backend] Listening on port {}".format(port))
        if routes != {}:
            print("[Backend] route settings {}".format(routes))

        while True:
            conn, addr = server.accept()
            #
            #  TODO: implement the step of the client incomping connection
            #        using multi-thread programming with the
            #        provided handle_client routine
            #
     print("[Backend] New connection from {}".format(addr))
            client_thread = threading.Thread(
                target=handle_client,
                args=(ip, port, conn, addr, routes)
            )
            client_thread.daemon = True  
            client_thread.start()

    except socket.error as e:
      print("Socket error: {}".format(e))

def setup_auth_routes():
    """
    Setup routes for authentication and protected resources
    """
    routes = {
        'GET': {
            '/': handle_main_page,
            '/login': show_login_page
        },
        'POST': {
            '/login': handle_login
        }
    }
    return routes

def handle_main_page(request):
    """
    Handle GET / - Check if user is authenticated via cookie
    """
    # Check for authentication cookie
    if hasattr(request, 'cookies') and 'auth' in request.cookies:
        if request.cookies['auth'] == 'true':
            # User is authenticated - serve main page
            response = Response(request)
            # You'll need to implement serve_static_file or similar
            return response.build_response(request)
    
    # Not authenticated - redirect to login or show 401
    response = Response(request)
    response.status_code = 401
    return response.build_notfound()

def handle_login(request):
    """
    Handle POST /login - Validate credentials and set cookie
    """
    # Parse form data from request body
    import urllib.parse
    if hasattr(request, 'body'):
        body_params = urllib.parse.parse_qs(request.body)
        username = body_params.get('username', [''])[0]
        password = body_params.get('password', [''])[0]
    else:
        username = ''
        password = ''
    
    # Validate credentials (hardcoded for demo)
    if username == 'admin' and password == 'password':
        # Login successful
        response = Response(request)
        response.status_code = 200
        response.headers['Set-Cookie'] = 'auth=true; Path=/'
        
        # You might want to serve a success page or redirect
        return response.build_response(request)
    else:
        # Login failed
        response = Response(request)
        response.status_code = 401
        response.headers['Content-Type'] = 'text/html'
        # Return error page
        return response.build_notfound()

def show_login_page(request):
    """
    Handle GET /login - Show login form
    """
    response = Response(request)
    response.status_code = 200
    # You'll need to serve the actual login HTML page
    return response.build_response(request)

def create_backend(ip, port, routes={}):
    """
    Entry point for creating and running the backend server.

    :param ip (str): IP address to bind the server.
    :param port (int): Port number to listen on.
    :param routes (dict, optional): Dictionary of route handlers. Defaults to empty dict.
    """

    run_backend(ip, port, routes)
