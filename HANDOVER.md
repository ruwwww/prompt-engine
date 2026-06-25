# Prompt-Engine: AI Agent Handover Context

> **Created:** 2026-06-25  
> **Project:** `C:\Coding3\prompt-engine`  
> **Status:** Active development — 55 tests passing  
> **Current branch:** `master` (latest commit: `e7e280e`)

---

## 1. Project Purpose

This is a **Python ECS-style prompt composition engine** that translates structured scene descriptions into natural-language image generation prompts (for tools like Midjourney, DALL-E, Stable Diffusion, etc.).

The engine takes a JSON `scene` dict as input and outputs a single rendered prompt string, handling:
- Human subjects with clothing, face/hair attributes, accessories
- Relationships between subjects and objects
- Environment, lighting, weather, composition
- Camera framing filtration (what's visible at different shot sizes)
- Tone variants (default/poetic/vivid/concise/technical)
- Style overlays
- Predefined wardrobe bundles (Composition Approach)

---

## 2. Repository Layout

```
C:\Coding3\prompt-engine\
├── compiler.py         # Core engine — ALL systems live here
├── test_compiler.py    # Regression + integration tests (55 tests)
├── compile.py          # CLI entrypoint
├── main.py             # Script runner / examples
└── data/
    ├── actions.json            # Action templates (holding, sitting, etc.)
    ├── attires.json            # Wardrobe bundles (Composition Approach) ← NEW
    ├── attribute_metadata.json # Zone priority + tags
    ├── composition.json        # Composition types
    ├── environments.json       # Environment types
    ├── lighting.json           # Lighting presets
    ├── subjects.json           # Named human subject defaults
    ├── poses.json              # Pose → visible zone overrides
    ├── render_profiles.json    # Output profiles (portrait/cinematic/etc.)
    ├── spatial_relationships.json
    ├── styles.json             # Style overlay templates
    ├── templates.json          # Slot descriptor templates for all nouns
    └── weather.json
```

---

## 3. Architecture: Systems in `compiler.py`

All systems follow the same ECS pattern: they receive `SceneObject` instances, read components from them, and emit `CandidateFragment` objects that the `RenderSystem` sorts and assembles into the final prompt.

| System | Line | Responsibility |
|--------|------|----------------|
| `safe_format()` | 15 | Core template renderer — slot descriptors → text |
| `CandidateFragment` | 140 | Output unit: zone, type, tags, priority, text, actor_id |
| `SceneObject` | 157 | Scene entity wrapper — `components` dict holds all data |
| `WardrobeSystem` | 167 | **NEW** — resolves `attire` bundles onto human slots |
| `SubjectSystem` | 222 | Merges subject defaults into human objects |
| `VisibilitySystem` | 257 | Computes visible zones from camera framing + pose |
| `AttributeCollectorSystem` | 284 | Walks visible zones, emits clothing/attribute fragments |
| `RelationshipSystem` | 360 | Handles actor↔object interactions (holding, sitting on, etc.) |
| `EnvironmentSystem` | 535 | Emits environment + ambient prop + composition fragments |
| `ValidationSystem` | 636 | Pre-flight checks (unknown templates, missing actors, etc.) |
| `RenderSystem` | 708 | Sorts candidates by priority, filters by profile tags, assembles |
| `StyleSystem` | 908 | Appends style overlay text |
| `PromptCompiler` | 926 | **Orchestrator** — loads all data files, calls all systems |

---

## 4. Key Data Concepts

### SceneObject Components
Every object in `scene["objects"]` becomes a `SceneObject`. The `components` dict holds everything except `"type"` and `"id"`.

For a **human** object, key components are:
- `"gender"` — `"man"` | `"woman"` | `"person"`
- `"subject"` — named preset from `subjects.json`
- `"attire"` — **NEW** named bundle from `attires.json`
- `"Face"`, `"Hair"`, `"UpperBody"`, `"LowerBody"`, `"Feet"`, `"Hands"` — zone dicts
- Zone dict either has `owned_item_id` pointing to another object, or inline attributes

For a **clothing/item** object:
- `"type"`: `"clothing"` | `"item"` | `"prop"`
- `"template_key"`: key into `templates.json` (e.g. `"SuitJacket"`, `"Hoodie"`)
- Any slot values: `"color"`, `"style"`, `"material"`, `"pattern"`, etc.

### Camera Framing → Visible Zones
| Framing | Visible Zones |
|---------|--------------|
| `full_body` | Face, Hair, UpperBody, LowerBody, Feet, Hands |
| `medium` | Face, Hair, UpperBody, Hands |
| `close_up` | Face, Hair |

### Template Slot Descriptors (`templates.json`)
Templates are either:
- A plain string with `{placeholders}` — e.g. `"short {color} hair"`
- A slot descriptor dict with `"head"` noun + `"slots"` map (pre/post modifiers)

Example:
```json
"SuitJacket": {
  "head": "suit jacket",
  "slots": {
    "color": { "position": "pre" },
    "style": { "position": "pre" }
  }
}
```
A navy, tailored suit jacket → `"navy tailored suit jacket"`

### Attires (`data/attires.json`) — Composition Approach
Predefined wardrobe bundles that auto-assign clothing items to zones:
```json
{
  "business_suit": {
    "UpperBody": { "owned_item_id": "suit_jacket_1" },
    "LowerBody": { "owned_item_id": "suit_pants_1" },
    "Feet":      { "owned_item_id": "oxford_shoes_1" }
  }
}
```
- If the user defines `"suit_jacket_1"` in `scene["objects"]`, their overrides (color, style, etc.) are preserved
- If not, `WardrobeSystem` injects a default `SceneObject` with the correct `template_key`
- Camera framing then naturally filters which zones appear

---

## 5. Scene Input Structure (Reference)

```python
scene = {
    "camera": {"framing": "medium"},       # full_body | medium | close_up
    "tone": "default",                      # default | poetic | vivid | concise | technical
    "render_profile": "cinematic",          # portrait | fashion | cinematic | character_sheet
    "style": "cinematic_teal_orange",       # key in styles.json
    "pose": "sitting",                      # optional, overrides zone visibility
    "anchors": {"primary": "h1"},           # boosts priority of objects
    "placements": {"env_bg": "background"}, # reduces priority

    "objects": {
        "h1": {
            "type": "human",
            "gender": "woman",
            "attire": "business_suit",       # Composition Approach
            "subject": "urban_influencer",   # or use subject
            "Face": {"expression": "confident"},
            "Hair": {"color": "dark", "style": "long, wavy"},
            "UpperBody": {"owned_item_id": "dress_1"},
        },
        "dress_1": {
            "type": "clothing",
            "template_key": "Dress",
            "color": "green",
            "style": "sleeveless",
            "pattern": "white polka dots"
        },
        "env_1": {
            "type": "environment",
            "template_key": "TennisCourt",
            "location": "outdoor, reddish-brown clay"
        },
        "comp_1": {
            "type": "composition",
            "template_key": "cinematic"
        }
    },

    "relationships": [
        {"type": "holding", "actor": "h1", "object": "racket_1"}
    ]
}
```

---

## 6. Test Suite (`test_compiler.py`)

**55 tests across these classes:**

| Class | Coverage |
|-------|----------|
| `TestSafeFormat` | Template rendering, missing keys, spacing |
| `TestVisibility` | Camera framing zone filtering, pose overrides |
| `TestSubjects` | Subject merging, override priority |
| `TestAttributeCollector` | Zone walking, owned items, inline attrs |
| `TestRelationshipSystem` | Holding, sitting, spatial relationships |
| `TestEnvironmentSystem` | Env types, ambient props, composition |
| `TestValidationSystem` | Error/warning detection |
| `TestRenderSystem` | Tag filtering, priority sorting, profile modes |
| `TestToneVariants` | Tone-aware template rendering |
| `TestMultiCharacter` | Multiple human subjects, anchor priorities |
| `TestIntegration` (various) | Full scene end-to-end tests |
| `TestPatterns` | Pattern descriptors and prepositions |
| **`TestCompositionApproach`** | **NEW** — Attire bundles, overrides, camera filtering |

Run with: `pytest` from `C:\Coding3\prompt-engine\`

---

## 7. Pending Feature: Selfie/iPhone Descriptor Set

The user was exploring adding a new descriptor set just before context limit. The full descriptors:

> *"Shot on iPhone. Hyper-realistic snapshot. Young, slender girl taking a selfie. She is wearing the clothes from the second photo. Skin is slightly tanned. The girl has voluminous floral wreaths made of small wild daisies on her head. The wreaths must be lush, natural, fresh, like a summer flower crown. The flowers are arranged around her head, avoiding an artificial look. Her hair is very long, reaching her waist, styled in voluminous curls along the entire length, beautifully arranged in front over her shoulders; the very long hair is blowing in the wind, slightly falling onto her face. Background: a summer field like a hill with green grass, scattered with wild daisies, nothing else in the background. Open clear blue sky without clouds. Do not blur the background. Head is slightly tilted towards her shoulder. No hands in the frame. Straight horizon line, hair blowing strongly in the wind. Sunny weather during the golden hour, hyper-realism, 9:16 aspect ratio."*

### Analysis: What Needs Adding to the Engine

#### a) New Templates (`data/templates.json`)
```json
"FlowerCrown": {
  "head": "flower crown",
  "slots": {
    "style": { "position": "pre" },
    "flowers": { "position": "post", "prep": "made of" }
  }
},
"SummerField": {
  "head": "summer field",
  "slots": {
    "location": { "position": "post", "prep": "on" }
  }
}
```

#### b) New Zone: `Head` (for accessories like wreaths/crowns)
- Add `"Head"` to `VisibilitySystem.CAMERA_ZONES` for all framings
- Add `"Head"` priority entry in `attribute_metadata.json`
- Scene usage: `"Head": {"owned_item_id": "crown_1"}`

#### c) New `motion` slot on `Hair` template
Update `templates.json` Hair descriptor:
```json
"Hair": {
  ...
  "slots": {
    "color": ...,
    "length": ...,
    "style": ...,
    "motion": { "position": "post", "prep": "," }
  }
}
```
Allows: `"very long, voluminous curls, blowing strongly in the wind"`

#### d) New Style entries (`data/styles.json`)
```json
"iphone_hyperreal": {
  "template": "shot on iPhone, hyper-realistic snapshot, 9:16 aspect ratio"
},
"golden_hour_photorealistic": {
  "template": "sunny golden hour lighting, hyper-realism, photorealistic"
}
```

#### e) New Environment (`data/environments.json`)
```json
"summer_field": {
  "template": "a summer field on a hill covered with green grass and scattered wild daisies, open clear blue sky"
}
```

#### f) `aspect_ratio` and `render_hint` in scene/render output
- Add `"aspect_ratio"` as a top-level scene key
- Pass it through `RenderSystem.compose()` as a suffix to the final output string

#### g) `no_hands` camera directive
- Add `"no_hands"` flag to `scene["camera"]`
- `VisibilitySystem` should exclude `Hands` zone if `no_hands: true`

#### h) `head_tilt` pose descriptor
- Can be added as a `Face` component: `"Face": {"head_tilt": "slightly towards shoulder"}`
- Or as a new `"pose_detail"` slot in `camera` data

### Target Integration Test
```python
scene = {
    "camera": {"framing": "medium", "no_hands": True, "aspect_ratio": "9:16"},
    "tone": "default",
    "render_profile": "cinematic",
    "style": "iphone_hyperreal",
    "objects": {
        "h1": {
            "type": "human",
            "gender": "woman",
            "Face": {"expression": "selfie", "head_tilt": "slightly towards shoulder",
                     "skin": "slightly tanned"},
            "Hair": {"color": "dark", "length": "very long, reaching waist",
                     "style": "voluminous curls", "motion": "blowing strongly in the wind"},
            "Head": {"owned_item_id": "crown_1"},
            "UpperBody": {"owned_item_id": "dress_1"}
        },
        "crown_1": {
            "type": "accessory",
            "template_key": "FlowerCrown",
            "style": "voluminous, lush, natural",
            "flowers": "small wild daisies"
        },
        "env_1": {
            "type": "environment",
            "template_key": "SummerField",
            "location": "a hill with green grass, scattered with wild daisies"
        }
    }
}
```

---

## 8. Priority Task List for Next Agent

1. **Add `Head` zone** to `VisibilitySystem.CAMERA_ZONES`, `attribute_metadata.json`, and test it
2. **Add `motion` slot** to `Hair` template descriptor in `templates.json`
3. **Add `FlowerCrown` and `SummerField`** to `templates.json` and `environments.json`
4. **Add `iphone_hyperreal` and `golden_hour_photorealistic`** styles to `styles.json`
5. **Add `no_hands` camera directive** — `VisibilitySystem` removes `Hands` zone when set
6. **Add `aspect_ratio` pass-through** to `RenderSystem.compose()` output
7. **Write the integration test** for the selfie scene above
8. **Run `pytest`** — must stay green (55+) before committing

---

## 9. Design Principles to Maintain

- **ECS consistency**: New features = new System classes or new slots on existing systems. Never put logic directly in `compile_scene`.
- **Override priority**: User-defined values in `scene["objects"]` ALWAYS win over defaults (subject, attire, etc.)
- **Camera framing gates visibility**: Any new body zone MUST be added to `VisibilitySystem.CAMERA_ZONES`
- **Template-key coupling**: Every injected `SceneObject` must have a `template_key` that exists in `templates.json`
- **Zero regressions**: `pytest` must stay green before any commit
- **Data-driven**: Prefer adding to JSON data files over hardcoding strings in Python

---

## 10. Git State

```
branch:  master
latest:  e7e280e — "Implement WardrobeSystem for Composition Approach attire resolution and testing"

Files modified in that commit:
  compiler.py          (+WardrobeSystem class, +wardrobe_system integration in PromptCompiler)
  test_compiler.py     (+TestCompositionApproach: 3 new tests)
  data/templates.json  (+SuitJacket, SuitPants, OxfordShoes, PoloShirt, TennisSkirt, Sneakers)
  data/attires.json    (NEW FILE — business_suit, tennis_uniform bundles)
```
