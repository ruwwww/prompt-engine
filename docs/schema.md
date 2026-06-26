# Scene JSON Schema Reference

The Prompt Engine accepts a structured `scene.json` file that describes actors, their attributes, clothing, relationships, environment, and camera settings.

## Top-level Fields

| Field            | Type     | Required | Description |
|------------------|----------|----------|-------------|
| `camera`         | object   | no       | Camera framing and settings |
| `environment`    | object   | no       | Location, lighting, weather |
| `pose`           | string   | no       | Named pose (e.g., "standing", "sitting") |
| `render_profile` | string   | no       | Output style profile name |
| `style`          | string   | no       | Photographic style overlay |
| `composition`    | object   | no       | Composition type |
| `tone`           | string   | no       | Linguistic tone (default, vivid, concise) |
| `mood`           | string   | no       | Mood descriptor |
| `output_format`  | string   | no       | "legacy" (default) or "labeled" |
| `anchors`        | object   | no       | Map of role -> object ID for primary entities |
| `placements`     | object   | no       | Map of object ID -> placement label |
| `body_config`    | object   | no       | Per-actor body configuration overrides |
| `objects`        | object   | **yes**  | Scene objects keyed by ID |
| `relationships`  | array    | no       | Relationships between objects |

## Camera Object

```json
{
  "framing": "full_body",
  "shot_type": "close-up",
  "angle": "eye level",
  "depth_of_field": "shallow"
}
```

| Field           | Type   | Required | Values |
|-----------------|--------|----------|--------|
| `framing`       | string | no       | `full_body`, `medium`, `close_up` |
| `shot_type`     | string | no       | Any descriptive text |
| `angle`         | string | no       | Any descriptive text |
| `depth_of_field`| string | no       | Any descriptive text |

## Environment Object

```json
{
  "type": "cafe",
  "lighting": "warm",
  "weather": "clear",
  "geolocation": "Paris",
  "location": "the left bank"
}
```

| Field        | Type   | Required | Description |
|--------------|--------|----------|-------------|
| `type`       | string | **yes**  | Environment key (cafe, alley, beach, forest, etc.) |
| `lighting`   | string | no       | Lighting preset key |
| `weather`    | string | no       | Weather preset key |
| `geolocation`| string | no       | Geographic location |
| `location`   | string | no       | Free-text location description |

## Scene Objects

Each key in `objects` is a unique ID (e.g. `h1`, `hoodie_1`).

### Human / Creature Object

```json
{
  "h1": {
    "type": "human",
    "gender": "woman",
    "subject": "urban_influencer",
    "attire": "business_suit",
    "Face": {
      "expression": "smiling",
      "makeup": "soft"
    },
    "Hair": {
      "color": "brown",
      "length": "long",
      "style": "wavy"
    },
    "Eyes": {
      "color": "green"
    },
    "UpperBody": {
      "owned_item_id": "hoodie_1"
    },
    "LowerBody": {
      "owned_item_id": "pants_1"
    },
    "Feet": {
      "owned_item_id": "shoes_1"
    },
    "Hands": {
      "owned_item_id": "ring_1"
    },
    "Headwear": {
      "owned_item_id": "sunglasses_1"
    },
    "body_surface_features": [
      {
        "location": "UpperBody",
        "marking": "tattoo",
        "design": "a dragon on her forearm"
      }
    ]
  }
}
```

#### Zone Fields (Face, Hair, etc.)

Zone names use **PascalCase** keys (`Face`, `Hair`, `UpperBody`, etc.).

| Zone         | Description |
|--------------|-------------|
| `Face`       | Facial expression and makeup |
| `Hair`       | Hair color, length, style, texture, arrangement |
| `Eyes`       | Eye color and appearance |
| `Ears`       | Ear shape (e.g., "pointed" for elves) |
| `Tusks`      | Tusk size and material (for orcs) |
| `Jaw`        | Jaw shape |
| `UpperBody`  | Upper body clothing slot (`owned_item_id`) |
| `LowerBody`  | Lower body clothing slot (`owned_item_id`) |
| `Feet`       | Footwear slot (`owned_item_id`) |
| `Hands`      | Accessory/hand item slot (`owned_item_id`) |
| `Headwear`   | Headwear slot (`owned_item_id`) |

