"""
api/main.py — FastAPI application for the Prompt Engine.

Endpoints:
  POST /compile   — Accepts scene.json, returns the final prompt string.
  POST /resolve   — Accepts scene.json, returns the fully resolved component
                    map (deep-merged state) for debugging.
  GET  /health    — Returns {"status": "ok", "templates_loaded": 57}.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError

# Ensure the project root is on sys.path so we can import compiler
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from compiler import PromptCompiler
from schemas.scene import SceneInput

app = FastAPI(
    title="Prompt Engine API",
    description="Compile structured scene facts into natural language prompts.",
    version="1.0.0",
)

# CORS — allow all origins for demo purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global compiler instance (lazy init)
_compiler: PromptCompiler | None = None


def get_compiler() -> PromptCompiler:
    global _compiler
    if _compiler is None:
        _compiler = PromptCompiler()
    return _compiler


def count_templates() -> int:
    """Count the number of Jinja2 template files available."""
    template_dir = _project_root / "data" / "grammar" / "templates"
    if not template_dir.exists():
        return 0
    return len(list(template_dir.rglob("*.jinja2")))


# ---------------------------------------------------------------------------
# Static file serving for the web demo
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
async def index():
    index_path = _project_root / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Prompt Engine</h1><p>index.html not found.</p>")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "templates_loaded": count_templates(),
    }


@app.post("/compile")
async def compile_scene(payload: Dict[str, Any]):
    """Compile a scene JSON into a natural language prompt.

    Returns the final prompt string.
    """
    compiler = get_compiler()

    # Validate input via Pydantic
    try:
        scene = SceneInput(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    scene_data = dict(payload)  # copy to avoid mutating caller's dict
    output_format = scene_data.get("output_format", "labeled")

    try:
        prompt = compiler.compile_scene(
            scene_data,
            strict=False,
            output_format=output_format,
        )
        return {"prompt": prompt}
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/resolve")
async def resolve_scene(payload: Dict[str, Any]):
    """Resolve a scene JSON and return the deep-merged component map.

    Useful for debugging and the web demo's resolved JSON preview.
    """
    compiler = get_compiler()

    # Validate input via Pydantic
    try:
        scene = SceneInput(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    try:
        resolved = compiler.resolve_scene(payload, strict=False)
        return {"resolved": resolved}
    except (ValueError, KeyError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run("api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    run()
