import argparse
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from compiler import PromptCompiler

PORT = 8000
compiler = PromptCompiler()

class DemoRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            try:
                with open(os.path.join(os.path.dirname(__file__), "index.html"), "rb") as f:
                    self.wfile.write(f.read())
            except Exception as e:
                self.wfile.write(f"Error loading index.html: {e}".encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/compile":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                scene_data = json.loads(post_data.decode("utf-8"))
                output_format = scene_data.pop("output_format", "labeled")
                compiled_prompt = compiler.compile_scene(scene_data, strict=False, output_format=output_format)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                res = json.dumps({"prompt": compiled_prompt})
                self.wfile.write(res.encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                res = json.dumps({"error": str(e)})
                self.wfile.write(res.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run():
    parser = argparse.ArgumentParser(description="Prompt Engine Demo Server")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to run on (default: {PORT})")
    args = parser.parse_args()
    port = args.port

    server_address = ("", port)
    httpd = HTTPServer(server_address, DemoRequestHandler)
    print(f"\n========================================================")
    print(f"  Prompt Engine Demo Server running at http://localhost:{port}")
    print(f"  Press Ctrl+C to terminate.")
    print(f"========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
