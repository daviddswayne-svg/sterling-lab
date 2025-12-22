import os
import sys
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Robust Range-Handling Server for Video Streaming
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class RangeDataHandler(BaseHTTPRequestHandler):
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
        file_size = os.path.getsize(path)
        mime_type = "video/mp4" if path.endswith(".mp4") else "application/octet-stream"
        
        # Handle Range Header
        range_header = self.headers.get("Range")
        
        if range_header:
            # Parse Range: bytes=0-1234
            range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                
                # Cap the end
                if end >= file_size:
                    end = file_size - 1
                
                length = end - start + 1
                
                self.send_response(206)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                
                # Send the chunk
                try:
                    with open(path, 'rb') as f:
                        f.seek(start)
                        bytes_to_send = length
                        # Increased chunk size to 1MB for better tunnel throughput
                        chunk_size = 1024 * 1024 
                        
                        while bytes_to_send > 0:
                            read_len = min(chunk_size, bytes_to_send)
                            data = f.read(read_len)
                            if not data:
                                break
                            self.wfile.write(data)
                            bytes_to_send -= len(data)
                except BrokenPipeError:
                    pass # Client disconnected, normal for video seeking
                return

        # Fallback: Serve whole file (Status 200)
        self.send_response(200)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
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
    
    server = ThreadingHTTPServer(('0.0.0.0', port), RangeDataHandler)
    print(f"Starting Robust Range-Streaming Server on port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
