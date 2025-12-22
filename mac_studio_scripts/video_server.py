import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

# Use ThreadingMixIn to handle multiple requests (e.g. browser range requests) concurrently
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class VideoRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add headers to encourage streaming/caching
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

if __name__ == '__main__':
    port = 8888
    # Ensure we serve from the video directory
    os.chdir(os.path.expanduser("~/Movies/SiteVideos"))
    
    server = ThreadingHTTPServer(('0.0.0.0', port), VideoRequestHandler)
    print(f"Starting Threaded Video Server on port {port} serving {os.getcwd()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
