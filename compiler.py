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

        # Auto-create scene objects for subject preset owned_item_id references
        for zone, zone_data in components.items():
            if isinstance(zone_data, dict) and "owned_item_id" in zone_data:
                item_id = zone_data["owned_item_id"]
                if item_id not in scene_objects:
                    base_name = re.sub(r"_\d+$", "", item_id)
                    template_key = "".join(w.capitalize() for w in base_name.split("_"))
                    scene_objects[item_id] = {
                        "id": item_id,
                        "type": "clothing",
                        "template_key": template_key,
                    }
                else:
                    base_name = re.sub(r"_\d+$", "", item_id)
                    template_key = "".join(w.capitalize() for w in base_name.split("_"))
                    if "template_key" not in scene_objects[item_id]:
                        scene_objects[item_id]["template_key"] = template_key
                    if "type" not in scene_objects[item_id]:
                        scene_objects[item_id]["type"] = "clothing"

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
            else:
                base_name = re.sub(r"_\d+$", "", item_id)
                template_key = "".join(w.capitalize() for w in base_name.split("_"))
                if "template_key" not in scene_objects[item_id]:
                    scene_objects[item_id]["template_key"] = template_key
                if "type" not in scene_objects[item_id]:
                    scene_objects[item_id]["type"] = "clothing"

    return components


# ---------------------------------------------------------------------------
# Pipeline Step 2: apply_delta
# ---------------------------------------------------------------------------

