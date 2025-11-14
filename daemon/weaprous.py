from .backend import create_backend

class WeApRous:
    def __init__(self):
        self.routes = {}
        self.ip = None
        self.port = None

    def prepare_address(self, ip, port):
        self.ip = ip
        self.port = port

    def route(self, path, methods=['GET']):
        # ensure list of methods
        if isinstance(methods, str):
            methods = [methods]
        def decorator(func):
            for m in methods:
                key = (m.upper(), path)
                self.routes[key] = func
            # attach meta
            func._route_path = path
            func._route_methods = methods
            return func
        return decorator

    def run(self):
        if not self.ip or not self.port:
            raise RuntimeError("WeApRous: call prepare_address(ip,port) before run()")
        # delegate to backend to create a TCP server that will use HttpAdapter
        create_backend(self.ip, self.port, self.routes)
