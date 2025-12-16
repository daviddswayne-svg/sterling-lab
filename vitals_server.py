import http.server
import socketserver
import json
import subprocess
import os

PORT = 8999

def get_vitals():
    vitals = {
        "ollama_status": False,
        "ssh_connections": 0,
        "load_avg": [0, 0, 0]
    }
    
    # Check Ollama
    try:
        # Check if process is running
        result = subprocess.run(["pgrep", "ollama"], stdout=subprocess.PIPE)
        if result.returncode == 0:
            vitals["ollama_status"] = True
    except Exception:
        pass

    # Check SSH Connections
    try:
        # Netstat to count established ssh connections
        # "netstat -an | grep :22 | grep ESTABLISHED | wc -l" is a common way, 
        # but on mac standard port might be different or we want all sshd.
        # simpler: pgrep -c sshd (count of sshd processes) - 1 (listener) ?
        # Let's stick to netstat for actual established connections if possible, or lsof.
        # Using lsof -i :22 -sTCP:ESTABLISHED is cleaner but might require sudo for all users.
        # Let's just count 'sshd' processes for now as a proxy for active sessions (minus the listener).
        
        result = subprocess.run("netstat -an | grep .22 | grep ESTABLISHED | wc -l", shell=True, stdout=subprocess.PIPE)
        count = int(result.stdout.strip())
        vitals["ssh_connections"] = count
    except Exception:
        pass

    # Load Average
    try:
        vitals["load_avg"] = os.getloadavg()
    except Exception:
        pass
        
    return vitals

class VitalsHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/vitals':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            data = get_vitals()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence logging to keep confirmed output clean
        return

if __name__ == "__main__":
    Handler = VitalsHandler
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Serving vitals at port {PORT}")
        httpd.serve_forever()
