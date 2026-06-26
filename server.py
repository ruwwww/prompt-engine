import argparse
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from compiler import PromptCompiler

PORT = 8000
compiler = PromptCompiler()

def parse_labeled_prompt(labeled_str: str) -> dict:
    fields = {
        "subject": "",
        "clothing": "",
        "action": "",
        "environment": "",
        "lighting": "",
        "camera": "",
        "style": "",
        "composition": ""
    }
    lines = [line.strip() for line in labeled_str.split("\n")]
    for line in lines:
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            val = parts[1].strip()
            if key == "subject":
                fields["subject"] = val
            elif key == "clothing":
                fields["clothing"] = val
            elif key == "action":
                fields["action"] = val
            elif key == "environment":
                fields["environment"] = val
            elif key == "lighting":
                fields["lighting"] = val
            elif key == "camera":
                fields["camera"] = val
            elif key in ("style details", "style"):
                fields["style"] = val
            elif key in ("objects", "composition"):
                fields["composition"] = val
    return fields

class DemoRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        BaseHTTPRequestHandler.end_headers(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

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
                
                # Make deep copies of scene_data for multiple compilations
                scene_data_legacy = json.loads(json.dumps(scene_data))
                scene_data_labeled = json.loads(json.dumps(scene_data))
                
                legacy_prompt = compiler.compile_scene(scene_data_legacy, strict=False, output_format="legacy")
                labeled_prompt = compiler.compile_scene(scene_data_labeled, strict=False, output_format="labeled")
                eight_field = parse_labeled_prompt(labeled_prompt)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                res = json.dumps({
                    "prompt": legacy_prompt,
                    "eightFieldPrompt": eight_field
                })
                self.wfile.write(res.encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                
                res = json.dumps({"error": str(e)})
                self.wfile.write(res.encode("utf-8"))
        elif self.path == "/resolve":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                scene_data = json.loads(post_data.decode("utf-8"))
                resolved = compiler.resolve_scene(scene_data, strict=False)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                res = json.dumps({"resolved": resolved}, default=str)
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