def apply_delta(components: dict, user_overrides: dict) -> dict:
    """Apply user overrides on top of resolved blueprint.
    Returns a NEW dict (no mutation of input).
    Dot-notation keys like "Face.expression" are supported.
    Dict overrides are MERGED (not replaced) to preserve owned_item_id."""
    result = json.loads(json.dumps(components))

    for key_path, value in user_overrides.items():
        parts = key_path.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        # Merge dicts instead of replacing to preserve owned_item_id
        if isinstance(current.get(parts[-1]), dict) and isinstance(value, dict):
            current[parts[-1]].update(value)
        else:
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
        if item_id:
            if item_id in scene_objects:
                item = scene_objects[item_id]
                item_components = {k: v for k, v in item.items() if k not in ("type", "id")}
                resolved = dict(item_components)
                for k, v in zone_data.items():
                    if k != "owned_item_id" and k != "template_key":
                        resolved[k] = v
                if "template_key" not in resolved:
                    resolved["template_key"] = item.get("template_key", zone)
                result[zone] = resolved
            else:
                base_name = re.sub(r"_\d+$", "", item_id)
                template_key = "".join(w.capitalize() for w in base_name.split("_"))
                resolved = {k: v for k, v in zone_data.items() if k != "owned_item_id"}
                resolved["template_key"] = template_key
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
    placements: dict = None,
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

        # Variant resolution — check object type for variant matching
        object_obj_type = object_obj.get("type", "")
        for variant in definition.get("variants", []):
            when = variant.get("when", {})
            match = True
            for k, v in when.items():
                if k == "object_type":
                    if object_obj_type != v:
                        match = False
                        break
                elif k.endswith("_type"):
                    role_key = k[:-5]
                    role_id = rel.get(role_key)
                    role_obj = scene_objects.get(role_id, {})
                    if role_obj.get("type") != v:
                        match = False
                        break
            if match:
                template = variant.get("template", template)
                clause = variant.get("clause", clause)
                break

        actor_phrase = _get_noun_phrase(actor_id, rel, scene_objects, mentioned_ids, templates_db, placements)
        object_phrase = _get_noun_phrase(object_id, rel, scene_objects, mentioned_ids, templates_db, placements)

        # Build gender-aware possessive pronoun for suffix templates
        actor_gender = actor_obj.get("gender", "person")
        if actor_gender == "man":
            possessive = "his"
        elif actor_gender == "woman":
            possessive = "her"
        else:
            possessive = "their"

        ctx = {
            "actor": actor_phrase,
            "object": object_phrase,
            "subject": actor_phrase,
            "target": object_phrase,
            "container": object_phrase,
            "_possessive": possessive,
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
    placements: dict = None,
) -> str:
    """Generate a noun phrase for an entity in a relationship."""
    obj = scene_objects.get(entity_id, {})
    obj_type = obj.get("type", "")

    if obj_type in ("human", "creature"):
        gender = obj.get("gender", "person")
        if entity_id in mentioned_ids:
            if gender == "woman":
                return "she"
            elif gender == "man":
                return "he"
            else:
                return "they"
        else:
            if gender == "woman":
                return "a woman"
            elif gender == "man":
                return "a man"
            else:
                return "a person"

    if entity_id in mentioned_ids:
        # Reuse previously mentioned entity
        template_key = obj.get("template_key")
        if template_key and template_key in templates_db:
            return safe_format(templates_db[template_key], obj)
        parts = [obj.get("material", ""), obj.get("color", ""), obj_type]
        phrase = " ".join(p for p in parts if p).strip()
        return phrase if phrase else entity_id

    mentioned_ids.add(entity_id)

    template_key = obj.get("template_key")
    if template_key and template_key in templates_db:
        phrase = safe_format(templates_db[template_key], obj)
    else:
        # Fallback: material + color + type
        parts = [obj.get("material", ""), obj.get("color", ""), obj_type]
        phrase = " ".join(p for p in parts if p).strip()
        if not phrase:
            phrase = entity_id

    # Add article for non-plural
    if phrase and not phrase.startswith(("a ", "an ", "the ")):
        first_char = phrase[0].lower()
        article = "an" if first_char in "aeiou" else "a"
        phrase = f"{article} {phrase}"

    if placements and entity_id in placements:
        placement = placements[entity_id]
        phrase = f"{phrase} in {placement}"

    return phrase


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

    # Find environment data: first check scene_objects for env-type objects,
    # then fall back to scene_data["environment"]
    env_data = None
    for obj_id, obj in scene_objects.items():
        if obj.get("type") == "environment":
            env_data = obj
            break
    if env_data is None:
        env_data = scene_data.get("environment")

    if env_data:
        env_type = env_data.get("template_key") or env_data.get("location") or env_data.get("type")
        if env_type:
            db_key = env_type
            if db_key not in environments_db and db_key.lower() in environments_db:
                db_key = db_key.lower()
            env_def = environments_db.get(db_key, {})
            template = env_def.get("template", "")
            lighting_key = env_data.get("lighting") or env_def.get("default_lighting", "")
            weather_key = env_data.get("weather") or env_def.get("default_weather", "")

            lighting_str = ""
            if lighting_key:
                lighting_str = lighting_db[lighting_key].get("template", lighting_key) if lighting_key in lighting_db else lighting_key

            weather_str = ""
            if weather_key:
                weather_str = weather_db[weather_key].get("template", weather_key) if weather_key in weather_db else weather_key

            ctx = {
                "type": env_type,
                "lighting": lighting_str,
                "weather": weather_str,
                "location": env_data.get("location", ""),
                "geolocation": env_data.get("geolocation", ""),
            }
            env_text = safe_format(template, ctx)

            # ECS query: find ambient fixtures and furniture
            owned_item_ids = set()
            for o_id, o in scene_objects.items():
                if o.get("type") == "human":
                    for zone_name, zone_val in o.items():
                        if isinstance(zone_val, dict) and "owned_item_id" in zone_val:
                            owned_item_ids.add(zone_val["owned_item_id"])

            relationship_targets = set()
            for r in scene_data.get("relationships", []):
                t_id = r.get("object") or r.get("target") or r.get("subject2") or r.get("container")
                if t_id:
                    relationship_targets.add(t_id)

            ambient_fixtures = []
            for o_id, o in scene_objects.items():
                o_type = o.get("type")
                if o_type in ("fixture", "furniture") and o_id not in owned_item_ids and o_id not in relationship_targets:
                    tkey = o.get("template_key")
                    tpl = templates_db.get(tkey)
                    if tpl:
                        phrase = safe_format(tpl, o)
                    else:
                        parts = [o.get("material", ""), o.get("color", ""), o_type]
                        phrase = " ".join(p for p in parts if p).strip()
                    if phrase:
                        if not phrase.startswith(("a ", "an ", "the ")):
                            first_char = phrase[0].lower()
                            art = "an" if first_char in "aeiou" else "a"
                            phrase = f"{art} {phrase}"
                        ambient_fixtures.append(phrase)

            if ambient_fixtures:
                if len(ambient_fixtures) == 1:
                    fixtures_str = ambient_fixtures[0]
                elif len(ambient_fixtures) == 2:
                    fixtures_str = f"{ambient_fixtures[0]} and {ambient_fixtures[1]}"
                else:
                    fixtures_str = ", ".join(ambient_fixtures[:-1]) + f", and {ambient_fixtures[-1]}"
                env_text = f"{env_text} featuring {fixtures_str}"

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
        if zone not in included:
            continue
        if isinstance(data, dict):
            vis_tags = data.get("visibility_tags")
            if vis_tags and camera_framing not in vis_tags:
                continue
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

        metadata_key = zone_data.get("metadata_key")
        if not metadata_key:
            LEGACY_META_KEYS = {
                "Face": "expression",
                "Hair": "hair",
            }
            metadata_key = LEGACY_META_KEYS.get(zone, zone.lower())
        priority = attribute_metadata_db.get(metadata_key, {}).get("priority", 50)
        tags = attribute_metadata_db.get(metadata_key, {}).get("tags", ["identity"])

        template_key = zone_data.get("template_key", zone)
        template = templates_db.get(template_key) or templates_db.get(zone)

        if template:
            ctx = dict(zone_data)
            ctx["_tone"] = active_tone
            text = safe_format(template, ctx)
        elif zone_data.get("type") in ("clothing", "item", "prop"):
            # Skip clothing/items without templates (matches old compiler behavior)
            continue
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
    skip_keys = {"visibility_tags", "render_priority", "render_group", "metadata_key", "renderer", "template_key"}
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
# Validation
# ---------------------------------------------------------------------------

