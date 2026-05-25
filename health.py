# health.py
# Lightweight health check server that runs alongside Streamlit.
# Railway and monitoring tools can ping /health to verify the service is up.

import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/health":
            payload = json.dumps({
                "status": "ok",
                "service": "docagent",
                "timestamp": datetime.utcnow().isoformat(),
                "anthropic_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()
        
    def log_message(self, format, *args):
        pass

def start_health_server(port: int=8502):
    """
    Start the health check server in a background daemon thread.
    Daemon=True means it shuts down automatically when the main process exits.
    """
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()