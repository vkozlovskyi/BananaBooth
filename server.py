#!/usr/bin/env python3
"""BananaBooth local server — Python 3 standard library only.

    python3 server.py            # then open http://localhost:8787
    python3 server.py --port 9000

Serves index.html and proxies the calls the browser can't make itself
(api.replicate.com doesn't allow cross-origin requests):

    /replicate/<path>   ->  https://api.replicate.com/<path>
    /fetch?url=<url>    ->  GET of a Replicate output file (replicate.delivery only)

The Replicate token travels in each request's Authorization header and is
passed straight through: it is never logged, stored, or written to disk.
The server listens on 127.0.0.1 only and rejects requests from other origins.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC = {"/": "index.html", "/index.html": "index.html"}
REPLICATE_API = "https://api.replicate.com/"
FETCH_HOSTS = ("replicate.delivery",)  # output files: replicate.delivery and its subdomains
FORWARD_REQUEST_HEADERS = ("Authorization", "Content-Type", "Accept", "Prefer", "Cancel-After")
FORWARD_RESPONSE_HEADERS = ("Content-Type", "Retry-After")
MAX_BODY = 110 * 1024 * 1024  # Replicate's Files API limit is 100 MB
API_TIMEOUT = 150             # seconds; "Prefer: wait" holds a request for up to 60 s
USER_AGENT = "BananaBooth-proxy/1.0"
PORT = 8787


def allowed_fetch_url(url):
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower()
    return (
        p.scheme == "https"
        and p.port in (None, 443)
        and any(host == h or host.endswith("." + h) for h in FETCH_HOSTS)
    )


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """API calls carry the token, so never follow redirects anywhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AllowedRedirect(urllib.request.HTTPRedirectHandler):
    """Output downloads may redirect, but only to another allowed host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_fetch_url(newurl):
            raise urllib.error.HTTPError(newurl, 403, "Redirect to a disallowed host", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


API_OPENER = urllib.request.build_opener(NoRedirect)
FETCH_OPENER = urllib.request.build_opener(AllowedRedirect)


class Handler(BaseHTTPRequestHandler):
    server_version = "BananaBooth/1.0"

    def do_GET(self):
        self.route("GET")

    def do_POST(self):
        self.route("POST")

    def do_DELETE(self):
        self.route("DELETE")

    # ---- routing -------------------------------------------------------
    def route(self, method):
        if not self.same_origin():
            return
        path, _, query = self.path.partition("?")
        if path.startswith("/replicate/"):
            return self.proxy_api(method, self.path[len("/replicate/"):])
        if path == "/fetch" and method == "GET":
            return self.proxy_fetch(query)
        if method == "GET" and path in STATIC:
            return self.serve_file(STATIC[path])
        if method == "GET" and path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        self.send_json(404, {"detail": "Not found"})

    def same_origin(self):
        """Only answer the BananaBooth page itself (blocks other sites and DNS rebinding)."""
        host = self.headers.get("Host", "")
        allowed = {f"localhost:{PORT}", f"127.0.0.1:{PORT}", f"[::1]:{PORT}"}
        origin = self.headers.get("Origin")
        if host not in allowed or (origin is not None and origin != f"http://{host}"):
            self.send_json(403, {"detail": "Forbidden: requests must come from the BananaBooth page on localhost."})
            return False
        return True

    # ---- handlers ------------------------------------------------------
    def serve_file(self, name):
        try:
            with open(os.path.join(ROOT, name), "rb") as f:
                data = f.read()
        except OSError:
            return self.send_json(404, {"detail": f"{name} not found next to server.py"})
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def proxy_api(self, method, rest):
        if not rest.startswith("v1/"):
            return self.send_json(404, {"detail": "Only /replicate/v1/* is proxied"})
        body = None
        if method == "POST":
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self.send_json(413, {"detail": "Request too large (Replicate files must be under 100 MB)"})
            body = self.rfile.read(length) if length else b""
        headers = {k: self.headers[k] for k in FORWARD_REQUEST_HEADERS if self.headers.get(k)}
        headers["User-Agent"] = USER_AGENT
        req = urllib.request.Request(REPLICATE_API + rest, data=body, method=method, headers=headers)
        self.forward(API_OPENER, req, API_TIMEOUT, "api.replicate.com")

    def proxy_fetch(self, query):
        url = urllib.parse.parse_qs(query).get("url", [""])[0]
        if not allowed_fetch_url(url):
            return self.send_json(400, {"detail": "Only https://replicate.delivery output URLs can be fetched."})
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        self.forward(FETCH_OPENER, req, 120, urllib.parse.urlsplit(url).hostname)

    def forward(self, opener, req, timeout, label):
        try:
            resp = opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            resp = e  # upstream error responses are relayed as-is
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", e)
            return self.send_json(502, {"detail": f"Proxy could not reach {label}: {reason}"})
        with resp:
            status = resp.code if isinstance(resp, urllib.error.HTTPError) else resp.status
            try:
                data = resp.read()
            except (TimeoutError, OSError) as e:
                return self.send_json(502, {"detail": f"Proxy lost the connection to {label}: {e}"})
            self.send_response(status)
            for k in FORWARD_RESPONSE_HEADERS:
                v = resp.headers.get(k) if resp.headers else None
                if v:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

    def send_json(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        # Request lines only (method + path) — headers, and so tokens, are never logged.
        sys.stderr.write("%s  %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    global PORT
    ap = argparse.ArgumentParser(description="Serve BananaBooth and proxy Replicate API calls.")
    ap.add_argument("--port", type=int, default=PORT)
    PORT = ap.parse_args().port
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    httpd.daemon_threads = True
    print(f"BananaBooth running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