def validate(scene_data: dict, templates_db: dict, actions_db: dict,
             spatial_db: dict, subjects_db: dict, strict: bool = False) -> list:
    """Pre-flight checks. Returns list of {"severity": "error"|"warning", "message": str}.

    Checks:
      1. Unknown template keys (severity: error)
      2. Unknown relationship types (severity: error)
      3. Missing subject presets (severity: warning)
    """
    errors = []

    # 1. Unknown template keys
    for obj_id, obj_data in scene_data.get("objects", {}).items():
        template_key = obj_data.get("template_key")
        if template_key and template_key not in templates_db:
            # Check if zone name is a fallback
            zone = obj_data.get("zone")
            if zone and zone in templates_db:
                continue
            errors.append({
                "severity": "error",
                "message": f"Unknown template_key '{template_key}' for object '{obj_id}'",
            })

    # 2. Unknown relationship types
    for rel in scene_data.get("relationships", []):
        rel_type = rel.get("type", "")
        if rel_type not in actions_db and rel_type not in spatial_db:
            errors.append({
                "severity": "error",
                "message": f"Unknown relationship type '{rel_type}'",
            })

    # 3. Missing subject presets
    for obj_id, obj_data in scene_data.get("objects", {}).items():
        subject = obj_data.get("subject")
        if subject and subject not in subjects_db:
            errors.append({
                "severity": "warning",
                "message": f"Unknown subject preset '{subject}' for object '{obj_id}'",
            })

    if strict and any(e["severity"] == "error" for e in errors):
        raise ValueError("\n".join(e["message"] for e in errors if e["severity"] == "error"))

    return errors


# ---------------------------------------------------------------------------
# Assembler core
# ---------------------------------------------------------------------------

