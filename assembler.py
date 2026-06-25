"""
prompt-engine/assembler.py
Clean Slate Assembler — Pure functions, prototypal inheritance, grammar catalog.
"""
import os
import json
import re
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Shared utility (ported from compiler.py)
# ---------------------------------------------------------------------------

def safe_format(template_str, context: dict) -> str:
    """Format a template string or slot descriptor, replacing missing keys with empty string
    and collapsing any resulting multi-spaces."""
    tone = context.get("_tone", "default")

    def resolve_tone_value(val):
        if isinstance(val, dict):
            if "singular" in val or "plural" in val:
                return val
            if any(k in val for k in ("default", "poetic", "vivid", "concise", "technical")):
                return val.get(tone) or val.get("default") or ""
        return val

    def adjust_articles(text: str) -> str:
        text = re.sub(r"\b([aA])\s+([aeiouAEIOU][a-zA-Z]*)", lambda m: m.group(1) + "n " + m.group(2), text)
        text = re.sub(r"\b([aA])n\s+([^aeiouAEIOU\s][a-zA-Z]*)", lambda m: m.group(1) + " " + m.group(2), text)
        return text

    STANDARD_RANKS = {
        "quantity": 1, "opinion": 2, "expression": 2, "fit": 3, "length": 3,
        "size": 3, "shape": 4, "style": 4, "species": 4, "age": 5, "color": 6,
        "origin": 7, "pattern": 8, "material": 8
    }

    template_str = resolve_tone_value(template_str)

    if isinstance(template_str, dict):
        head = template_str.get("head", "")
        head = resolve_tone_value(head)

        if isinstance(head, dict):
            agreement_role = head.get("agreement_with", "actor")
            is_plural = False
            if agreement_role == "self":
                is_plural = context.get("_plural_self", False)
            else:
                is_plural = context.get(f"_plural_{agreement_role}", False)
            head_val = head.get("plural" if is_plural else "singular", "")
            head = resolve_tone_value(head_val)
        else:
            if context.get("_plural_self", False) and "plural" in template_str:
                plural_cfg = template_str["plural"]
                if "irregular" in plural_cfg:
                    head = plural_cfg["irregular"]
                elif "suffix" in plural_cfg:
                    head = head + plural_cfg["suffix"]

        slots = template_str.get("slots", {})
        pre_modifiers = []
        post_modifiers = []

        for slot_name, slot_cfg in slots.items():
            val = context.get(slot_name)
            val = resolve_tone_value(val)
            val_str = str(val).strip() if val is not None else ""
            if not val_str:
                continue
            pos = slot_cfg.get("position", "pre")
            if pos == "pre":
                rank = slot_cfg.get("rank")
                if rank is None:
                    cat = slot_cfg.get("category")
                    rank = STANDARD_RANKS.get(cat) if cat else STANDARD_RANKS.get(slot_name, 50)
                pre_modifiers.append((rank, val_str))
            elif pos == "post":
                prep = slot_cfg.get("prep", "")
                if prep:
                    post_modifiers.append(f"{prep} {val_str}")
                else:
                    post_modifiers.append(val_str)

        pre_modifiers.sort(key=lambda x: x[0])
        pre_modifier_strings = [x[1] for x in pre_modifiers]
        parts = pre_modifier_strings + [head] + post_modifiers
        if "suffix" in template_str:
            suffix_val = resolve_tone_value(template_str["suffix"])
            if suffix_val:
                for k, v in context.items():
                    if k.startswith("_") and isinstance(v, str):
                        suffix_val = suffix_val.replace("{" + k + "}", v)
                parts.append(suffix_val)
        rendered = " ".join(parts)
        rendered = re.sub(r"\s+", " ", rendered).strip()
        return adjust_articles(rendered)

    placeholders = re.findall(r"\{([a-zA-Z0-9_]+)\}", str(template_str))
    kwargs = {}
    for p in placeholders:
        val = context.get(p)
        val = resolve_tone_value(val)
        kwargs[p] = str(val or "")

    rendered = str(template_str).format(**kwargs)
    rendered = re.sub(r"\s+", " ", rendered).strip()
    return adjust_articles(rendered)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def _load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Deep merge utility
