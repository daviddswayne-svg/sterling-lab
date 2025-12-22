import os
import sys
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

# Performance Revert: Use Python's native optimized SimpleHTTPRequestHandler
# This delegates file serving to lower-level OS calls (sendfile) where possible
# and handles Range requests automatically and efficiently.

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True  # Ensure threads exit when main process does

class CachingVideoHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add critical headers for caching and cross-origin
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=3600")
        # SimpleHTTPRequestHandler adds Last-Modified and Content-Length automatically
        super().end_headers()

if __name__ == '__main__':
    port = 8888
    # Video Dir
    os.chdir(os.path.expanduser("~/Movies/SiteVideos"))
    
    server = ThreadingHTTPServer(('0.0.0.0', port), CachingVideoHandler)
    
    # Keep TCP_NODELAY as it reduces latency over SSH tunnels
    server.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
    
    print(f"Starting FAST Native Threaded Server on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
