import base64

class HTTPReq:
    def __init__(self, method, route, version, headers, body):
        self.method = method
        self.route = route
        self.version = version
        self.headers = headers
        self.body = body

    def get_cookies(self):
        cookies = {}
        if 'Cookie' in self.headers:
            for kv in self.headers['Cookie'].split(';'):
                if '=' in kv:
                    k,v = kv.strip().split('=',1)
                    cookies[k] = v
        return cookies

class HTTPResp:
    def __init__(self, version='HTTP/1.1', status_code=200, reason='OK', headers=None, body=b''):
        self.version = version
        self.status_code = status_code
        self.reason = reason
        self.headers = headers or {}
        self.body = body if isinstance(body, (bytes, bytearray)) else body.encode()

    def get_raw_resp(self):
        header_string = ''
        for k,v in self.headers.items():
            header_string += f"{k}: {v}\r\n"
        return (f"{self.version} {self.status_code} {self.reason}\r\n" + header_string + "\r\n").encode() + self.body

class CachedResponse:
    def __init__(self, status_code, headers, body):
        self.version = 'HTTP/1.1'
        self.status_code = status_code
        self.reason = 'OK'
        self.headers = headers
        self.body = body if isinstance(body, (bytes, bytearray)) else body.encode()

    def get_raw_resp(self):
        header_string = ''
        for k,v in self.headers.items():
            header_string += f"{k}: {v}\r\n"
        return (f"{self.version} {self.status_code} {self.reason}\r\n" + header_string + "\r\n").encode() + self.body

class CashElement:
    def __init__(self):
        self.resps = {}
        self.spent = 0

    def set_resp(self, route, cached):
        self.resps[route] = cached

    def get_resp(self, route):
        return self.resps.get(route)