# ---------------------------------------------------------------------------

def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict.
    Override values win. Non-dict values in override replace base entirely."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


# ---------------------------------------------------------------------------
# Pipeline Step 1: resolve_blueprint
# ---------------------------------------------------------------------------

def resolve_blueprint(
    obj: dict,
    subjects_db: dict,
    attires_db: dict,
    scene_objects: dict
) -> dict:
    """Resolve a scene object's blueprint by merging subject preset + attire bundle.

    Merge order: scene data > subject defaults > attire defaults.
    Returns a flat component map (zone -> data).
    """
    components = {k: v for k, v in obj.items() if k not in ("type", "id")}

    subject_name = components.get("subject")
    if subject_name and subject_name in subjects_db:
        preset = subjects_db[subject_name]
        for comp_key, comp_val in preset.items():
            if comp_key == "type":
                continue
            if comp_key in components:
                if isinstance(components[comp_key], dict) and isinstance(comp_val, dict):
                    merged = dict(comp_val)
                    merged.update(components[comp_key])
                    components[comp_key] = merged
            else:
                components[comp_key] = comp_val

    attire_name = components.get("attire")
    if attire_name and attire_name in attires_db:
        attire = attires_db[attire_name]
        for zone, slot_data in attire.items():
            if not isinstance(slot_data, dict):
                continue
            existing = components.get(zone, {})
            if not isinstance(existing, dict):
                existing = {}
            existing["owned_item_id"] = slot_data["owned_item_id"]
            components[zone] = existing

            item_id = slot_data["owned_item_id"]
            if item_id not in scene_objects:
                base_name = re.sub(r"_\d+$", "", item_id)
                template_key = "".join(w.capitalize() for w in base_name.split("_"))
                scene_objects[item_id] = {
                    "id": item_id,
                    "type": "clothing",
                    "template_key": template_key,
                }

    return components


# ---------------------------------------------------------------------------
# Pipeline Step 2: apply_delta
# ---------------------------------------------------------------------------

def apply_delta(components: dict, user_overrides: dict) -> dict:
    """Apply user overrides on top of resolved blueprint.
    Returns a NEW dict (no mutation of input).
    Dot-notation keys like "Face.expression" are supported."""
    result = json.loads(json.dumps(components))

    for key_path, value in user_overrides.items():
        parts = key_path.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    return result


# ---------------------------------------------------------------------------
# Pipeline Step 3: resolve_references
# ---------------------------------------------------------------------------

def resolve_references(components: dict, scene_objects: dict) -> dict:
    """Replace owned_item_id references with actual item data.
    Returns a NEW dict (no mutation of input)."""
    result = json.loads(json.dumps(components))

    for zone, zone_data in result.items():
        if not isinstance(zone_data, dict):
            continue
        item_id = zone_data.get("owned_item_id")
        if item_id and item_id in scene_objects:
            item = scene_objects[item_id]
            item_components = {k: v for k, v in item.items() if k not in ("type", "id")}
            resolved = dict(item_components)
            for k, v in zone_data.items():
                if k != "owned_item_id":
                    resolved[k] = v
            resolved["template_key"] = item.get("template_key", zone)
            result[zone] = resolved

    return result


# ---------------------------------------------------------------------------
# Pipeline Step 4: apply_relationships
# ---------------------------------------------------------------------------

