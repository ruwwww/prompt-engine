# AGENTS.md — Prompt Engine

## Quick Reference

- **Tests**: `pytest` (129 tests, all in `test_compiler.py`)
- **CLI**: `python compile.py <scene.json> [--profile portrait|fashion|cinematic|character_sheet] [--strict]`
- **Demo**: `python main.py`
- **No CI, no lint, no typecheck** — pytest is the only verification gate

## Architecture

Everything lives in **`compiler.py`** (~1800 lines). There are no packages or modules — all systems are classes in one file.

**Data flow**: `PromptCompiler.compile_scene(scene)` → systems process `SceneObject` instances → emit `CandidateFragment` objects → `RenderSystem` sorts/filters/assembles into a single prompt string.

| System | Role |
|--------|------|
| `WardrobeSystem` | Resolves `attire` bundles (e.g. `"business_suit"`) onto human slots |
| `SubjectSystem` | Merges named subject presets (from `data/subjects.json`) into humans |
| `VisibilitySystem` | Computes visible body zones from `camera.framing` + `pose` |
| `AttributeCollectorSystem` | Walks visible zones, emits clothing/attribute fragments |
| `HairOntologySystem` | Normalizes and renders hair (supports old flat + new structured format) |
| `BodyConfigSystem` | Renders detailed pose: head tilt/turn, gaze, arms, legs, torso |
| `RelationshipSystem` | Handles actor↔object interactions (holding, sitting_on, etc.) |
| `EnvironmentSystem` | Emits environment + ambient props + composition fragments |
| `ValidationSystem` | Pre-flight checks (unknown templates, missing actors, etc.) |
| `RenderSystem` | Sorts by priority, filters by render profile tags, assembles output |
| `StyleSystem` | Appends style overlay text |

## Critical Rules

1. **Camera framing gates visibility** — any new body zone MUST be added to `VisibilitySystem.CAMERA_ZONES` dict (close_up / medium / full_body). If you forget, the zone is silently invisible.

2. **Override priority** — user values in `scene["objects"]` ALWAYS win over subject defaults and attire defaults. The merge order is: scene data > attire > subject defaults.

3. **Template-key coupling** — every `SceneObject` with `type: clothing|item|accessory|prop` needs a `template_key` that exists in `data/templates.json`. Missing keys silently produce empty text.

4. **Data-driven over hardcoded** — prefer adding to JSON files in `data/` over string literals in Python. Templates, environments, styles, poses, actions all live in `data/`.

5. **ECS consistency** — new features = new System classes or new slots on existing systems. Don't put business logic directly in `compile_scene`.

6. **`strict=True`** — calling `compile_scene(scene, strict=True)` raises `ValueError` on validation errors (instead of returning partial output).

## Data Files (`data/`)

14 JSON files. Key ones:

- `templates.json` — slot descriptors for all renderable nouns (clothing, items, environments, etc.)
- `subjects.json` — named human presets with default Face/Hair/clothing components
- `attires.json` — predefined wardrobe bundles (Composition Approach)
- `attribute_metadata.json` — zone priority + tags for render filtering
- `render_profiles.json` — which tags each profile includes (portrait excludes clothing, fashion excludes emotion, etc.)
- `poses.json` — pose definitions + `hidden_zones` for occlusion
- `environments.json` — environment types + `affordances` for anchor resolution
- `actions.json` — relationship type definitions (holding, sitting_on, etc.)
- `styles.json` — style overlay templates (editorial, cinematic_teal_orange, etc.)

## Scene Object Patterns

**Human**: `type: "human"`, optional `subject` (preset name), optional `attire` (bundle name), zone components (`Face`, `Hair`, `UpperBody`, `LowerBody`, `Feet`, `Hands`, `Headwear`, `Eyes`).

**Clothing/Item**: `type: "clothing|item|prop"`, required `template_key`, slot values (`color`, `style`, `material`, `pattern`, etc.).

**Environment**: `type: "environment"`, required `template_key`, optional `lighting`, `weather`, `location`, `geolocation`.

**Fixture**: `type: "fixture"` — auto-created by anchor resolution (e.g. `"balcony.railing"` creates a fixture SceneObject).

## Environment Anchors

Use dot notation in relationships to target parts of an environment:
```python
"relationships": [{"type": "leaning_on", "actor": "h1", "target": "balcony.railing"}]
```
This auto-creates a fixture `SceneObject` from the environment's affordances in `data/environments.json`.

## Hair Ontology

Hair accepts **two formats** (both work):
- **Old flat**: `{"color": "brown", "length": "long", "style": "wavy"}`
- **New structured**: `{"texture": {...}, "color": {...}, "arrangement": {...}, "appearance": {...}, "state": [...], "cultural": {...}}`

Both are normalized internally. Use whichever is simpler for the scene.

## BodyConfig

Fine-grained pose control via `scene["body_config"][object_id]`:
```python
"body_config": {
    "h1": {
        "head": {"tilt": "slightly_left", "turn": "away_from_camera"},
        "gaze": {"direction": "toward_target", "target": "phone"},
        "arms": {"left": "crossed", "right": "crossed"},
        "legs": {"position": "bent"},
        "torso": {"lean": "forward"}
    }
}
```
BodyConfig overrides scene-level `pose`. Also affects visibility (e.g. `arms: behind_back` hides `Hands` zone).

## Gotchas

- `HANDOVER.md` contains useful context but the test count is **stale** (says 55, actual is 129). Always verify with `pytest`.
- `HairOntologySystem` has duplicate method definitions (lines ~819-827) — dead code, ignore it.
- `safe_format` handles article adjustment (a→an before vowels) automatically.
- Render profiles control which fragment **tags** appear. Check `data/render_profiles.json` before assuming what's visible.
- The `body_surface_features` component (tattoos, scars, etc.) is suppressed when clothing covers that zone — check `attribute_metadata.json` for `covers_body_surface` flag.
