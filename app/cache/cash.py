import socketserver, socket, os, base64, pickle, redis, http.client

from cash_classes import HTTPReq, HTTPResp, CachedResponse, CashElement

REDIS_CLIENT = redis.Redis(host=os.environ['REDIS_HOST'], port=6379, encoding='utf-8', decode_responses=True)

MINIMUM_CASH = 10000000.0

def parseCash(stream_text:str):
    spent = 0
    body = ''
    while spent < MINIMUM_CASH:
        cur, _, stream_text = stream_text.partition('\r\n')
        if not cur:
            break
        try:
            amount_s, units = cur.split(' ',1)
            if units == 'DOLLARS':
                amount = float(amount_s)
            elif units == 'CENTS':
                amount = float(amount_s)/100.0
            else:
                raise Exception('I cannot understand the units!')
        except Exception:
            raise
        index = round(amount) if amount <= len(stream_text) else len(stream_text) - len(cur)
        cur2 = stream_text[:index]
        stream_text = stream_text[index:]
        if not (len(cur2) >= amount) or amount < 0:
            raise Exception('Are you trying to steal from me?')
        spent += amount
        body += cur2
    return body, stream_text, spent

def parseHTTPReq(data:bytes):
    # naive HTTP/1.1 request parser sufficient for this demo
    s = data.decode('latin-1')
    try:
        line, _, rest = s.partition('\r\n')
        method, route, version = line.split(' ')
        headers = {}
        while True:
            hline, _, rest = rest.partition('\r\n')
            if hline == '':
                break
            if ':' in hline:
                k,v = hline.split(':',1)
                headers[k.strip()] = v.strip()
        body = rest
        # cash encoding smuggling capability
        if 'Cash-Encoding' in headers and headers['Cash-Encoding'] == 'Money!':
            body, rest2, spent = parseCash(body)
        else:
            rest2 = ''
        headers['Content-Length'] = str(len(body.encode()))
        return [HTTPReq(method, route, version, headers, body)], rest2
    except Exception as e:
        return None, ''

def forward_to_js(req:HTTPReq):
    conn = http.client.HTTPConnection('127.0.0.1', 3000, timeout=5)
    headers = {k:v for k,v in req.headers.items() if k.lower() not in ('host','content-length')}
    headers['Host'] = 'backend'
    conn.request(req.method, req.route, body=req.body.encode() if isinstance(req.body, str) else req.body, headers=headers)
    resp = conn.getresponse()
    body = resp.read()
    hdrs = {k:v for (k,v) in resp.getheaders()}
    return CachedResponse(resp.status, hdrs, body)

class CashTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        raw = b''
        self.request.settimeout(2.0)
        try:
            chunk = self.request.recv(65535)
            raw += chunk
        except Exception:
            pass

        reqs, _ = parseHTTPReq(raw)
        if not reqs:
            self.request.send(HTTPResp(status_code=400, reason='Bad Request', headers={'Content-Type':'text/plain'}, body=b'bad request').get_raw_resp())
            return

        req = reqs[0]
        cookies = req.get_cookies()
        uid = cookies.get('uid')
        if uid and REDIS_CLIENT.exists(uid):
            try:
                cash_elem = pickle.loads(base64.b64decode(REDIS_CLIENT.get(uid)))
                cached = cash_elem.get_resp(req.route)
                if cached:
                    cached.headers['X-Cache-Hit'] = 'HIT!'
                    cached.headers['X-CashSpent'] = str(cash_elem.spent)
                    cached.headers['X-CachedRoutes'] = str(len(cash_elem.resps))
                    self.request.send(cached.get_raw_resp())
                    return
            except Exception:
                pass

        # otherwise forward
        resp = forward_to_js(req)

        # cache response if uid exists
        if uid:
            try:
                if REDIS_CLIENT.exists(uid):
                    cash_elem = pickle.loads(base64.b64decode(REDIS_CLIENT.get(uid)))
                else:
                    cash_elem = CashElement()
                cash_elem.set_resp(req.route, resp)
                REDIS_CLIENT.set(uid, base64.b64encode(pickle.dumps(cash_elem)))
                resp.headers['X-CachedRoutes'] = str(len(cash_elem.resps))
            except Exception:
                pass
        self.request.send(resp.get_raw_resp())

if __name__ == '__main__':
    HOST, PORT = '0.0.0.0', 9000
    with socketserver.TCPServer((HOST, PORT), CashTCPHandler) as server:
        server.serve_forever()