def apply_relationships(
    relationships: list,
    scene_objects: dict,
    visible_zones: list,
    actions_db: dict,
    spatial_db: dict,
    templates_db: dict,
    environments_db: dict,
) -> list:
    """Process relationships and emit text fragments.
    Returns a list of fragment dicts."""
    if not relationships:
        return []

    fragments = []
    mentioned_ids = set()

    for rel in relationships:
        rel_type = rel.get("type")
        if not rel_type:
            continue

        definition = actions_db.get(rel_type) or spatial_db.get(rel_type)
        if not definition:
            continue

        actor_id = rel.get("actor") or rel.get("subject") or rel.get("subject1")
        object_id = rel.get("object") or rel.get("target") or rel.get("subject2") or rel.get("container")

        if not actor_id or not object_id:
            continue

        actor_obj = scene_objects.get(actor_id, {})
        object_obj = scene_objects.get(object_id, {})

        roles = definition.get("roles", {})
        valid = True
        for role_name, role_def in roles.items():
            allowed = role_def.get("allowed", [])
            role_id = rel.get(role_name)
            if role_id and role_id in scene_objects:
                role_obj = scene_objects[role_id]
                role_type = role_obj.get("type", "")
                if allowed and role_type not in allowed:
                    valid = False
                    break
        if not valid:
            continue

        required_zones = definition.get("required_zones", {})
        actor_zone = required_zones.get("actor")
        if actor_zone and actor_zone not in visible_zones:
            continue

        template = definition.get("template")
        clause = definition.get("clause", "")
        priority = definition.get("priority", 80)
        chain_order = definition.get("chain_order", 99)

        actor_phrase = _get_noun_phrase(actor_id, rel, scene_objects, mentioned_ids, templates_db)
        object_phrase = _get_noun_phrase(object_id, rel, scene_objects, mentioned_ids, templates_db)

        ctx = {
            "actor": actor_phrase,
            "object": object_phrase,
            "subject": actor_phrase,
            "target": object_phrase,
            "container": object_phrase,
        }

        if isinstance(template, dict):
            text = safe_format(template, ctx)
        else:
            text = safe_format(template, ctx) if template else ""

        if isinstance(clause, dict):
            clause_text = safe_format(clause, ctx)
        else:
            clause_text = safe_format(clause, ctx) if clause else ""

        mentioned_ids.add(actor_id)
        mentioned_ids.add(object_id)

        fragments.append({
            "zone": "relationship",
            "frag_type": "relationship",
            "tags": definition.get("tags", ["action"]),
            "priority": priority,
            "text": text,
            "clause_text": clause_text,
            "actor_id": actor_id,
            "chain_order": chain_order,
        })

    return fragments


def _get_noun_phrase(
    entity_id: str,
    rel: dict,
    scene_objects: dict,
    mentioned_ids: set,
    templates_db: dict,
) -> str:
    """Generate a noun phrase for an entity in a relationship."""
    obj = scene_objects.get(entity_id, {})
    obj_type = obj.get("type", "")

    if obj_type in ("human", "creature"):
        gender = obj.get("gender", "person")
        if gender == "woman":
            return "she" if entity_id in mentioned_ids else "a woman"
        elif gender == "man":
            return "he" if entity_id in mentioned_ids else "a man"
        else:
            return "they" if entity_id in mentioned_ids else "a person"

    template_key = obj.get("template_key")
    if template_key and template_key in templates_db:
        template = templates_db[template_key]
        article = "a" if obj_type != "clothing" else "a"
        rendered = safe_format(template, obj)
        if entity_id in mentioned_ids:
            return rendered
        return f"{article} {rendered}"

    return entity_id


# ---------------------------------------------------------------------------
# Pipeline Step 5: apply_environment
# ---------------------------------------------------------------------------

