# Prompt Engine — Quickstart

Compile structured scene facts into rich natural language prompts for AI image generators.

## Installation

```bash
pip install prompt-engine
```

Or run from source:

```bash
git clone <repo>
cd prompt-engine
pip install -e .
```

## Usage

### 1. CLI — Single file

Create a `scene.json`:

```json
{
  "camera": { "framing": "full_body" },
  "objects": {
    "h1": {
      "type": "human",
      "subject": "urban_influencer"
    }
  }
}
```

Compile it:

```bash
python compile.py scene.json --profile cinematic
```

Output:

```
Full-body shot of a smiling woman with long wavy brown hair, wearing an oversized black cotton hoodie and baggy olive cargo pants
```

### 2. CLI — Shorthand input

```bash
python compile.py --simple "woman, smiling, holding coffee, in cafe"
```

This resolves to a full scene JSON and compiles it automatically.

### 3. API server

```bash
python -m api.main --port 8000
```

Then POST a scene JSON:

```bash
curl -X POST http://localhost:8000/compile \
  -H "Content-Type: application/json" \
  -d '{
    "camera": {"framing": "medium"},
    "objects": {
      "h1": {
        "type": "human",
        "gender": "woman",
        "Face": {"expression": "smiling"}
      }
    }
  }'
```

### 4. Python API

```python
from compiler import PromptCompiler

compiler = PromptCompiler()

scene = {
    "camera": {"framing": "full_body"},
    "objects": {
        "h1": {
            "type": "human",
            "gender": "woman",
            "Face": {"expression": "smiling"},
            "Hair": {"color": "brown", "length": "long", "style": "wavy"}
        }
    }
}

prompt = compiler.compile_scene(scene)
print(prompt)
```

## Examples

### Example 1: Simple person

```json
{
  "camera": { "framing": "close_up" },
  "objects": {
    "h1": {
      "type": "human",
      "gender": "woman",
      "Face": { "expression": "smiling" },
      "Hair": { "color": "auburn", "length": "shoulder-length", "style": "curly" }
    }
  }
}
```

### Example 2: Person with relationship (holding a coffee)

```json
{
  "camera": { "framing": "medium" },
  "render_profile": "cinematic",
  "objects": {
    "h1": {
      "type": "human",
      "gender": "man",
      "Face": { "expression": "thoughtful" }
    },
    "c1": {
      "type": "drink",
      "template_key": "CoffeeCup",
      "material": "ceramic",
      "color": "white"
    }
  },
  "relationships": [
    { "type": "holding", "actor": "h1", "object": "c1" }
  ]
}
```

### Example 3: Full complex scene (Tennis Player)

```json
{
  "camera": { "framing": "medium" },
  "render_profile": "cinematic",
  "style": "photorealistic",
  "objects": {
    "h1": {
      "type": "human",
      "gender": "woman",
      "Face": { "expression": "smiling gently" },
      "Hair": { "color": "dark", "style": "pulled back into a high ponytail" },
      "UpperBody": { "owned_item_id": "dress_1" },
      "Hands": { "owned_item_id": "racket_1" }
    },
    "dress_1": {
      "type": "clothing",
      "template_key": "Dress",
      "style": "one-shoulder pale yellow athletic dress"
    },
    "racket_1": {
      "type": "item",
      "template_key": "Racket",
      "color": "white and yellow",
      "style": "tennis"
    },
    "env_court": {
      "type": "environment",
      "template_key": "TennisCourt",
      "material": "clay",
      "lighting": "natural daylight"
    }
  },
  "relationships": [
    { "type": "holding", "actor": "h1", "object": "racket_1" }
  ]
}
```

## Render Profiles

| Profile          | Focus                              |
|------------------|------------------------------------|
| `character_sheet`| Full detail list (default)         |
| `cinematic`      | Scene description sentence         |
| `fashion`        | Clothing & environment focused     |
| `portrait`       | Identity & emotion only            |
