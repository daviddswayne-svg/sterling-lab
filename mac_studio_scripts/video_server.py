import os
import sys
import re
import socket
import time
from email.utils import formatdate
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# FINAL STRATEGY: 
# 1. Use ThreadingMixIn for concurrency (vital for multiple buffer requests).
# 2. Use Manual Range Handling (vital for 206 streaming over tunnel).
# 3. Use 256KB Chunks + TCP_NODELAY (vital for SSH latency).
# 4. Use Cache-Control (vital for preload/refresh).

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class RobustRangeVideoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Initial check for path
        path = self.path.split('?')[0]
        # Security: Prevent escaping directory
        if '..' in path or path.startswith('/'):
            path = '.' + path
        
        if not os.path.exists(path) or os.path.isdir(path):
            self.send_error(404, "File not found")
            return

        # Get file stats
        stats = os.stat(path)
        file_size = stats.st_size
        last_modified = formatdate(stats.st_mtime, usegmt=True)
        mime_type = "video/mp4" if path.endswith(".mp4") else "image/jpeg" if path.endswith(".jpg") else "application/octet-stream"
        
        # Handle Range Header (CRITICAL for streaming)
        range_header = self.headers.get("Range")
        
        if range_header:
            range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                
                if end >= file_size:
                    end = file_size - 1
                
                length = end - start + 1
                
                self.send_response(206) # Partial Content
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Last-Modified", last_modified)
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                
                try:
                    with open(path, 'rb') as f:
                        f.seek(start)
                        bytes_to_send = length
                        chunk_size = 256 * 1024 # 256KB for SSH Tunnel
                        
                        while bytes_to_send > 0:
                            read_len = min(chunk_size, bytes_to_send)
                            data = f.read(read_len)
                            if not data:
                                break
                            self.wfile.write(data)
                            bytes_to_send -= len(data)
                except BrokenPipeError:
                    pass
                return

        # Fallback: Serve whole file (Status 200) - Only for small files/images
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", last_modified)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        
        try:
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
        except BrokenPipeError:
            pass

if __name__ == '__main__':
    port = 8888
    # Video Dir
    os.chdir(os.path.expanduser("~/Movies/SiteVideos"))
    
    server = ThreadingHTTPServer(('0.0.0.0', port), RobustRangeVideoHandler)
    
    # TCP Opts
    server.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
    
    print(f"Starting Robust Threaded Video Server on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