def apply_environment(
    scene_data: dict,
    scene_objects: dict,
    environments_db: dict,
    lighting_db: dict,
    weather_db: dict,
    composition_db: dict,
    templates_db: dict,
) -> list:
    """Process environment and emit text fragments.
    Returns a list of fragment dicts."""
    fragments = []

    env_data = scene_data.get("environment")
    if env_data:
        env_type = env_data.get("type") or env_data.get("template_key")
        if env_type and env_type in environments_db:
            env_def = environments_db[env_type]
            template = env_def.get("template", "")
            lighting_key = env_data.get("lighting") or env_def.get("default_lighting", "")
            weather_key = env_data.get("weather") or env_def.get("default_weather", "")

            lighting_str = ""
            if lighting_key and lighting_key in lighting_db:
                lighting_str = lighting_db[lighting_key].get("template", "")

            weather_str = ""
            if weather_key and weather_key in weather_db:
                weather_str = weather_db[weather_key].get("template", "")

            ctx = {
                "type": env_type,
                "lighting": lighting_str,
                "weather": weather_str,
                "location": env_data.get("location", ""),
                "geolocation": env_data.get("geolocation", ""),
            }
            env_text = safe_format(template, ctx)

            fragments.append({
                "zone": "environment",
                "frag_type": "environment",
                "tags": ["environment"],
                "priority": 65,
                "text": env_text,
            })

            if lighting_str:
                fragments.append({
                    "zone": "lighting",
                    "frag_type": "lighting",
                    "tags": ["lighting"],
                    "priority": 55,
                    "text": lighting_str,
                })

            if weather_str:
                fragments.append({
                    "zone": "weather",
                    "frag_type": "weather",
                    "tags": ["weather"],
                    "priority": 50,
                    "text": weather_str,
                })

    comp_data = scene_data.get("composition")
    if comp_data:
        comp_type = comp_data.get("type")
        if comp_type and comp_type in composition_db:
            comp_text = composition_db[comp_type].get("template", comp_type)
            fragments.append({
                "zone": "composition",
                "frag_type": "composition",
                "tags": ["composition"],
                "priority": 88,
                "text": comp_text,
            })

    return fragments


# ---------------------------------------------------------------------------
# Pipeline Step 6: apply_style_tone
# ---------------------------------------------------------------------------

def apply_style_tone(scene_data: dict, styles_db: dict) -> list:
    """Process style overlay and emit a fragment.
    Returns a list with a single fragment (or empty)."""
    style_name = scene_data.get("style")
    if not style_name:
        return []

    style_def = styles_db.get(style_name, {})
    text = style_def.get("template", style_name)

    return [{
        "zone": "style",
        "frag_type": "style",
        "tags": ["style"],
        "priority": 90,
        "text": text,
    }]


# ---------------------------------------------------------------------------
# Pipeline Step 7: filter_by_camera
# ---------------------------------------------------------------------------