class Assembler:
    """Clean Slate Assembler — pipeline of pure functions."""

    def __init__(self, data_dir: str = None):
        global DATA_DIR
        if data_dir:
            DATA_DIR = data_dir
        else:
            DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
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

    def assemble(self, scene_data: dict, strict: bool = False) -> str:
        """Assemble a scene into a prompt string.

        Args:
            scene_data: The scene dictionary.
            strict: If True, raise ValueError on validation errors.
        """
        # Pre-flight validation
        validate(scene_data, self.templates_db, self.actions_db,
                 self.spatial_db, self.subjects_db, strict=strict)
        camera = scene_data.get("camera", {})
        camera_framing = camera.get("framing", "full_body")
        pose_name = scene_data.get("pose")
        render_profile_name = scene_data.get("render_profile", "character_sheet")
        active_tone = scene_data.get("tone", "default")

        render_profile = self.render_profiles_db.get(render_profile_name, {
            "include_tags": ["identity", "emotion", "clothing", "action", "style"],
            "max_fragments": 10,
        })
        include_tags = set(render_profile.get("include_tags", []))

        # Load camera profiles for relationship zone checks and BSF visibility
        camera_profiles_path = os.path.join(DATA_DIR, "camera_profiles.json")
        with open(camera_profiles_path, "r", encoding="utf-8") as f:
            camera_profiles = json.load(f)
        camera_framing_zones = set(camera_profiles.get(camera_framing, []))
        # Apply pose hidden zones to camera framing zones
        if pose_name and pose_name in self.poses_db:
            hidden = set(self.poses_db[pose_name].get("hidden_zones", []))
            camera_framing_zones = camera_framing_zones - hidden

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

            gender = components.get("gender", obj.get("gender", "person"))
            subject_name = components.get("subject", obj.get("subject", ""))
            morphology = components.get("morphology", obj.get("morphology", {}))

            identity_frags = render_to_text(
                visible, render_profile_name,
                self.templates_db, self.attribute_metadata_db,
                self.render_profiles_db, active_tone
            )
            for f in identity_frags:
                f["actor_id"] = obj_id
            all_fragments.extend(identity_frags)

            # Body surface features (tattoos, scars, freckles, etc.)
            bsf = components.get("body_surface_features") or []
            # Determine covered zones: check attribute_metadata for covers_body_surface flag
            covered_zones = set()
            for zone_name in visible:
                meta_key = zone_name.lower()
                meta = self.attribute_metadata_db.get(meta_key, {})
                if meta.get("covers_body_surface"):
                    covered_zones.add(zone_name)
            bs_meta = self.attribute_metadata_db.get("body_surface", {"tags": [], "priority": 50})
            for feature in bsf:
                loc = feature.get("location", "")
                # BSF visibility is gated by camera framing zones (after pose hidden zones applied)
                if loc not in camera_framing_zones:
                    continue
                if loc in covered_zones:
                    continue
                template = self.templates_db.get("BodySurface")
                if template:
                    text = safe_format(template, {**feature, "_tone": active_tone})
                    all_fragments.append({
                        "zone": loc,
                        "frag_type": "body_surface",
                        "tags": bs_meta.get("tags", []),
                        "priority": bs_meta.get("priority", 50),
                        "text": text,
                        "actor_id": obj_id,
                    })

            all_fragments.append({
                "zone": "_subject_type",
                "frag_type": "native",
                "tags": ["identity"],
                "priority": 100,
                "text": _get_subject_type(gender, morphology),
                "actor_id": obj_id,
            })

            # body_config: scene-level > subject preset body_config
            body_config_data = scene_data.get("body_config", {}).get(obj_id)
            if body_config_data is None:
                # Check subject preset for body_config
                body_config_data = components.get("body_config")
            if body_config_data:
                all_fragments.extend(_render_body_config(body_config_data, obj_id))
            elif pose_name and pose_name in self.poses_db:
                pose_def = self.poses_db[pose_name]
                pose_text = pose_def.get("pose_text", "")
                if pose_text:
                    all_fragments.append({
                        "zone": "_pose",
                        "frag_type": "pose",
                        "tags": ["pose"],
                        "priority": 70,
                        "text": pose_text,
                        "actor_id": obj_id,
                    })
                elif subject_name:
                    all_fragments.append({
                        "zone": "_default_gaze",
                        "frag_type": "body_config",
                        "tags": ["body_config"],
                        "priority": 55,
                        "text": "looking toward the camera",
                        "actor_id": obj_id,
                    })
            elif subject_name:
                all_fragments.append({
                    "zone": "_default_gaze",
                    "frag_type": "body_config",
                    "tags": ["body_config"],
                    "priority": 55,
                    "text": "looking toward the camera",
                    "actor_id": obj_id,
                })

        relationships = scene_data.get("relationships", [])
        # Compute visible zones for relationship actor checks using camera framing zones directly.
        # This ensures actors without components can still participate in relationships
        # (e.g., a bare {"type": "human", "gender": "woman"} can still hold an object).
        all_visible = list(camera_framing_zones)
        placements = scene_data.get("placements", {})
        rel_frags = apply_relationships(
            relationships, scene_objects, all_visible,
            self.actions_db, self.spatial_db, self.templates_db, self.environments_db,
            placements
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

        max_frags = render_profile.get("max_fragments", 10)

        filtered = [f for f in all_fragments if any(t in include_tags for t in f.get("tags", []))]
        filtered.sort(key=lambda f: (-f.get("priority", 0), f.get("zone", ""), f.get("text", "")))
        filtered = filtered[:max_frags]

        return _assemble_output(filtered, physical_ids, render_profile, include_tags)


def _is_physical(obj: dict) -> bool:
    """Check if an object is a physical entity (human, creature, etc.)."""
    if obj.get("type") in ("human", "creature"):
        return True
    if obj.get("subject"):
        return True
    if obj.get("morphology"):
        return True
    return False


def _get_subject_type(gender: str, morphology: dict) -> str:
    """Get the subject type string (e.g., 'orc', 'elf', 'woman', 'man')."""
    if morphology and morphology.get("type"):
        return morphology["type"]
    if gender in ("woman", "man", "person"):
        return gender
    if gender:
        return gender
    return "person"


def _render_body_config(body_config: dict, obj_id: str) -> list:
    """Render body config into text fragments."""
    fragments = []
    parts = []

    head = body_config.get("head", {})
    tilt = head.get("tilt", "")
    turn = head.get("turn", "")
    if tilt and tilt != "upright":
        tilt_words = {
            "forward": "tilted forward",
            "back": "tilted back",
            "left": "tilted to the left",
            "right": "tilted to the right",
            "slightly_left": "tilted slightly to the left",
            "slightly_right": "tilted slightly to the right",
        }
        parts.append(tilt_words.get(tilt, f"tilted {tilt.replace('_', ' ')}"))
    if turn and turn != "toward_camera":
        turn_words = {
            "away_from_camera": "turned away from the camera",
            "profile_left": "turned to the left",
            "profile_right": "turned to the right",
        }
        parts.append(turn_words.get(turn, f"turned {turn.replace('_', ' ')}"))

    gaze = body_config.get("gaze", {})
    direction = gaze.get("direction", "")
    target = gaze.get("target", "")
    if direction == "toward_target" and target:
        parts.append(f"looking at {target}")
    elif direction == "toward_camera":
        parts.append("looking toward the camera")
    elif direction:
        dir_words = {
            "up": "looking upward",
            "down": "looking downward",
            "left": "looking to the left",
            "right": "looking to the right",
            "away": "looking away",
        }
        parts.append(dir_words.get(direction, f"looking {direction.replace('_', ' ')}"))

    arms = body_config.get("arms", {})
    left = arms.get("left", "")
    right = arms.get("right", "")
    if left and right and left == right:
        # Symmetric case: "arms crossed" not "left arm crossed, right arm crossed"
        pos_words = {
            "crossed": "arms crossed",
            "raised": "arms raised",
            "extended": "arms extended",
            "behind_back": "hands clasped behind their back",
            "on_hips": "hands on hips",
        }
        parts.append(pos_words.get(left, f"arms {left.replace('_', ' ')}"))
    else:
        if left:
            parts.append(f"left arm {left.replace('_', ' ')}")
        if right:
            parts.append(f"right arm {right.replace('_', ' ')}")

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
    include_tags: set = None,
) -> str:
    """Assemble fragments into a natural language prompt string.

    Groups fragments by actor_id so multi-character scenes render each
    character separately, then joins them with commas.
    """
    if not fragments:
        return ""
    if include_tags is None:
        include_tags = set(render_profile.get("include_tags", []))

    # Group fragments by actor_id, preserving physical_ids ordering
    # Fragments without actor_id (env, style) go into a shared pool
    actor_frags: dict = {aid: [] for aid in physical_ids}
    shared_frags: list = []

    for f in fragments:
        if f.get("frag_type") == "relationship":
            continue
        aid = f.get("actor_id")
        if aid and aid in actor_frags:
            actor_frags[aid].append(f)
        else:
            shared_frags.append(f)

    # Separate env/style from relationships in shared_frags
    env_frags = [f for f in shared_frags if f.get("frag_type") in ("environment", "lighting", "weather")]
    style_frags_shared = [f for f in shared_frags if f.get("frag_type") == "style"]
    rel_frags_shared = [f for f in shared_frags if f.get("frag_type") == "relationship"]
    other_shared = [f for f in shared_frags
                    if f.get("frag_type") not in ("environment", "lighting", "weather", "style", "relationship")]

    def _render_actor(aid: str, frags: list) -> str:
        """Render a single actor's fragments into a natural language string."""
        identity_frags = []
        clothing_frags = []
        body_config_frags = []
        pose_frags = []
        rel_frags_actor = []
        surface_frags = []

        for f in frags:
            zone = f.get("zone", "")
            frag_type = f.get("frag_type", "")
            if frag_type == "relationship":
                rel_frags_actor.append(f)
            elif frag_type in ("body_config",):
                body_config_frags.append(f)
            elif frag_type == "pose":
                pose_frags.append(f)
            elif frag_type == "body_surface":
                surface_frags.append(f)
            elif zone in ("Face", "Hair", "Eyes", "Tusks", "Ears", "Jaw", "_subject_type"):
                identity_frags.append(f)
            elif zone in ("UpperBody", "LowerBody", "Feet", "Hands", "Headwear"):
                clothing_frags.append(f)
            else:
                identity_frags.append(f)

        identity_frags.sort(key=lambda f: -f.get("priority", 0))

        parts = []

        subject_type = ""
        # Only include face expression if "emotion" tag is in the include_tags
        face_expr = "" if "emotion" not in include_tags else ""
        face_expr_raw = ""
        hair_frag = None
        eyes_frag = None
        other_identity = []
        for frag in identity_frags:
            if frag.get("zone") == "_subject_type":
                subject_type = frag["text"]
            elif frag.get("zone") == "Face":
                face_expr_raw = frag["text"]
            elif frag.get("zone") == "Hair":
                hair_frag = frag
            elif frag.get("zone") == "Eyes":
                eyes_frag = frag
            else:
                other_identity.append(frag["text"])

        # Only show face expression if emotion tag is allowed by render profile
        face_expr = face_expr_raw if "emotion" in include_tags else ""

        if face_expr and subject_type:
            parts.append(f"{face_expr} {subject_type}")
        elif subject_type:
            parts.append(subject_type)
        elif face_expr:
            parts.append(face_expr)

        with_parts = []
        if hair_frag:
            with_parts.append(hair_frag["text"])
        if eyes_frag:
            with_parts.append(eyes_frag["text"])
        for text in other_identity:
            with_parts.append(text)
        # Body surface features shown in "with" section
        for sf in surface_frags:
            with_parts.append(sf["text"])

        if with_parts:
            if len(with_parts) == 1:
                if parts:
                    parts[0] = f"{parts[0]} with {with_parts[0]}"
                else:
                    parts.append(with_parts[0])
            else:
                joined = ", ".join(with_parts[:-1]) + (f", and {with_parts[-1]}" if len(with_parts) > 1 else "")
                if parts:
                    parts[0] = f"{parts[0]} with {joined}"
                else:
                    parts.append(joined)

        if clothing_frags:
            clothing_frags.sort(key=lambda f: -f.get("priority", 50))
            clothing_texts = [f["text"] for f in clothing_frags]
            if len(clothing_texts) == 1:
                text = clothing_texts[0]
                # Add article for single clothing item
                if text and not text.startswith(("a ", "an ", "the ")):
                    first_char = text[0].lower()
                    article = "an" if first_char in "aeiou" else "a"
                    text = f"{article} {text}"
                parts.append(f"wearing {text}")
            elif len(clothing_texts) == 2:
                parts.append(f"wearing {clothing_texts[0]} and {clothing_texts[1]}")
            else:
                joined = ", ".join(clothing_texts[:-1])
                parts.append(f"wearing {joined}, and {clothing_texts[-1]}")

        if body_config_frags:
            for f in body_config_frags:
                parts.append(f["text"])

        if pose_frags:
            for f in pose_frags:
                parts.append(f["text"])

        # Attach actor-specific relationship fragments
        actor_rels = [f for f in rel_frags_actor]
        if actor_rels:
            if render_profile.get("narrative_mode") == "scene_description":
                actor_rels.sort(key=lambda f: f.get("chain_order", 99))
                # Convert the first one to finite verb
                first_clause = actor_rels[0].get("clause_text", actor_rels[0]["text"])
                for participle, finite in {
                    "holding": "holds",
                    "sitting": "sits",
                    "hugging": "hugs",
                    "standing next to": "stands next to",
                    "sitting inside": "sits inside",
                    "soaking in": "soaks in",
                }.items():
                    if first_clause.startswith(participle):
                        first_clause = finite + first_clause[len(participle):]
                        break
                
                parts.append(first_clause)
                
                # Append remaining clauses with space
                for f in actor_rels[1:]:
                    c = f.get("clause_text", f["text"])
                    if c:
                        parts.append(c)
            else:
                for f in actor_rels:
                    clause = f.get("clause_text", f["text"])
                    if clause:
                        if parts and not parts[-1].endswith(","):
                            parts[-1] = parts[-1].rstrip() + ","
                        parts.append(f" {clause}" if not clause.startswith(" ") else clause)

        if not parts:
            return ""

        result = " ".join(parts)
        result = re.sub(r"\s+", " ", result).strip()
        result = re.sub(r",\s*looking toward", " looking toward", result)
        return result

    # Build relationship lookup per actor
    rel_by_actor: dict = {aid: [] for aid in physical_ids}
    ungrouped_rels = []
    for f in fragments:
        if f.get("frag_type") == "relationship":
            aid = f.get("actor_id")
            if aid and aid in rel_by_actor:
                rel_by_actor[aid].append(f)
            else:
                ungrouped_rels.append(f)

    # Render each actor
    actor_parts = []
    for aid in physical_ids:
        frags_for_actor = actor_frags[aid] + rel_by_actor[aid]
        rendered = _render_actor(aid, frags_for_actor)
        if rendered:
            actor_parts.append(rendered)

    if not actor_parts:
        return ""

    result = ", ".join(actor_parts)

    # Append ungrouped relationships
    if ungrouped_rels:
        for f in ungrouped_rels:
            clause = f.get("clause_text", f["text"])
            if clause:
                if not result.endswith(","):
                    result = result.rstrip() + ","
                result += f" {clause}" if not clause.startswith(" ") else clause

    # Append environment
    if env_frags:
        env_text = env_frags[0]["text"] if env_frags else ""
        if env_text:
            if any(k in env_text.lower() for k in ("cafe", "office", "room", "restaurant", "tunnel")):
                prep = "inside"
            elif "beach" in env_text.lower() or "court" in env_text.lower():
                prep = "on"
            elif "poolside" in env_text.lower():
                prep = "at"
            else:
                prep = "in"
            
            if env_text.startswith(("in ", "on ", "at ", "inside ")):
                result += f" {env_text}"
            elif env_text.startswith(("a ", "an ", "the ")):
                result += f" {prep} {env_text}"
            else:
                vowels = "aeiou"
                art = "an" if env_text[0].lower() in vowels else "a"
                result += f" {prep} {art} {env_text}"

    comp_frags = [f for f in other_shared if f.get("frag_type") == "composition"]
    if render_profile.get("narrative_mode") == "scene_description":
        other_shared = [f for f in other_shared if f.get("frag_type") != "composition"]

    if render_profile.get("narrative_mode") == "scene_description" and comp_frags:
        comp_text = comp_frags[0]["text"]
        if "cinematic" in comp_text:
            suffix = ", shot in cinematic style"
        elif "over-the-shoulder" in comp_text:
            suffix = ", shot in an over-the-shoulder style"
        else:
            suffix = f", shot in {comp_text} style"
        result += suffix

    # Append style/atmospheric
    for f in style_frags_shared + other_shared:
        text = f["text"]
        if text:
            if not result.endswith(","):
                result = result.rstrip() + ","
            result += f" {text}" if not text.startswith(" ") else text

    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r",\s*looking toward", " looking toward", result)

    return result


class PromptCompiler(Assembler):
    def compile_scene(self, scene_data: dict, strict: bool = False) -> str:
        return self.assemble(scene_data, strict=strict)
