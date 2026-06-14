import os, json
from http.server import HTTPServer, BaseHTTPRequestHandler

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "path": self.path}).encode())
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"HTTP Server on port {port}", flush=True)
    HTTPServer(("0.0.0.0", port), H).serve_forever()
