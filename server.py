import argparse
import json
import os
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from compiler import PromptCompiler

PORT = 8000
compiler = PromptCompiler()

class SafeHTTPServer(HTTPServer):
    def handle_error(self, request, client_address):
        import sys
        exc_type, exc_value, _ = sys.exc_info()
        if exc_type is not None and issubclass(exc_type, (ConnectionError, socket.error)):
            # Cleanly ignore client disconnection errors
            pass
        else:
            super().handle_error(request, client_address)

def parse_labeled_prompt(labeled_str: str) -> dict:
    fields = {
        "subject": "",
        "clothing": "",
        "action": "",
        "environment": "",
        "objects": "",
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
            elif key == "objects":
                fields["objects"] = val
            elif key == "lighting":
                fields["lighting"] = val
            elif key == "camera":
                fields["camera"] = val
            elif key in ("style details", "style"):
                fields["style"] = val
            elif key == "composition":
                fields["composition"] = val
    return fields

class DemoRequestHandler(BaseHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except (ConnectionError, socket.error):
            pass

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
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            res = json.dumps({"status": "active", "message": "Prompt Engine API Server is running. Access the studio frontend in the /fe directory."})
            self.wfile.write(res.encode("utf-8"))
        elif self.path == "/bootstrap":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                bootstrap_data = {
                    "subjects": compiler.subjects_db,
                    "environments": compiler.environments_db,
                    "poses": compiler.poses_db,
                    "attires": compiler.attires_db,
                    "actions": compiler.actions_db,
                    "spatial_relationships": compiler.spatial_db,
                }
                res = json.dumps(bootstrap_data, default=str)
                self.wfile.write(res.encode("utf-8"))
            except Exception as e:
                res = json.dumps({"error": str(e)})
                self.wfile.write(res.encode("utf-8"))
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
                
                legacy_prompt = compiler.compile_scene(scene_data_legacy, strict=False)
                labeled_prompt = compiler.compile_scene(scene_data_labeled, strict=False)
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
        elif self.path == "/validate":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)

            try:
                from schemas.scene import SceneInput
                from pydantic import ValidationError

                scene_data = json.loads(post_data.decode("utf-8"))
                try:
                    SceneInput.model_validate(scene_data)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    res = json.dumps({
                        "valid": True,
                        "errors": [],
                        "message": "✅ Scene JSON is valid."
                    })
                    self.wfile.write(res.encode("utf-8"))
                except ValidationError as e:
                    errors = []
                    for error in e.errors():
                        field_path = ".".join(str(loc) for loc in error["loc"])
                        errors.append({
                            "field": field_path,
                            "msg": error["msg"],
                            "value": error.get("input", None)
                        })
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    res = json.dumps({
                        "valid": False,
                        "errors": errors,
                        "message": f"❌ Validation failed: {len(errors)} error(s) found."
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
    httpd = SafeHTTPServer(server_address, DemoRequestHandler)
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