#### Clothing / Item / Fixture Object

```json
{
  "hoodie_1": {
    "type": "clothing",
    "template_key": "Hoodie",
    "color": "black",
    "fit": "oversized",
    "material": "cotton"
  }
}
```

Clothing items are referenced by `owned_item_id` from actor zone fields.

### Subject Presets

Built-in subject presets that provide default attributes:

| Preset              | Gender | Description |
|---------------------|--------|-------------|
| `urban_influencer`  | woman  | Smiling, brown wavy hair, hoodie + cargo pants |
| `professional_man`  | man    | Confident, dark neat hair, suit |
| `athletic_woman`    | woman  | Focused, black ponytail, polo + skirt |
| `cozy_creative`     | woman  | Thoughtful, auburn messy bun, linen top |
| `artistic_teens`    | person | Relaxed, auburn messy, hoodie |
| `orc_warrior`       | orc    | Snarling, tusks, chainmail |
| `elf_archer`        | elf    | Focused, silver braided hair, leather vest |

### Attire Bundles

Attire bundles override a subject's default clothing:

| Bundle            | Items |
|-------------------|-------|
| `business_suit`   | Suit jacket, suit pants, oxford shoes |
| `tennis_uniform`  | Polo shirt, tennis skirt, sneakers |
| `cozy_winter`     | Knit sweater, high-waist jeans, ankle boots, beanie |
| `wizard_attire`   | Wizard robe |
| `full_plate_armor`| Full plate armor ensemble |

## Relationships

```json
{
  "relationships": [
    {
      "type": "holding",
      "actor": "h1",
      "object": "c1"
    },
    {
      "type": "sitting",
      "actor": "h1",
      "target": "cafe.chair"
    }
  ]
}
```

| Field       | Type   | Required | Description |
|-------------|--------|----------|-------------|
| `type`      | string | **yes**  | Relationship type |
| `actor`     | string | varies   | Actor object ID |
| `subject`   | string | varies   | Alternative to actor |
| `object`    | string | varies   | Target object ID |
| `target`    | string | varies   | Alternative to object |
| `container` | string | varies   | Container object ID |
| `chain_order`| int   | no       | Order in chained relationships |

### Relationship Types

| Type               | Example |
|--------------------|---------|
| `holding`          | holding a coffee cup |
| `holding_drink`    | variant for drink objects |
| `holding_phone`    | variant for phone objects |
| `holding_near_eye` | holding near eye |
| `sitting`          | sitting on/in |
| `leaning_on`       | leaning against |
| `standing_next_to` | standing next to |
| `looking_at`       | looking at |
| `hugging`          | hugging |
| `rest_arms_on`     | resting arms on |
| `dangling_feet`    | dangling feet |
| `soaking_in`       | soaking in (bathtub) |
| `inside`           | inside (spatial) |

### Environment Anchors

Relationships can target environment fixtures using dot notation:

```json
{
  "relationships": [
    { "type": "leaning_on", "actor": "h1", "target": "balcony.railing" }
  ]
}
```

The engine resolves `balcony.railing` to the railing fixture defined in the balcony environment's affordances.

## Body Config

Per-actor body configuration overrides:

```json
{
  "body_config": {
    "h1": {
      "head": { "tilt": "slightly_left", "turn": "away_from_camera" },
      "gaze": { "direction": "down" },
      "arms": { "left": "crossed", "right": "crossed" },
      "legs": { "position": "standing" },
      "torso": { "lean": "forward" }
    }
  }
}
```

## Composition

```json
{
  "composition": {
    "type": "cinematic"
  }
}
```

Available types: `cinematic`, `rule_of_thirds`, `over_the_shoulder`, `symmetrical`, `dynamic`.