def filter_by_camera(
    components: dict,
    camera_framing: str,
    pose_name: str = None,
    poses_db: dict = None,
) -> dict:
    """Filter components based on camera profile and pose occlusion.
    Returns a filtered component map."""
    profiles_path = os.path.join(DATA_DIR, "camera_profiles.json")
    with open(profiles_path, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    included = set(profiles.get(camera_framing, []))

    if pose_name and poses_db:
        pose_def = poses_db.get(pose_name, {})
        hidden = set(pose_def.get("hidden_zones", []))
        included = included - hidden

    result = {}
    for zone, data in components.items():
        if zone in included:
            result[zone] = data

    return result


# ---------------------------------------------------------------------------
# Pipeline Step 8: render_to_text
# ---------------------------------------------------------------------------

def render_to_text(
    visible_components: dict,
    render_profile: str,
    templates_db: dict,
    attribute_metadata_db: dict,
    render_profiles_db: dict,
    active_tone: str = "default",
) -> list:
    """Render visible components into text fragments.
    Returns a list of fragment dicts."""
    fragments = []

    for zone, zone_data in visible_components.items():
        if not isinstance(zone_data, dict):
            continue
        if zone in ("gender", "subject", "attire", "morphology"):
            continue

        priority = attribute_metadata_db.get(zone.lower(), {}).get("priority", 50)
        tags = attribute_metadata_db.get(zone.lower(), {}).get("tags", ["identity"])

        template = templates_db.get(zone)
        if template:
            ctx = dict(zone_data)
            ctx["_tone"] = active_tone
            text = safe_format(template, ctx)
        else:
            text = _render_generic_zone(zone, zone_data)

        if text.strip():
            fragments.append({
                "zone": zone,
                "frag_type": "native",
                "tags": tags,
                "priority": priority,
                "text": text,
            })

    return fragments


def _render_generic_zone(zone: str, zone_data: dict) -> str:
    """Render a zone without a template as key-value pairs."""
    skip_keys = {"visibility_tags", "render_priority", "render_group", "metadata_key", "renderer"}
    parts = []
    for key, val in zone_data.items():
        if key in skip_keys:
            continue
        if isinstance(val, dict):
            for sub_key, sub_val in val.items():
                parts.append(f"{sub_val} {sub_key}")
        else:
            if zone.lower() in key.lower():
                parts.append(str(val))
            else:
                parts.append(f"{val} {key.lower()}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Assembler core
# ---------------------------------------------------------------------------

class Assembler:
    """Clean Slate Assembler — pipeline of pure functions."""

    def __init__(self):
        self.subjects_db = _load_json("subjects.json")
        self.attires_db = _load_json("attires.json")
        self.templates_db = _load_json("templates.json")
        self.attribute_metadata_db = _load_json("attribute_metadata.json")
        self.render_profiles_db = _load_json("render_profiles.json")
        self.actions_db = _load_json("actions.json")
        self.spatial_db = _load_json("spatial_relationships.json")
        self.environments_db = _load_json("environments.json")
        self.lighting_db = _load_json("lighting.json")
        self.weather_db = _load_json("weather.json")
        self.composition_db = _load_json("composition.json")
        self.styles_db = _load_json("styles.json")
        self.poses_db = _load_json("poses.json")

    def assemble(self, scene_data: dict) -> str:
        """Assemble a scene into a prompt string."""
        camera = scene_data.get("camera", {})
        camera_framing = camera.get("framing", "full_body")
        pose_name = scene_data.get("pose")
        render_profile_name = scene_data.get("render_profile", "character_sheet")
        active_tone = scene_data.get("tone", "default")

        render_profile = self.render_profiles_db.get(render_profile_name, {
            "include_tags": ["identity", "emotion", "clothing", "action", "style"],
            "max_fragments": 10,
        })

        scene_objects = {}
        for obj_id, obj_data in scene_data.get("objects", {}).items():
            scene_objects[obj_id] = {**obj_data, "id": obj_id}

        physical_ids = []
        for obj_id, obj in scene_objects.items():
            if _is_physical(obj):
                physical_ids.append(obj_id)

        if not physical_ids:
            return ""

        all_fragments = []

        for obj_id in physical_ids:
            obj = scene_objects[obj_id]

            components = resolve_blueprint(obj, self.subjects_db, self.attires_db, scene_objects)

            user_overrides = {k: v for k, v in obj.items()
                              if k not in ("type", "id", "subject", "attire") and isinstance(v, dict)}
            components = apply_delta(components, user_overrides)

            components = resolve_references(components, scene_objects)

            visible = filter_by_camera(components, camera_framing, pose_name, self.poses_db)

            identity_frags = render_to_text(
                visible, render_profile_name,
                self.templates_db, self.attribute_metadata_db,
                self.render_profiles_db, active_tone
            )
            for f in identity_frags:
                f["actor_id"] = obj_id
            all_fragments.extend(identity_frags)

            body_config_data = scene_data.get("body_config", {}).get(obj_id)
            if body_config_data:
                all_fragments.extend(_render_body_config(body_config_data, obj_id))

        relationships = scene_data.get("relationships", [])
        rel_frags = apply_relationships(
            relationships, scene_objects, [],
            self.actions_db, self.spatial_db, self.templates_db, self.environments_db
        )
        all_fragments.extend(rel_frags)

        env_frags = apply_environment(
            scene_data, scene_objects,
            self.environments_db, self.lighting_db,
            self.weather_db, self.composition_db, self.templates_db
        )
        all_fragments.extend(env_frags)

        style_frags = apply_style_tone(scene_data, self.styles_db)
        all_fragments.extend(style_frags)

        include_tags = set(render_profile.get("include_tags", []))
        max_frags = render_profile.get("max_fragments", 10)

        filtered = [f for f in all_fragments if any(t in include_tags for t in f.get("tags", []))]
        filtered.sort(key=lambda f: -f.get("priority", 0))
        filtered = filtered[:max_frags]

        return _assemble_output(filtered, physical_ids, render_profile)


def _is_physical(obj: dict) -> bool:
    """Check if an object is a physical entity (human, creature, etc.)."""
    if obj.get("type") in ("human", "creature"):
        return True
    if obj.get("subject"):
        return True
    if obj.get("morphology"):
        return True
    return False


def _render_body_config(body_config: dict, obj_id: str) -> list:
    """Render body config into text fragments."""
    fragments = []
    parts = []

    head = body_config.get("head", {})
    if head.get("tilt"):
        parts.append(f"head tilted {head['tilt'].replace('_', ' ')}")
    if head.get("turn"):
        parts.append(f"head turned {head['turn'].replace('_', ' ')}")

    gaze = body_config.get("gaze", {})
    if gaze.get("direction"):
        direction = gaze["direction"].replace("_", " ")
        if gaze.get("target"):
            parts.append(f"gaze {direction} {gaze['target']}")
        else:
            parts.append(f"gaze {direction}")

    arms = body_config.get("arms", {})
    if arms.get("left"):
        parts.append(f"left arm {arms['left'].replace('_', ' ')}")
    if arms.get("right"):
        parts.append(f"right arm {arms['right'].replace('_', ' ')}")

    legs = body_config.get("legs", {})
    if legs.get("position"):
        parts.append(f"legs {legs['position'].replace('_', ' ')}")

    torso = body_config.get("torso", {})
    if torso.get("lean"):
        parts.append(f"torso leaning {torso['lean'].replace('_', ' ')}")

    if parts:
        fragments.append({
            "zone": "body_config",
            "frag_type": "body_config",
            "tags": ["body_config"],
            "priority": 60,
            "text": ", ".join(parts),
            "actor_id": obj_id,
        })

    return fragments


def _assemble_output(
    fragments: list,
    physical_ids: list,
    render_profile: dict,
) -> str:
    """Assemble fragments into a natural language prompt string."""
    if not fragments:
        return ""

    identity_frags = []
    clothing_frags = []
    relationship_frags = []
    env_frags = []
    atmospheric_frags = []
    pose_frags = []
    body_config_frags = []

    for f in fragments:
        zone = f.get("zone", "")
        frag_type = f.get("frag_type", "")
        if frag_type == "relationship":
            relationship_frags.append(f)
        elif frag_type in ("environment", "lighting", "weather"):
            env_frags.append(f)
        elif frag_type == "style":
            atmospheric_frags.append(f)
        elif frag_type == "pose":
            pose_frags.append(f)
        elif frag_type == "body_config":
            body_config_frags.append(f)
        elif zone in ("Face", "Hair", "Eyes", "Headwear", "Tusks", "Ears", "Jaw"):
            identity_frags.append(f)
        elif zone in ("UpperBody", "LowerBody", "Feet", "Hands"):
            clothing_frags.append(f)
        else:
            atmospheric_frags.append(f)

    parts = []

    for frag in identity_frags:
        parts.append(frag["text"])

    if clothing_frags:
        clothing_texts = [f["text"] for f in clothing_frags]
        if len(clothing_texts) == 1:
            parts.append(f"wearing {clothing_texts[0]}")
        else:
            joined = ", ".join(clothing_texts[:-1])
            parts.append(f"wearing {joined} and {clothing_texts[-1]}")

    if body_config_frags:
        for f in body_config_frags:
            parts.append(f["text"])

    if relationship_frags:
        for f in relationship_frags:
            parts.append(f["text"])

    if env_frags:
        env_text = env_frags[0]["text"] if env_frags else ""
        if env_text:
            parts.append(f"in {env_text}" if not env_text.startswith("in ") else env_text)

    if atmospheric_frags:
        for f in atmospheric_frags:
            parts.append(f["text"])

    if not parts:
        return ""

    result = ", ".join(parts)
    result = re.sub(r"\s+", " ", result).strip()

    if result:
        result = result[0].upper() + result[1:]

    return result
