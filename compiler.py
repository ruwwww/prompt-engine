"""
prompt-engine/assembler.py
Clean Slate Assembler — Pure functions, prototypal inheritance, grammar catalog.
"""
import os
import json
import re
from typing import Any, Dict, List, Optional, Tuple
import output_formatter
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


# ---------------------------------------------------------------------------
# Camera Framing Mapping
# ---------------------------------------------------------------------------

CAMERA_FRAMING_MAP = {
    "close_up": "close-up",
    "medium": "medium",
    "full_body": "full-body",
}

# ---------------------------------------------------------------------------
# Shared utility (ported from compiler.py)
# ---------------------------------------------------------------------------


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
    if isinstance(attire_name, str) and attire_name in attires_db:
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

def resolve_references(components: dict, scene_objects: dict,
                       primitives_db: dict = None) -> dict:
    """Replace owned_item_id references with actual item data.
    Expands template_key to garment_type from the primitive catalog
    and strips template_key from resolved components.
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
                _expand_template_key(resolved, primitives_db)
                result[zone] = resolved
            else:
                base_name = re.sub(r"_\d+$", "", item_id)
                template_key = "".join(w.capitalize() for w in base_name.split("_"))
                resolved = {k: v for k, v in zone_data.items() if k != "owned_item_id"}
                resolved["template_key"] = template_key
                _expand_template_key(resolved, primitives_db)
                result[zone] = resolved

    # Second pass: expand template_key on non-owned_item_id sub-components
    # (e.g. morphology, or other zones that reference primitives directly)
    for zone, zone_data in result.items():
        if isinstance(zone_data, dict) and "template_key" in zone_data:
            if "owned_item_id" not in zone_data:
                _expand_template_key(zone_data, primitives_db)

    return result


def _expand_template_key(component: dict, primitives_db: dict = None) -> None:
    """In-place: expand template_key by fetching primitive data from primitives_db,
    deep-merging literal values into the component, then preserving template_key
    as _primitive_id for Jinja2 template lookup.
    Keeps template_key only if primitive is not found
    (e.g. fixtures where template_key IS the data)."""
    tkey = component.get("template_key")
    if tkey and primitives_db:
        prim = primitives_db.get(tkey)
        if isinstance(prim, dict):
            for k, v in prim.items():
                if k not in component:
                    component[k] = v
            # Preserve the template_key as _primitive_id before stripping
            if "_primitive_id" not in component:
                component["_primitive_id"] = tkey
            component.pop("template_key", None)
            component.pop("template", None)
    component.pop("template", None)


# ---------------------------------------------------------------------------
# Pipeline Step 4: apply_relationships
# ---------------------------------------------------------------------------

def apply_relationships(
    relationships: list,
    scene_objects: dict,
    visible_zones: list,
    actions_db: dict,
    spatial_db: dict,
    environments_db: dict,
    placements: dict = None,
    affordance_types_db: dict = None,
    env_data: dict = None,
    jinja2_env: object = None,
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
        subjects_ids = rel.get("subjects")

        if not actor_id and not subjects_ids:
            continue

        # Skip if relationship has target/object/container role but missing value
        roles = definition.get("roles", {})
        has_object_role = any(r in ("object", "target", "container") for r in roles)
        if has_object_role and not object_id:
            continue

        actor_obj = scene_objects.get(actor_id, {}) if actor_id else {}
        object_obj = scene_objects.get(object_id, {}) if object_id else {}

        # Try affordance query first (new system)
        if affordance_types_db and env_data and object_id and actor_id:
            binding = _resolve_affordance_query(
                rel_type, object_obj, set(visible_zones),
                env_data, affordance_types_db,
                jinja2_env,
            )
            if binding:
                clause_head = binding.get("clause_head", "")
                preposition = binding.get("preposition", "")
                object_phrase = binding.get("object_phrase", "")
                if preposition:
                    clause_text = f"{clause_head} {preposition} {object_phrase}"
                else:
                    clause_text = f"{clause_head} {object_phrase}"
                text = clause_text
                fragments.append({
                    "zone": "relationship",
                    "frag_type": "relationship",
                    "tags": ["action"],
                    "priority": 88,
                    "text": text,
                    "clause_text": clause_text,
                    "actor_id": actor_id,
                    "action_id": binding.get("action_id", rel_type),
                    "chain_order": rel.get("chain_order", 1),
                })
                mentioned_ids.add(actor_id)
                mentioned_ids.add(object_id)
                continue

        valid = True
        for role_name, role_def in roles.items():
            allowed = role_def.get("allowed", [])
            multiple = role_def.get("multiple", False)
            if multiple:
                r_ids = rel.get(role_name, [])
                if not isinstance(r_ids, list):
                    r_ids = [r_ids] if r_ids else []
                for rid in r_ids:
                    if rid and rid in scene_objects:
                        role_obj = scene_objects[rid]
                        role_type = role_obj.get("type", "")
                        if allowed and role_type not in allowed:
                            valid = False
                            break
            else:
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
        if actor_id and actor_zone and actor_zone not in visible_zones:
            continue

        priority = definition.get("priority", 80)
        chain_order = definition.get("chain_order", 99)

        # Variant resolution — check object type for variant matching
        object_obj_type = object_obj.get("type", "")
        variant_id = ""
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
                variant_id = variant.get("variant_id", "")
                break

        actor_phrase = _get_noun_phrase(actor_id, rel, scene_objects, mentioned_ids, placements, jinja2_env) if actor_id else ""
        object_phrase = _get_noun_phrase(object_id, rel, scene_objects, mentioned_ids, placements, jinja2_env) if object_id else ""

        subjects_phrases = []
        if isinstance(subjects_ids, list):
            for sub_id in subjects_ids:
                sub_phrase = _get_noun_phrase(sub_id, rel, scene_objects, mentioned_ids, placements, jinja2_env)
                if sub_phrase:
                    subjects_phrases.append(sub_phrase)

        possessive = "their"
        if actor_id and actor_obj:
            actor_gender = actor_obj.get("gender", "person")
            if actor_gender == "man":
                possessive = "his"
            elif actor_gender == "woman":
                possessive = "her"

        ctx = {
            "actor": actor_phrase,
            "object": object_phrase,
            "subject": actor_phrase,
            "target": object_phrase,
            "container": object_phrase,
            "subjects": subjects_phrases,
            "_possessive": possessive,
        }

        # Render using Jinja2 action templates
        text = ""
        clause_text = ""
        variant_suffix = f"_{variant_id}" if variant_id else ""
        if jinja2_env:
            try:
                text = jinja2_env.get_template(f"actions/{rel_type}{variant_suffix}.jinja2").render(**ctx)
            except TemplateNotFound:
                pass
            try:
                clause_text = jinja2_env.get_template(f"actions/{rel_type}{variant_suffix}_clause.jinja2").render(**ctx)
            except TemplateNotFound:
                pass

        if actor_id:
            mentioned_ids.add(actor_id)
        if object_id:
            mentioned_ids.add(object_id)
        if isinstance(subjects_ids, list):
            for sub_id in subjects_ids:
                mentioned_ids.add(sub_id)

        fragments.append({
            "zone": "relationship",
            "frag_type": "relationship",
            "tags": definition.get("tags", ["action"]),
            "priority": priority,
            "text": text,
            "clause_text": clause_text,
            "actor_id": actor_id,
            "action_id": rel_type,
            "chain_order": chain_order,
        })

    return fragments


def _get_noun_phrase(
    entity_id: str,
    rel: dict,
    scene_objects: dict,
    mentioned_ids: set,
    placements: dict = None,
    jinja2_env: object = None,
) -> str:
    """Generate a noun phrase for an entity in a relationship."""
    if not entity_id:
        return ""
    obj = scene_objects.get(entity_id, {})
    obj_type = obj.get("type", "")

    if obj_type in ("human", "creature"):
        gender = obj.get("gender", "person")
        is_subject_list = isinstance(rel.get("subjects"), list) and entity_id in rel.get("subjects")
        if entity_id in mentioned_ids and not is_subject_list:
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
        if template_key:
            if jinja2_env:
                j2_text = _render_jinja2_template(jinja2_env, template_key + ".jinja2", obj)
                if j2_text:
                    return j2_text
        parts = [obj.get("material", ""), obj.get("color", ""), obj_type]
        phrase = " ".join(p for p in parts if p).strip()
        return phrase if phrase else entity_id

    mentioned_ids.add(entity_id)

    template_key = obj.get("template_key")
    phrase = None
    if jinja2_env:
        t_name = (template_key + ".jinja2") if template_key else None
        if t_name:
            try:
                jinja2_env.get_template(t_name)
                phrase = _render_jinja2_template(jinja2_env, t_name, obj)
            except Exception:
                pass
        if not phrase:
            if obj_type == "fixture":
                phrase = _render_jinja2_template(jinja2_env, "Fixture.jinja2", obj)
            elif obj_type in ("object", "drink", "item"):
                phrase = _render_jinja2_template(jinja2_env, "Object.jinja2", obj)

    if not phrase:
        if obj.get("label"):
            phrase = obj["label"]
        elif obj_type == "fixture":
            phrase = template_key.replace("_", " ") if template_key else entity_id
        elif obj_type in ("object", "drink", "item"):
            phrase = template_key.replace("_", " ") if template_key else entity_id
        else:
            # Fallback: material + color + type
            parts = [obj.get("material", ""), obj.get("color", ""), obj_type]
            phrase = " ".join(p for p in parts if p).strip()
            if not phrase:
                phrase = entity_id

    # Add article for non-plural, or possessive pronoun if owner is defined
    owner_id = obj.get("owner")
    if owner_id and owner_id in scene_objects:
        owner_obj = scene_objects[owner_id]
        gender = owner_obj.get("gender", "person")
        subj_t = owner_obj.get("subject", "")
        possessive = "their"
        if gender in ("man", "boy") or subj_t in ("man", "boy"):
            possessive = "his"
        elif gender in ("woman", "girl") or subj_t in ("woman", "girl"):
            possessive = "her"
            
        if phrase:
            # Strip any leading article from the phrase before prepending possessive
            for art in ("a ", "an ", "the "):
                if phrase.lower().startswith(art):
                    phrase = phrase[len(art):].strip()
                    break
            phrase = f"{possessive} {phrase}"
    elif phrase and not phrase.startswith(("a ", "an ", "the ")):
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

def _natural_join(items: list) -> str:
    """Join a list of strings with commas and 'and' for the last item."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _render_fixture_label(fixture_obj: dict, jinja2_env: object = None) -> str:
    """Render a fixture object into a descriptive noun phrase using its template."""
    template_key = fixture_obj.get("template_key", "")
    if jinja2_env:
        t_name = (template_key + ".jinja2") if template_key else "Fixture.jinja2"
        try:
            if template_key and hasattr(jinja2_env, "get_template"):
                jinja2_env.get_template(t_name)
                j2_text = _render_jinja2_template(jinja2_env, t_name, fixture_obj)
            else:
                j2_text = _render_jinja2_template(jinja2_env, "Fixture.jinja2", fixture_obj)
            if j2_text:
                return j2_text
        except Exception:
            pass
    return fixture_obj.get("label", template_key.lower().replace("_", " ") if template_key else "fixture")


def apply_environment(
    scene_data: dict,
    scene_objects: dict,
    atmospheres_db: dict,
    lighting_db: dict,
    weather_db: dict,
    composition_db: dict,
    jinja2_env: object = None,
    relationship_target_ids: set = None,
    atmosphere_db: dict = None,
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
        if isinstance(env_data, str):
            env_data = {"type": env_data}
        env_type = env_data.get("template_key") or env_data.get("location") or env_data.get("type")
        if env_type:
            db_key = env_type
            if db_key not in atmospheres_db and db_key.lower() in atmospheres_db:
                db_key = db_key.lower()
            env_def = atmospheres_db.get(db_key, {})

            ground = env_def.get("ground", "")
            envelope = env_def.get("envelope", "")
            vista = env_def.get("vista", "")
            background = env_def.get("background", "")

            # Look up weather / lighting overrides
            user_lighting = env_data.get("lighting")
            user_weather = env_data.get("weather")
            if user_lighting or user_weather:
                lighting_str = ""
                if user_lighting:
                    lighting_entry = lighting_db.get(user_lighting, {})
                    if isinstance(lighting_entry, dict):
                        lighting_str = lighting_entry.get("template", user_lighting)
                    else:
                        lighting_str = user_lighting

                weather_str = ""
                if user_weather:
                    weather_entry = weather_db.get(user_weather, {})
                    if isinstance(weather_entry, dict):
                        weather_str = weather_entry.get("template", user_weather)
                    else:
                        weather_str = user_weather

                # Combine them to override the envelope
                if weather_str and lighting_str:
                    envelope = f"{weather_str} {lighting_str}"
                elif weather_str:
                    envelope = f"{weather_str} lighting"
                elif lighting_str:
                    envelope = f"{lighting_str} lighting"

            # Render Jinja2 templates
            env_text = ""
            if jinja2_env:
                env_text = _render_jinja2_template(jinja2_env, "Environment.jinja2", {
                    "ground": ground,
                    "envelope": envelope,
                    "vista": vista,
                    "background": background,
                })
            if not env_text:
                parts = []
                if ground:
                    parts.append(ground)
                if vista:
                    parts.append(f"with a view of {vista}")
                env_text = ", ".join(parts)

            lighting_text = ""
            if jinja2_env:
                lighting_text = _render_jinja2_template(jinja2_env, "Lighting.jinja2", {
                    "envelope": envelope,
                })
            if not lighting_text:
                lighting_text = envelope

            fragments.append({
                "zone": "environment",
                "frag_type": "environment",
                "tags": ["environment"],
                "priority": 65,
                "text": env_text,
                "ground": ground,
                "envelope": envelope,
                "vista": vista,
                "background": background,
            })

            if lighting_text:
                fragments.append({
                    "zone": "lighting",
                    "frag_type": "lighting",
                    "tags": ["environment"],
                    "priority": 55,
                    "text": lighting_text,
                })

    # Ambient fixture discovery: render fixture/furniture objects not referenced by relationships
    if relationship_target_ids is None:
        relationship_target_ids = set()
    ambient_fixture_labels = []
    for obj_id, obj in scene_objects.items():
        if obj.get("type") in ("fixture", "furniture") and obj_id not in relationship_target_ids:
            label = _render_fixture_label(obj, jinja2_env)
            if label:
                first_char = label[0].lower()
                article = "an" if first_char in "aeiou" else "a"
                ambient_fixture_labels.append(f"{article} {label}")

    if ambient_fixture_labels:
        fragments.append({
            "zone": "environment",
            "frag_type": "environment",
            "tags": ["environment"],
            "priority": 60,
            "text": f"featuring {_natural_join(ambient_fixture_labels)}",
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

def _render_jinja2_template(template_env, template_name: str, component: dict) -> str:
    """Render a Jinja2 template for a clothing/component zone.
    Returns empty string if template not found."""
    try:
        template = template_env.get_template(template_name)
        rendered = template.render(**component)
        # Collapse whitespace: newlines, multiple spaces -> single space
        rendered = re.sub(r'\s+', ' ', rendered).strip()
        return rendered
    except TemplateNotFound:
        return ""


def render_to_text(
    visible_components: dict,
    render_profile: str,
    attribute_metadata_db: dict,
    render_profiles_db: dict,
    active_tone: str = "default",
    jinja2_env: object = None,
    ensemble_key: str = None,
) -> list:
    """Render visible components into text fragments.
    Tries Jinja2 templates first (by _primitive_id, then by zone)."""
    fragments = []

    # Phase 0: Try Ensemble-level template (replaces all zone-by-zone rendering)
    if ensemble_key and jinja2_env:
        flat_ctx = {}
        for zone, zone_data in visible_components.items():
            if isinstance(zone_data, dict):
                flat_ctx.update(zone_data)
        ensemble_text = _render_jinja2_template(jinja2_env, ensemble_key + ".jinja2", flat_ctx)
        if ensemble_text:
            fragments.append({
                "zone": "_attire",
                "frag_type": "native",
                "tags": ["clothing"],
                "priority": 60,
                "text": ensemble_text,
            })
            return fragments

    for zone, zone_data in visible_components.items():
        if not isinstance(zone_data, dict):
            continue
        if zone in ("gender", "subject", "attire"):
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

        text = ""

        # Phase 1: Try Jinja2 templates (by _primitive_id, then by zone)
        if jinja2_env:
            primitive_id = zone_data.get("_primitive_id")
            if primitive_id:
                text = _render_jinja2_template(jinja2_env, primitive_id + ".jinja2", zone_data)
            if not text:
                text = _render_jinja2_template(jinja2_env, zone + ".jinja2", zone_data)

        # Hair uses dedicated renderer (not Jinja2 template)
        if not text and zone == "Hair":
            text = render_hair(normalize_hair(zone_data))

        # Fallback for zones without any template
        if not text:
            if zone_data.get("type") in ("clothing", "item", "prop"):
                continue
            text = _render_generic_zone(zone, zone_data)

        if text.strip():
            if zone == "Headwear":
                t_stripped = text.strip()
                if not t_stripped.startswith(("a ", "an ", "the ", "his ", "her ", "their ")):
                    if not (t_stripped.endswith("s") and not t_stripped.endswith("dress") and not t_stripped.endswith("harness")):
                        first_char = t_stripped[0].lower()
                        article = "an" if first_char in "aeiou" else "a"
                        text = f"{article} {t_stripped}"
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
    skip_keys = {"visibility_tags", "render_priority", "render_group", "metadata_key", "renderer", "template_key", "garment_type", "garment"}
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

def validate(scene_data: dict, actions_db: dict,
             spatial_db: dict, subjects_db: dict, strict: bool = False) -> list:
    """Pre-flight checks. Returns list of {"severity": "error"|"warning", "message": str}.

    Checks:
      1. Unknown relationship types (severity: error)
      2. Missing subject presets (severity: warning)
    """
    errors = []

    # 1. Unknown relationship types
    for rel in scene_data.get("relationships", []):
        rel_type = rel.get("type", "")
        if rel_type not in actions_db and rel_type not in spatial_db:
            errors.append({
                "severity": "error",
                "message": f"Unknown relationship type '{rel_type}'",
            })

    # 2. Missing subject presets
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


def derive_preposition(env_data: dict, spatial_prepositions: dict) -> str:
    """
    Derive the correct Subject-in-Environment preposition from structured
    SpatialFrame data. Reads containment from env_data['volume']['containment']
    and surface normal from env_data['primary_surface']['normal'].
    Falls back to 'in' if any key is missing.

    Args:
        env_data: A SpatialFrame dict as loaded from environments.json.
        spatial_prepositions: The loaded data/spatial_prepositions.json dict.

    Returns:
        A preposition string (e.g., 'inside', 'on', 'at', 'in').
    """
    volume = env_data.get("volume", {})
    surface = env_data.get("primary_surface", {})
    containment = volume.get("containment", "open")
    normal = surface.get("normal", "up")
    boundary = volume.get("boundary", "hard")

    containment_rules = spatial_prepositions.get(containment, {})

    if containment == "impossible":
        boundary_key = f"boundary_{boundary}"
        if boundary_key in containment_rules:
            return containment_rules[boundary_key]
        return containment_rules.get("default", "within")

    if containment == "open":
        normal_key = f"normal_{normal}"
        if normal_key in containment_rules:
            return containment_rules[normal_key]
        return containment_rules.get("default", "in")

    return containment_rules.get("default", "in")


ASSEMBLY_PHASES = {
    "subject_identity": 1,
    "attire": 2,
    "posture": 3,
    "figure_anchor": 4,
    "atmosphere": 5,
    "style": 6,
}


def _to_finite(clause_text: str, action_id: str, action_grammar_db: dict, number: str = "singular") -> str:
    """
    Convert a participial clause to finite form using action_grammar.json.

    Args:
        clause_text: The full clause text beginning with the participle
                     (e.g., "leaning against the counter").
        action_id:   The action_id key for lookup in action_grammar_db.
        action_grammar_db: The loaded data/action_grammar.json dict.
        number:      "singular" or "plural" — controls 3sg vs pl form.

    Returns:
        The clause text with the participle replaced by the finite form,
        or the original clause_text unchanged if no grammar entry exists.
    """
    grammar = action_grammar_db.get(action_id)
    if not grammar:
        return clause_text

    participle = grammar.get("participle", "")
    if number == "plural":
        finite = grammar.get("finite_pl", participle)
    else:
        finite = grammar.get("finite_3sg", participle)

    if clause_text.startswith(participle):
        return finite + clause_text[len(participle):]
    elif " " + participle + " " in clause_text:
        return clause_text.replace(" " + participle + " ", " " + finite + " ")

    return clause_text


def _resolve_affordance_query(
    action_id: str,
    target_obj: dict,
    visible_zones: set,
    env_data: dict,
    affordance_types_db: dict,
    jinja2_env: object = None,
) -> dict | None:
    """
    Perform an AffordanceQuery for a single relationship.

    Looks up the target fixture in env_data['fixtures'], matches the action_id
    to an AffordanceRecord, validates body zones against visible_zones.

    Returns a ResolvedBinding dict if valid, or None if invalid/occluded.
    """
    fixture_name = target_obj.get("fixture_name") or target_obj.get("template_key", "").lower()

    fixtures = env_data.get("fixtures", {})
    fixture_def = fixtures.get(fixture_name)

    if fixture_def is None:
        return None

    matched_affordance = None
    for aff_ref in fixture_def.get("affordances", []):
        aff_type_key = aff_ref.get("affordance_type")
        aff_type = affordance_types_db.get(aff_type_key, {})
        if aff_type.get("action_id") == action_id:
            matched_affordance = aff_type
            break

    if matched_affordance is None:
        return None

    required_zones = matched_affordance.get("body_zones", [])
    for zone in required_zones:
        if zone not in visible_zones:
            return None

    # Use Jinja2 template rendering for scene object fixtures when available
    template_key = target_obj.get("template_key", "")
    obj_phrase = None
    if jinja2_env:
        t_name = (template_key + ".jinja2") if template_key else "Fixture.jinja2"
        try:
            if template_key and hasattr(jinja2_env, "get_template"):
                try:
                    jinja2_env.get_template(t_name)
                    obj_phrase = _render_jinja2_template(jinja2_env, t_name, target_obj)
                except Exception:
                    obj_phrase = _render_jinja2_template(jinja2_env, "Fixture.jinja2", target_obj)
            else:
                obj_phrase = _render_jinja2_template(jinja2_env, "Fixture.jinja2", target_obj)
        except Exception:
            pass

    if obj_phrase:
        obj_phrase = obj_phrase.strip()
        first_char = obj_phrase[0].lower()
        obj_article = "an" if first_char in "aeiou" else "a"
        object_phrase = f"{obj_article} {obj_phrase}"
    else:
        fixture_label = target_obj.get("label") or fixture_name.replace("_", " ")
        fixture_article = "a"
        if fixture_label and fixture_label[0].lower() in "aeiou":
            fixture_article = "an"
        object_phrase = f"{fixture_article} {fixture_label}"

    preposition = matched_affordance.get("preposition_hint") or "near"
    clause_head = matched_affordance.get("clause_head", action_id.replace("_", " "))

    return {
        "action_id": action_id,
        "fixture_id": fixture_name,
        "clause_head": clause_head,
        "preposition": preposition,
        "object_phrase": object_phrase,
        "grammatical_role": matched_affordance.get("grammatical_role", "object"),
        "body_zones": required_zones,
    }


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
        self.attribute_metadata_db = _load_json("attribute_metadata.json")
        self.render_profiles_db = _load_json("render_profiles.json")
        self.actions_db = _load_json("actions.json")
        self.spatial_db = _load_json("spatial_relationships.json")
        self.environments_db = _load_json("environments.json")
        self.atmospheres_db = _load_json("primitives/atmospheres.json")
        self.lighting_db = _load_json("lighting.json")
        self.weather_db = _load_json("weather.json")
        self.composition_db = _load_json("composition.json")
        self.styles_db = _load_json("styles.json")
        self.poses_db = _load_json("poses.json")
        self.spatial_prepositions_db = _load_json("spatial_prepositions.json")
        self.affordance_types_db = _load_json("affordance_types.json")
        self.action_grammar_db = _load_json("action_grammar.json")
        self.atmosphere_db = _load_json("atmosphere.json")

        # --- Merge all primitive catalogs into a single primitives_db ---
        self.primitives_db = {}
        for _pf in ("primitives/clothing.json", "primitives/items.json",
                    "primitives/fixtures.json", "primitives/accessories.json",
                    "primitives/hairstyles.json", "primitives/morphologies.json"):
            _data = _load_json(_pf)
            if _data:
                self.primitives_db.update(_data)

        # --- Set up Jinja2 environment for clothing templates ---
        templates_dir = os.path.join(DATA_DIR, "grammar", "templates")
        self.jinja2_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False,
        )

    def resolve_scene(self, scene_data: dict, strict: bool = False) -> dict:
        """Run the full resolution pipeline and return the resolved component trees
        per actor, plus environment/camera state. Useful for debugging and the
        web demo's 'deep merged' JSON preview."""
        validate(scene_data, self.actions_db,
                 self.spatial_db, self.subjects_db, strict=strict)
        camera = scene_data.get("camera", {})
        camera_framing = camera.get("framing", "full_body")
        pose_name = scene_data.get("pose")
        render_profile_name = scene_data.get("render_profile", "character_sheet")

        camera_profiles_path = os.path.join(DATA_DIR, "camera_profiles.json")
        with open(camera_profiles_path, "r", encoding="utf-8") as f:
            camera_profiles = json.load(f)

        scene_objects = {}
        for obj_id, obj_data in scene_data.get("objects", {}).items():
            scene_objects[obj_id] = {**obj_data, "id": obj_id}

        environment_data = scene_data.get("environment", {})
        if isinstance(environment_data, str):
            environment_data = {"type": environment_data}
        env_type = environment_data.get("type")
        env_def = self.environments_db.get(env_type, {}) if env_type else {}
        env_fixtures = env_def.get("fixtures", env_def.get("affordances", {}))

        for rel in scene_data.get("relationships", []):
            for field in ("target", "actor", "subject", "container", "object"):
                val = rel.get(field)
                if isinstance(val, str) and "." in val:
                    parts = val.split(".", 1)
                    if len(parts) == 2:
                        prefix, suffix = parts
                        if env_type and prefix == env_type and suffix in env_fixtures:
                            if val not in scene_objects:
                                scene_objects[val] = {
                                    "id": val, "type": "fixture",
                                    "template_key": suffix, "anchor": suffix,
                                    "env_type": env_type,
                                }

        physical_ids = [oid for oid, obj in scene_objects.items() if _is_physical(obj)]

        actors = {}
        for obj_id in physical_ids:
            obj = scene_objects[obj_id]
            components = resolve_blueprint(obj, self.subjects_db, self.attires_db, scene_objects)
            user_overrides = {k: v for k, v in obj.items()
                              if k not in ("type", "id", "subject", "attire") and isinstance(v, dict)}
            components = apply_delta(components, user_overrides)
            for _scalar_key in ("gender", "morphology"):
                if _scalar_key in obj:
                    components[_scalar_key] = obj[_scalar_key]
            components = resolve_references(components, scene_objects, self.primitives_db)

            visible = filter_by_camera(components, camera_framing, pose_name, self.poses_db)

            gender = components.get("gender", obj.get("gender", "person"))
            subject_name = components.get("subject", obj.get("subject", ""))
            morphology = components.get("morphology", obj.get("morphology", {}))

            actors[obj_id] = {
                "components": components,
                "visible": visible,
                "gender": gender,
                "subject_name": subject_name,
                "morphology": morphology,
            }

        env_resolved = None
        env_prep = "in"
        if env_type:
            db_key = env_type
            if db_key not in self.environments_db and db_key.lower() in self.environments_db:
                db_key = db_key.lower()
            env_resolved = self.environments_db.get(db_key, {})

        return {
            "actors": actors,
            "physical_ids": physical_ids,
            "camera": camera,
            "camera_framing_zones": list(camera_profiles.get(camera_framing, [])),
            "environment_type": env_type,
            "environment_resolved": env_resolved,
            "render_profile": render_profile_name,
        }

    def _render_object_label(self, obj: dict) -> str:
        """Render the base noun phrase of an object without articles or possession."""
        template_key = obj.get("template_key", "")
        phrase = ""
        if self.jinja2_env:
            t_name = (template_key + ".jinja2") if template_key else "Object.jinja2"
            try:
                if template_key:
                    self.jinja2_env.get_template(t_name)
                    phrase = _render_jinja2_template(self.jinja2_env, t_name, obj)
                else:
                    phrase = _render_jinja2_template(self.jinja2_env, "Object.jinja2", obj)
            except Exception:
                pass
        
        if not phrase:
            label = obj.get("label")
            if label:
                phrase = label
            else:
                parts = [obj.get("material", ""), obj.get("color", ""), template_key.lower().replace("_", " ") if template_key else obj.get("type", "object")]
                phrase = " ".join(p for p in parts if p).strip()
                if not phrase:
                    phrase = "object"
        return phrase

    def _render_object(self, obj: dict, scene_objects: dict = None) -> str:
        """Render an object into a descriptive noun phrase using its template or fallback,
        taking possession (owner) and spatial context (location) into account."""
        if scene_objects is None:
            scene_objects = {}
        
        label = self._render_object_label(obj)
        
        # Check possession/ownership
        owner_id = obj.get("owner")
        phrase = ""
        if owner_id:
            owner = scene_objects.get(owner_id)
            if owner:
                gender = owner.get("gender", "neutral")
                possessive = "his" if gender == "man" else "her" if gender == "woman" else "their"
                phrase = f"{possessive} {label}"
        
        if not phrase:
            if label and not label.startswith(("a ", "an ", "the ")):
                first_char = label[0].lower()
                article = "an" if first_char in "aeiou" else "a"
                phrase = f"{article} {label}"
            else:
                phrase = label

        # Check spatial context (location)
        location_id = obj.get("location")
        if location_id:
            location = scene_objects.get(location_id)
            if location:
                location_label = location.get("label", location_id)
                # Keep compatibility with both fixture labels/templates
                phrase = f"{phrase} on the {location_label}"
        
        return phrase

    def _is_object_visible(self, obj: dict, visible_zones: set) -> bool:
        """Check if an object is visible based on camera framing zones."""
        # Default to LowerBody for floor / environment objects if zone is not explicitly provided.
        obj_zone = obj.get("zone", "LowerBody")
        return obj_zone in visible_zones

    def _is_excluded_by_relationship(self, obj_id: str, relationships: list) -> bool:
        """Only exclude objects that are actively target of interaction like 'holding' or 'using'."""
        for rel in relationships:
            rel_type = rel.get("type", "")
            if rel.get("object") == obj_id and rel_type in ("holding", "using"):
                return True
            if rel.get("target") == obj_id and rel_type in ("holding", "using"):
                return True
        return False

    def _collect_objects(self, scene_objects: dict, relationships: list, visible_zones: set) -> list:
        """Collect and deduplicate visible and non-interaction-excluded objects, rendering them with counts and ownership/context."""
        label_counts = {}
        # Keep track of the first raw object of each label to copy properties like owner and location
        label_to_obj = {}

        for obj_id, obj in scene_objects.items():
            if obj.get("type") in ("object", "drink", "item"):
                if not self._is_object_visible(obj, visible_zones):
                    continue
                if self._is_excluded_by_relationship(obj_id, relationships):
                    continue

                label = self._render_object_label(obj)
                if not label:
                    continue
                
                label_counts[label] = label_counts.get(label, 0) + 1
                if label not in label_to_obj:
                    label_to_obj[label] = obj

        prop_phrases = []
        for label, count in label_counts.items():
            obj = label_to_obj[label]
            # Support pluralization
            rendered_label = label
            if count > 1:
                # Basic pluralization: add 's' unless it already ends with 's' or is irregular
                if label.endswith("s"):
                    rendered_label = f"{count} {label}"
                else:
                    rendered_label = f"{count} {label}s"
            
            # Now build the full phrase with possession (owner)
            owner_id = obj.get("owner")
            phrase = ""
            if owner_id and count == 1: # Possession usually applies to singular or is prepended
                owner = scene_objects.get(owner_id)
                if owner:
                    gender = owner.get("gender", "neutral")
                    possessive = "his" if gender == "man" else "her" if gender == "woman" else "their"
                    phrase = f"{possessive} {rendered_label}"
            
            if not phrase:
                if count > 1:
                    phrase = rendered_label
                elif rendered_label and not rendered_label.startswith(("a ", "an ", "the ")):
                    first_char = rendered_label[0].lower()
                    article = "an" if first_char in "aeiou" else "a"
                    phrase = f"{article} {rendered_label}"
                else:
                    phrase = rendered_label

            # Check spatial context (location)
            location_id = obj.get("location")
            if location_id:
                location = scene_objects.get(location_id)
                if location:
                    location_label = location.get("label", location_id)
                    phrase = f"{phrase} on the {location_label}"
            
            prop_phrases.append(phrase)

        return prop_phrases



    def inject_camera_descriptor(self, state: dict) -> dict:
        """Inject Camera text based on framing value (if toggle is ON).
        Returns state with '_camera_text' key containing the camera descriptor string.
        If user has manually defined a Camera key in scene data, does nothing."""
        inject = state.get("_inject_camera", True)
        if not inject:
            return state
        camera = state.get("camera", {})
        if "Camera" in state.get("scene_data", {}):
            return state
        framing = camera.get("framing", "full_body")
        mapped_framing = CAMERA_FRAMING_MAP.get(framing, "full-body")
        shot_type = camera.get("shot_type", "")
        angle = camera.get("angle", "")
        # Phase 1: Try Jinja2 camera template with richer context
        text = ""
        if self.jinja2_env:
            text = _render_jinja2_template(self.jinja2_env, "Camera.jinja2", {
                "framing": mapped_framing,
                "shot_type": shot_type,
                "angle": angle,
            })
        # Phase 2: Plain string fallback
        if not text:
            if shot_type:
                text = f"{shot_type} shot of"
            elif mapped_framing:
                text = f"{mapped_framing} shot of"
            else:
                text = "Shot of"
        state["_camera_text"] = text
        return state

    def _pluralize_subject_type(self, subj_type: str) -> str:
        plurals = {
            "woman": "women",
            "man": "men",
            "person": "people",
            "child": "children",
            "girl": "girls",
            "boy": "boys",
            "orc": "orcs",
            "elf": "elves",
            "creature": "creatures",
            "human": "humans",
            "adult": "adults"
        }
        return plurals.get(subj_type, subj_type + "s")

    def _build_actor_description(self, actor_id: str, frags: list, scene_objects: dict, narrative_mode: str = "fact_chain") -> dict:
        obj = scene_objects.get(actor_id, {})
        gender = obj.get("gender", "person")
        morphology = obj.get("morphology", {})
        subject_type = _get_subject_type(gender, morphology)
        
        identity_adjectives = []
        hair_phrase = ""
        clothing_items = []
        accessories = []
        posture_phrase = ""
        action_clauses = []
        extra_identity_texts = []
        
        CLOTHING_ZONES = {"UpperBody", "LowerBody", "Feet"}
        ACCESSORY_ZONES = {"Hands", "Jewelry", "Accessories", "Headwear"}
        
        for f in frags:
            zone = f.get("zone", "")
            frag_type = f.get("frag_type", "")
            
            if zone == "_subject_type":
                subject_type = f["text"]
            elif zone == "Hair":
                hair_phrase = f["text"]
            elif zone == "Face":
                if f["text"] not in identity_adjectives:
                    identity_adjectives.append(f["text"])
            elif zone in CLOTHING_ZONES:
                if not any(item["label"] == f["text"] for item in clothing_items):
                    clothing_items.append({"layer_order": f.get("priority", 50), "label": f["text"]})
            elif zone in ACCESSORY_ZONES:
                if f["text"] not in accessories:
                    accessories.append(f["text"])
            elif frag_type == "relationship":
                clause = f.get("clause_text", f["text"])
                if clause not in action_clauses:
                    action_clauses.append(clause)
            elif zone in ("body_config", "_pose", "pose"):
                posture_texts = [p.strip() for p in posture_phrase.split(",")] if posture_phrase else []
                if f["text"] not in posture_texts:
                    if posture_phrase:
                        posture_phrase += ", " + f["text"]
                    else:
                        posture_phrase = f["text"]
            elif zone in ("Tusks", "Ears", "Jaw", "Eyes"):
                if f["text"] not in extra_identity_texts:
                    extra_identity_texts.append(f["text"])
                    
        render_style = obj.get("render_style", "")
        
        adj_part = ", ".join(identity_adjectives) if identity_adjectives else ""
        subject_phrase_parts = []
        if render_style:
            subject_phrase_parts.append(render_style)
        if adj_part:
            subject_phrase_parts.append(adj_part)
        subject_phrase_parts.append(subject_type)
        subject_phrase = " ".join(subject_phrase_parts)
        
        with_parts = []
        if hair_phrase:
            with_parts.append(hair_phrase)
        for extra in extra_identity_texts:
            with_parts.append(extra)
            
        if with_parts:
            subject_phrase += " with " + output_formatter._join_list(with_parts)
            
        pronoun = "She"
        if subject_type in ("man", "boy"):
            pronoun = "He"
        elif subject_type not in ("woman", "girl"):
            pronoun = "They"
            
        if narrative_mode == "scene_description":
            rel_info = []
            for f in frags:
                if f.get("frag_type") == "relationship":
                    clause = f.get("clause_text", f["text"])
                    rel_info.append((clause, f.get("chain_order", 99), f.get("action_id", "")))
            rel_info.sort(key=lambda x: x[1])
            if rel_info:
                first_clause, _, first_act_id = rel_info[0]
                number = "plural" if pronoun == "They" else "singular"
                finite_first = _to_finite(first_clause, first_act_id, self.action_grammar_db, number)
                
                chained_clauses = [finite_first]
                for clause, _, _ in rel_info[1:]:
                    chained_clauses.append(clause)
                action_clauses = [" ".join(chained_clauses)]
            else:
                action_clauses = []
            
        return {
            "actor_id": actor_id,
            "subject_phrase": subject_phrase,
            "subject_type": subject_type,
            "clothing_items": clothing_items,
            "accessories": accessories,
            "posture_phrase": posture_phrase,
            "action_clauses": action_clauses,
            "pronoun": pronoun,
            "render_style": render_style
        }

    def _combine_actor_descriptions(self, descriptions: list, scene_objects: dict, scene_data: dict, narrative_mode: str = "fact_chain") -> dict:
        groups = scene_data.get("groups", [])
        
        desc_by_id = {d["actor_id"]: d for d in descriptions}
        
        actor_to_group = {}
        group_by_id = {}
        for g in groups:
            group_by_id[g["id"]] = g
            for member in g.get("members", []):
                if member in desc_by_id:
                    actor_to_group[member] = g
                    
        grouped_actors = defaultdict(list)
        non_grouped_actors = []
        for d in descriptions:
            g = actor_to_group.get(d["actor_id"])
            if g:
                grouped_actors[g["id"]].append(d)
            else:
                non_grouped_actors.append(d)
                
        # Build combined subject phrase
        subj_phrases = []
        processed_groups = set()
        for d in descriptions:
            actor_id = d["actor_id"]
            g = actor_to_group.get(actor_id)
            if g:
                if g["id"] not in processed_groups:
                    processed_groups.add(g["id"])
                    label = g.get("label") or g.get("type") or "group"
                    article = "an" if label[0].lower() in "aeiou" else "a"
                    subj_phrases.append(f"{article} {label}")
            else:
                phrase = d["subject_phrase"]
                if phrase.startswith("A "):
                    phrase = "a " + phrase[2:]
                elif phrase.startswith("An "):
                    phrase = "an " + phrase[3:]
                subj_phrases.append(phrase)
                
        if len(subj_phrases) == 1:
            subject_phrase = subj_phrases[0]
        elif len(subj_phrases) == 2:
            subject_phrase = f"{subj_phrases[0]} and {subj_phrases[1]}"
        else:
            subject_phrase = ", ".join(subj_phrases[:-1]) + f", and {subj_phrases[-1]}"
            
        if subject_phrase:
            subject_phrase = subject_phrase[0].upper() + subject_phrase[1:]
            
        # Build clothing
        clothing_parts = []
        for gid, members in grouped_actors.items():
            member_clothing_sets = []
            for m in members:
                labels = sorted([item["label"] for item in m["clothing_items"]])
                member_clothing_sets.append(tuple(labels))
            if len(set(member_clothing_sets)) == 1 and members[0]["clothing_items"]:
                pronoun = "Both" if len(members) == 2 else "They"
                labels = [item["label"] for item in sorted(members[0]["clothing_items"], key=lambda x: x.get("layer_order", 0), reverse=True)]
                if labels:
                    labels[0] = "matching " + labels[0]
                c_phrase = f"{pronoun} wear " + output_formatter._join_list_with_over(labels) + "."
                clothing_parts.append(c_phrase)
            else:
                for m in members:
                    subj_t = m["subject_type"]
                    style_prefix = ""
                    if m["render_style"]:
                        if "photoreal" in m["render_style"].lower():
                            style_prefix = "realistic "
                        elif "stylized" in m["render_style"].lower() or "anim" in m["render_style"].lower():
                            style_prefix = "animated "
                        else:
                            style_prefix = m["render_style"] + " "
                    identifier = f"The {style_prefix}{subj_t}"
                    sorted_items = sorted(m["clothing_items"], key=lambda x: x.get("layer_order", 0), reverse=True)
                    labels = [item["label"] for item in sorted_items]
                    if labels:
                        c_phrase = f"{identifier} wears " + output_formatter._join_list_with_over(labels) + "."
                        clothing_parts.append(c_phrase)
                        
        for d in non_grouped_actors:
            c_phrase = output_formatter.format_clothing_field(d["clothing_items"], d["pronoun"])
            if c_phrase:
                clothing_parts.append(c_phrase)
        clothing_phrase = " ".join(clothing_parts)
        
        # Build action
        action_parts = []
        holding_objs = {}
        for d in descriptions:
            actor_id = d["actor_id"]
            held = []
            for rel in scene_data.get("relationships", []):
                if rel.get("type") == "holding" and rel.get("actor") == actor_id:
                    obj_id = rel.get("object")
                    if obj_id in scene_objects:
                        held.append(obj_id)
            holding_objs[actor_id] = held

        # Handle matching held items (e.g. suitcases)
        matching_held_clause = ""
        if len(descriptions) == 2:
            a1_id, a2_id = descriptions[0]["actor_id"], descriptions[1]["actor_id"]
            a1_held = holding_objs.get(a1_id, [])
            a2_held = holding_objs.get(a2_id, [])
            if len(a1_held) == 1 and len(a2_held) == 1:
                o1 = scene_objects[a1_held[0]]
                o2 = scene_objects[a2_held[0]]
                if o1.get("label") == o2.get("label") and o1.get("label"):
                    label = o1["label"]
                    plural_label = label + "s" if not label.endswith("s") else label
                    matching_held_clause = f"Both hold their matching {plural_label}"
                    for d in descriptions:
                        d["action_clauses"] = [
                            c for c in d["action_clauses"]
                            if not (c.startswith("holding ") or c.startswith("holds ") or c.startswith("is holding "))
                        ]

        # First check if all same action for all actors
        all_action_sets = []
        for d in descriptions:
            action_text = d["posture_phrase"] + " | " + " & ".join(d["action_clauses"])
            all_action_sets.append(action_text)
        all_same_action = len(set(all_action_sets)) == 1

        if all_same_action and len(descriptions) > 1:
            pronoun = "Both" if len(descriptions) == 2 else "They"
            act_phrase = output_formatter.format_action_field(descriptions[0]["posture_phrase"], descriptions[0]["action_clauses"], pronoun, is_finite=(narrative_mode == "scene_description"))
            action_parts.append(act_phrase)
        elif matching_held_clause:
            a1_other = descriptions[0]["action_clauses"]
            a2_other = descriptions[1]["action_clauses"]
            if a1_other == a2_other:
                other_clause = " and ".join(a1_other) if a1_other else ""
                if other_clause:
                    if other_clause.startswith("looking "):
                        other_clause = "look " + other_clause[8:]
                    elif other_clause.startswith("smiling "):
                        other_clause = "smile " + other_clause[8:]
                    combined_act = f"Both hold their matching {plural_label} and {other_clause}"
                else:
                    combined_act = f"Both hold their matching {plural_label}"
                action_parts.append(output_formatter._cap_sentence(combined_act))
            else:
                action_parts.append(output_formatter._cap_sentence(matching_held_clause))
                for d in descriptions:
                    subj_t = d["subject_type"]
                    style_prefix = ""
                    if d["render_style"]:
                        if "photoreal" in d["render_style"].lower():
                            style_prefix = "realistic "
                        elif "stylized" in d["render_style"].lower() or "anim" in d["render_style"].lower():
                            style_prefix = "animated "
                        else:
                            style_prefix = d["render_style"] + " "
                    identifier = f"The {style_prefix}{subj_t}"
                    parts = []
                    verb_be = "" if narrative_mode == "scene_description" else " is"
                    if d["posture_phrase"]:
                        parts.append(f"{identifier}{verb_be} {d['posture_phrase']}")
                    for clause in d["action_clauses"]:
                        if parts:
                            parts.append(clause)
                        else:
                            parts.append(f"{identifier}{verb_be} {clause}")
                    if parts:
                        action_parts.append(output_formatter._cap_sentence(", ".join(parts)))
        else:
            for gid, members in grouped_actors.items():
                member_action_sets = []
                for m in members:
                    action_text = m["posture_phrase"] + " | " + " & ".join(m["action_clauses"])
                    member_action_sets.append(action_text)
                if len(set(member_action_sets)) == 1:
                    pronoun = "Both" if len(members) == 2 else "They"
                    act_phrase = output_formatter.format_action_field(members[0]["posture_phrase"], members[0]["action_clauses"], pronoun, is_finite=(narrative_mode == "scene_description"))
                    action_parts.append(act_phrase)
                else:
                    for m in members:
                        subj_t = m["subject_type"]
                        style_prefix = ""
                        if m["render_style"]:
                            if "photoreal" in m["render_style"].lower():
                                style_prefix = "realistic "
                            elif "stylized" in m["render_style"].lower() or "anim" in m["render_style"].lower():
                                style_prefix = "animated "
                            else:
                                style_prefix = m["render_style"] + " "
                        identifier = f"The {style_prefix}{subj_t}"
                        parts = []
                        verb_be = "" if narrative_mode == "scene_description" else " is"
                        if m["posture_phrase"]:
                            parts.append(f"{identifier}{verb_be} {m['posture_phrase']}")
                        for clause in m["action_clauses"]:
                            if parts:
                                parts.append(clause)
                            else:
                                parts.append(f"{identifier}{verb_be} {clause}")
                        if parts:
                            action_parts.append(output_formatter._cap_sentence(", ".join(parts)))
                            
            for d in non_grouped_actors:
                act_phrase = output_formatter.format_action_field(d["posture_phrase"], d["action_clauses"], d["pronoun"], is_finite=(narrative_mode == "scene_description"))
                if act_phrase:
                    action_parts.append(act_phrase)
                    
        action_phrase = " ".join(action_parts)
        
        return {
            "subject_phrase": subject_phrase,
            "clothing_phrase": clothing_phrase,
            "action_phrase": action_phrase,
            "pronoun": "They" if (len(descriptions) > 1 or all_same_subj) else descriptions[0]["pronoun"]
        }

    def assemble(self, scene_data: dict, strict: bool = False, inject_camera_descriptor: bool = True, output_format: str = "legacy") -> str:
        """Assemble a scene into a prompt string.

        Args:
            scene_data: The scene dictionary.
            strict: If True, raise ValueError on validation errors.
            inject_camera_descriptor: If True, automatically add camera framing
                to the prompt. Default True.
        """
        # Store toggle in state for pipeline steps
        scene_data = {**scene_data, "_inject_camera": inject_camera_descriptor}

        # Pre-flight validation
        validate(scene_data, self.actions_db,
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

        # Resolve environment anchors
        environment_data = scene_data.get("environment", {})
        if isinstance(environment_data, str):
            environment_data = {"type": environment_data}
        env_type = environment_data.get("type")
        env_def = self.environments_db.get(env_type, {}) if env_type else {}
        env_fixtures = env_def.get("fixtures", env_def.get("affordances", {}))

        resolved_relationships = []
        for rel in scene_data.get("relationships", []):
            rel_copy = dict(rel)
            valid_anchor_rel = True
            for field in ("target", "actor", "subject", "container", "object"):
                val = rel_copy.get(field)
                if isinstance(val, str) and "." in val:
                    valid_anchor_rel = False
            if valid_anchor_rel:
                resolved_relationships.append(rel_copy)

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

            # Apply top-level scalar overrides (e.g. gender, morphology) that
            # apply_delta skips because they are not dicts.  User-supplied
            # values must always win over subject-preset defaults.
            for _scalar_key in ("gender", "morphology"):
                if _scalar_key in obj:
                    components[_scalar_key] = obj[_scalar_key]

            components = resolve_references(components, scene_objects, self.primitives_db)

            visible = filter_by_camera(components, camera_framing, pose_name, self.poses_db)

            gender = components.get("gender", obj.get("gender", "person"))
            subject_name = components.get("subject", obj.get("subject", ""))
            morphology = components.get("morphology", obj.get("morphology", {}))

            # Extract ensemble key for template-level attire rendering
            attire_key = components.get("attire")
            if not isinstance(attire_key, str):
                attire_key = None

            identity_frags = render_to_text(
                visible, render_profile_name,
                self.attribute_metadata_db,
                self.render_profiles_db, active_tone,
                self.jinja2_env,
                ensemble_key=attire_key,
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
                text = _render_jinja2_template(self.jinja2_env, "BodySurface.jinja2", feature)
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

        # Compute visible zones for relationship actor checks using camera framing zones directly.
        # This ensures actors without components can still participate in relationships
        # (e.g., a bare {"type": "human", "gender": "woman"} can still hold an object).
        all_visible = list(camera_framing_zones)
        placements = scene_data.get("placements", {})

        # Resolve environment data early for affordance queries and preposition derivation
        env_data = None
        for obj_id, obj in scene_objects.items():
            if obj.get("type") == "environment":
                env_data = obj
                break
        if env_data is None:
            env_data = scene_data.get("environment")

        env_resolved = None
        env_prep = "in"
        if env_data:
            if isinstance(env_data, str):
                env_data = {"type": env_data}
            env_type = env_data.get("template_key") or env_data.get("location") or env_data.get("type")
            if env_type:
                db_key = env_type
                if db_key not in self.environments_db and db_key.lower() in self.environments_db:
                    db_key = db_key.lower()
                env_resolved = self.environments_db.get(db_key, {})
                if env_resolved:
                    env_prep = derive_preposition(env_resolved, self.spatial_prepositions_db)

        rel_frags = apply_relationships(
            resolved_relationships, scene_objects, all_visible,
            self.actions_db, self.spatial_db, self.environments_db,
            placements, self.affordance_types_db, env_resolved,
            jinja2_env=self.jinja2_env,
        )
        all_fragments.extend(rel_frags)

        # Collect fixture IDs referenced by relationships
        relationship_target_ids = set()
        for rel in scene_data.get("relationships", []):
            for key in ("actor", "subject", "object", "target", "container"):
                val = rel.get(key)
                if val and isinstance(val, str):
                    relationship_target_ids.add(val)

        env_frags = apply_environment(
            scene_data, scene_objects,
            self.atmospheres_db, self.lighting_db,
            self.weather_db, self.composition_db,
            self.jinja2_env,
            relationship_target_ids=relationship_target_ids,
            atmosphere_db=self.atmosphere_db,
        )
        all_fragments.extend(env_frags)

        style_frags = apply_style_tone(scene_data, self.styles_db)
        all_fragments.extend(style_frags)

        max_frags = render_profile.get("max_fragments", 10)

        filtered = [f for f in all_fragments if any(t in include_tags for t in f.get("tags", []))]

        ZONE_TO_PHASE = {
            "_subject_type": ASSEMBLY_PHASES["subject_identity"],
            "Face": ASSEMBLY_PHASES["subject_identity"],
            "Hair": ASSEMBLY_PHASES["attire"],
            "Eyes": ASSEMBLY_PHASES["attire"],
            "Clothing": ASSEMBLY_PHASES["attire"],
            "body_config": ASSEMBLY_PHASES["posture"],
            "_pose": ASSEMBLY_PHASES["posture"],
            "pose": ASSEMBLY_PHASES["posture"],
            "relationship": ASSEMBLY_PHASES["figure_anchor"],
            "spatial": ASSEMBLY_PHASES["figure_anchor"],
            "environment": ASSEMBLY_PHASES["atmosphere"],
            "lighting": ASSEMBLY_PHASES["atmosphere"],
            "weather": ASSEMBLY_PHASES["atmosphere"],
            "style": ASSEMBLY_PHASES["style"],
            "composition": ASSEMBLY_PHASES["style"],
            "camera": ASSEMBLY_PHASES["style"],
        }
        for f in filtered:
            if "phase" not in f:
                f["phase"] = ZONE_TO_PHASE.get(f.get("zone", ""), 99)

        filtered.sort(key=lambda f: (
            f.get("phase", 99),
            f.get("chain_order", 0),
            -f.get("priority", 0),
            f.get("text", ""),
        ))
        filtered = filtered[:max_frags]

        env_label = ""
        ambient_fixtures = ""
        lighting_phrase = ""
        style_overlay = ""
        comp_text = ""
        for f in filtered:
            if f.get("zone") == "environment" and f.get("frag_type") == "environment":
                if f["text"].startswith("featuring "):
                    ambient_fixtures = f["text"]
                else:
                    env_label = f["text"]
            elif f.get("zone") == "lighting" or f.get("frag_type") == "lighting":
                lighting_phrase = f["text"]
            elif f.get("zone") == "style" or f.get("frag_type") == "style":
                style_overlay = f["text"]
            elif f.get("zone") == "composition" or f.get("frag_type") == "composition":
                comp_text = f["text"]
                
        if env_label and ambient_fixtures:
            env_label = f"{env_label}, {ambient_fixtures}"
        elif ambient_fixtures:
            env_label = ambient_fixtures

        # Determine the primary actor ID (first human/creature in objects)
        primary_actor_id = None
        for obj_id, obj in scene_objects.items():
            if obj.get("type") in ("human", "creature") or obj.get("subject"):
                primary_actor_id = obj_id
                break

        # Deduplicate fragments (Phase 4 backend safeguard)
        seen_frags = set()
        unique_filtered = []
        for f in filtered:
            key = (f.get("actor_id"), f.get("text"))
            if key not in seen_frags:
                seen_frags.add(key)
                unique_filtered.append(f)
        filtered = unique_filtered

        # Check if we should use the multi-actor flow
        narrative_mode = render_profile.get("narrative_mode", "fact_chain")
        if len(physical_ids) > 1:
            # Group fragments by actor_id
            actor_frags = defaultdict(list)
            global_frags = []
            for f in filtered:
                a_id = f.get("actor_id")
                if a_id in physical_ids:
                    actor_frags[a_id].append(f)
                else:
                    global_frags.append(f)
            
            descriptions = []
            for actor_id in physical_ids:
                frags = actor_frags[actor_id]
                desc = self._build_actor_description(actor_id, frags, scene_objects, narrative_mode)
                descriptions.append(desc)
                
            combined = self._combine_actor_descriptions(descriptions, scene_objects, scene_data, narrative_mode)
            
            # Add global action/relationship clauses
            global_clauses = []
            for f in global_frags:
                if f.get("frag_type") == "relationship":
                    clause = f.get("clause_text", f["text"])
                    if narrative_mode == "scene_description":
                        action_id = f.get("action_id", "")
                        clause = _to_finite(clause, action_id, self.action_grammar_db, "singular")
                    if clause and clause not in global_clauses:
                        global_clauses.append(clause)
            if global_clauses:
                if combined["action_phrase"]:
                    combined["action_phrase"] += ", " + ", ".join(global_clauses)
                else:
                    combined["action_phrase"] = ", ".join(global_clauses)
            clean_framing = CAMERA_FRAMING_MAP.get(camera.get("framing", ""), camera.get("framing", ""))
            
            # Gather non-interacted objects
            prop_phrases = self._collect_objects(scene_objects, scene_data.get("relationships", []), camera_framing_zones)
            
            # Rest of the multi-actor flow:
            # Gather background noise elements
            background_noise_phrases = []
            for obj_id, obj in scene_objects.items():
                if obj.get("type") == "background_noise":
                    label = obj.get("label") or obj.get("template_key") or obj_id
                    background_noise_phrases.append(label)
                    
            env_clause = ""
            if env_label:
                article = "an" if env_label[0].lower() in "aeiou" else "a"
                env_clause = f"{env_prep} {article} {env_label}"
                
            first_action = ""
            for d in descriptions:
                if d["action_clauses"]:
                    first_action = d["action_clauses"][0]
                    break
            if not first_action and global_clauses:
                first_action = global_clauses[0]
                
            # Get camera descriptor
            camera_text = ""
            if inject_camera_descriptor:
                state_desc = self.inject_camera_descriptor({"camera": camera, "scene_data": scene_data, "_inject_camera": inject_camera_descriptor})
                camera_text = state_desc.get("_camera_text", "")
                
            lead_subject = combined["subject_phrase"]
            if camera_text:
                subj_lower = combined["subject_phrase"]
                if subj_lower.startswith("A "):
                    subj_lower = "a " + subj_lower[2:]
                elif subj_lower.startswith("An "):
                    subj_lower = "an " + subj_lower[3:]
                else:
                    subj_lower = subj_lower[0].lower() + subj_lower[1:]
                cam_lower = camera_text[0].lower() + camera_text[1:] if camera_text else ""
                lead_subject = f"{cam_lower} {subj_lower}"
                    
            lead = output_formatter.format_lead_sentence(
                lead_subject,
                first_action,
                env_clause,
                lighting_phrase
            )
            if narrative_mode == "scene_description" and comp_text:
                if "cinematic" in comp_text:
                    suffix = ", shot in cinematic style"
                elif "over-the-shoulder" in comp_text:
                    suffix = ", shot in an over-the-shoulder style"
                else:
                    suffix = f", shot in {comp_text} style"
                if lead.endswith("."):
                    lead = lead[:-1] + suffix + "."
                else:
                    lead = lead + suffix + "."
            
            lines = [lead, ""]
            lines.append(f"Subject: {output_formatter._cap_sentence(combined['subject_phrase'])}")
            lines.append(f"Clothing: {combined['clothing_phrase']}")
            lines.append(f"Action: {combined['action_phrase']}")
            
            environment = output_formatter.format_environment_field(
                env_label, env_prep, background_noise_phrases
            )
            lines.append(f"Environment: {environment}")
            
            objects = output_formatter.format_objects_field(prop_phrases)
            if objects:
                lines.append(f"Objects: {objects}")
                
            lighting = output_formatter.format_lighting_field(lighting_phrase, "")
            lines.append(f"Lighting: {lighting}")
            
            camera_desc = output_formatter.format_camera_field(
                camera.get("shot_type", ""),
                camera.get("angle", ""),
                clean_framing,
                camera.get("depth_of_field", ""),
                camera.get("focus", "")
            )
            lines.append(f"Camera: {camera_desc}")
            
            style = output_formatter.format_style_field(
                style_overlay or render_profile.get("aesthetic", ""),
                render_profile.get("color_palette", ""),
                render_profile.get("quality", ""),
                scene_data.get("mood", "")
            )
            if style:
                lines.append(f"Style Details: {style}")
                
            return "\n".join(lines)

        # Collect categorized fragments for the first physical actor
        held_items = []
        accessories = []
        clothing_items = []
        posture_phrase = ""
        action_clauses = []
        identity_adjectives = []
        hair_phrase = ""
        subject_type = "person"
        actor_gender = "person"
        extra_identity_texts = []

        CLOTHING_ZONES = {"UpperBody", "LowerBody", "Feet"}
        ACCESSORY_ZONES = {"Hands", "Jewelry", "Accessories", "Headwear"}

        for f in filtered:
            zone = f.get("zone", "")
            frag_type = f.get("frag_type", "")
            tags = f.get("tags", [])

            if zone == "_subject_type":
                subject_type = f["text"]
                continue
            elif zone == "Hair":
                hair_phrase = f["text"]
            elif zone == "Face":
                identity_adjectives.append(f["text"])
            elif zone in CLOTHING_ZONES:
                clothing_items.append({"layer_order": f.get("priority", 50), "label": f["text"]})
            elif zone in ACCESSORY_ZONES:
                accessories.append(f["text"])
            elif frag_type == "relationship":
                clause = f.get("clause_text", f["text"])
                if clause not in action_clauses:
                    action_clauses.append(clause)
            elif zone in ("body_config", "_pose", "pose"):
                if posture_phrase:
                    posture_phrase += ", " + f["text"]
                else:
                    posture_phrase = f["text"]
            elif zone in ("Tusks", "Ears", "Jaw", "Eyes"):
                if f["text"] not in extra_identity_texts:
                    extra_identity_texts.append(f["text"])

        # Build subject phrase: "A [render_style] [expressions] [subject_type] with [hair] and [extra_identity]"
        adj_part = ", ".join(identity_adjectives) if identity_adjectives else ""
        subject_phrase_parts = []
        
        # Primary actor render_style
        primary_actor_obj = scene_objects.get(primary_actor_id, {})
        render_style = primary_actor_obj.get("render_style", "")
        if render_style:
            subject_phrase_parts.append(render_style)
            
        if adj_part:
            subject_phrase_parts.append(adj_part)
        subject_phrase_parts.append(subject_type)
        subject_phrase = " ".join(subject_phrase_parts)
        
        with_parts = []
        if hair_phrase:
            with_parts.append(hair_phrase)
        for extra in extra_identity_texts:
            with_parts.append(extra)
            
        if with_parts:
            subject_phrase += " with " + output_formatter._join_list(with_parts)

        # Get camera descriptor
        camera_text = ""
        if inject_camera_descriptor:
            state_desc = self.inject_camera_descriptor({"camera": camera, "scene_data": scene_data, "_inject_camera": inject_camera_descriptor})
            camera_text = state_desc.get("_camera_text", "")
            
        lead_subject = subject_phrase
        if camera_text:
            subj_lower = subject_phrase
            if subj_lower.startswith("A "):
                subj_lower = "a " + subj_lower[2:]
            elif subj_lower.startswith("An "):
                subj_lower = "an " + subj_lower[3:]
            else:
                subj_lower = subj_lower[0].lower() + subj_lower[1:]
            cam_lower = camera_text[0].lower() + camera_text[1:] if camera_text else ""
            lead_subject = f"{cam_lower} {subj_lower}"

        # Derive pronoun from subject type
        pronoun = "She"
        if subject_type == "man":
            pronoun = "He"
        elif subject_type not in ("woman",):
            pronoun = "They"

        if render_profile.get("narrative_mode") == "scene_description":
            rel_info = []
            for f in filtered:
                if f.get("frag_type") == "relationship":
                    clause = f.get("clause_text", f["text"])
                    rel_info.append((clause, f.get("chain_order", 99), f.get("action_id", "")))
            rel_info.sort(key=lambda x: x[1])
            if rel_info:
                first_clause, _, first_act_id = rel_info[0]
                number = "plural" if pronoun == "They" else "singular"
                finite_first = _to_finite(first_clause, first_act_id, self.action_grammar_db, number)
                
                chained_clauses = [finite_first]
                for clause, _, _ in rel_info[1:]:
                    chained_clauses.append(clause)
                action_clauses = [" ".join(chained_clauses)]
            else:
                action_clauses = []

        # Clean camera framing: "full_body" -> "full-body"
        clean_framing = CAMERA_FRAMING_MAP.get(camera.get("framing", ""), camera.get("framing", ""))

        # Gather non-interacted objects
        prop_phrases = self._collect_objects(scene_objects, scene_data.get("relationships", []), camera_framing_zones)

        # Gather background noise elements
        background_noise_phrases = []
        for obj_id, obj in scene_objects.items():
            if obj.get("type") == "background_noise":
                label = obj.get("label") or obj.get("template_key") or obj_id
                background_noise_phrases.append(label)

        return output_formatter.render_full_output({
            "subject_phrase": subject_phrase,
            "held_items": held_items,
            "accessories": accessories,
            "clothing_items": clothing_items,
            "posture_phrase": posture_phrase,
            "action_clauses": action_clauses,
            "env_label": env_label,
            "env_preposition": env_prep,
            "background_elements": background_noise_phrases,
            "scene_props": prop_phrases,
            "lighting_phrase": lighting_phrase,
            "weather_phrase": "",
            "shot_type": camera.get("shot_type", ""),
            "camera_angle": camera.get("angle", ""),
            "camera_framing": clean_framing,
            "depth_of_field": camera.get("depth_of_field", ""),
            "aesthetic": style_overlay or render_profile.get("aesthetic", ""),
            "color_palette": render_profile.get("color_palette", ""),
            "render_quality": render_profile.get("quality", ""),
            "mood": scene_data.get("mood", ""),
            "pronoun": pronoun,
            "focus": camera.get("focus", ""),
            "subject_phrase_injected": lead_subject,
            "comp_text": comp_text
        })


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





class RenderSystemWrapper:
    def __init__(self, profiles):
        self.profiles = profiles


class PromptCompiler(Assembler):
    def __init__(self, data_dir: str = None):
        super().__init__(data_dir=data_dir)
        self.render_system = RenderSystemWrapper(self.render_profiles_db)

    def compile_scene(self, scene_data: dict, strict: bool = False, inject_camera_descriptor: bool = True) -> str:
        output_format = scene_data.get("output_format", "labeled")
        return self.assemble(scene_data, strict=strict, inject_camera_descriptor=inject_camera_descriptor, output_format=output_format)


# ---------------------------------------------------------------------------
# Hair Ontology V2 Constants and Helper Functions
# ---------------------------------------------------------------------------

CURL_PATTERNS = {"straight", "wavy", "curly", "coily", "kinky"}
DENSITY_VALUES = {"thin", "medium", "thick"}
STRAND_VALUES = {"fine", "medium", "coarse"}
POROSITY_VALUES = {"low", "normal", "high"}

COLOR_TECHNIQUES = {
    "none", "balayage", "ombre", "sombre", "highlights", "lowlights",
    "money_piece", "babylights", "color_melt", "peekaboo",
    "root_smudge", "frosting", "dip_dye",
}
COLOR_VIBRANCY = {"natural", "fashion", "pastel", "neon"}
COLOR_PLACEMENT = {
    "all_over", "lengths_and_ends", "roots", "money_piece",
    "peekaboo", "underneath", "face_framing",
}

ARRANGEMENT_TYPES = {
    "loose", "down", "tousled",
    "ponytail", "half_up_half_down",
    "bun", "top_knot", "chignon", "ballerina_bun", "messy_bun", "donut_bun",
    "space_buns", "double_buns",
    "braid", "three_strand_braid", "french_braid", "dutch_braid",
    "fishtail_braid", "boxer_braids", "crown_braid",
    "double_dutch_braids", "triple_braid",
    "locs", "starter_locs", "traditional_locs", "freeform_locs", "sisterlocks",
    "twists", "two_strand_twists", "flat_twists", "senegalese_twists", "marley_twists",
    "box_braids", "knotless_braids", "cornrows", "faux_locs",
    "protective_style",
}

ARRANGEMENT_POSITIONS = {"high", "mid", "low", "side", "nape", "top", "crown"}

SHEEN_VALUES = {"matte", "natural", "silky", "glossy"}
CONDITION_VALUES = {"healthy", "dry", "damaged", "chemically_treated", "freshly_cut"}

HAIR_STATES = {
    "wet", "dry", "frizzy", "flat", "static", "humidity_affected",
    "freshly_washed", "second_day", "heat_styled", "air_dried",
    "windblown", "tousled", "messy", "freshly_done", "bed_head",
}

CULTURAL_STYLE_TYPES = {"locs", "twists", "protective_style", "natural", "treated"}
CULTURAL_SUBTYPES = {
    "starter", "traditional", "freeform", "sisterlocks", "comb_coils",
    "two_strand", "flat", "senegalese", "marley",
    "box_braids", "knotless_braids", "cornrows", "faux_locs", "goddess_locs",
    "wash_and_go", "twist_out", "braid_out", "bantu_knots", "puff",
}
CULTURAL_STAGES = {"new", "mature", "growing"}
CULTURAL_TREATMENTS = {"rebonded", "permed", "straightened", "relaxed", "texturized"}

HAIR_REGIONS = {"front", "back", "sides", "bangs"}


def _is_arrangement_type(val: str) -> bool:
    return val.lower().replace(" ", "_").replace("-", "_") in ARRANGEMENT_TYPES


def normalize_hair(raw: dict) -> dict:
    has_new_keys = any(k in raw for k in ("texture", "arrangement", "appearance", "cultural"))
    has_prev_new_keys = any(k in raw for k in ("structure",))

    if has_new_keys or has_prev_new_keys:
        ontology = _normalize_new_format(raw)
    else:
        ontology = _normalize_old_format(raw)

    if "regions" not in ontology:
        ontology["regions"] = {r: True for r in HAIR_REGIONS}

    return ontology


def _normalize_new_format(raw: dict) -> dict:
    ontology = {}

    texture = raw.get("texture", {})
    structure = raw.get("structure", {})
    if isinstance(texture, dict):
        ontology["texture"] = {
            "curl_pattern": texture.get("curl_pattern", "") or structure.get("shape", ""),
            "density": texture.get("density", ""),
            "strand": texture.get("strand", ""),
            "porosity": texture.get("porosity", ""),
        }
    else:
        ontology["texture"] = {
            "curl_pattern": structure.get("shape", ""),
            "density": "",
            "strand": "",
            "porosity": "",
        }

    color = raw.get("color", {})
    appearance = raw.get("appearance", {})
    if isinstance(color, str):
        ontology["color"] = {"base": color, "technique": "none", "secondary": "", "placement": "all_over", "vibrancy": "natural"}
    elif isinstance(color, dict) and color.get("base"):
        ontology["color"] = {
            "base": color.get("base", ""),
            "technique": color.get("technique", "none"),
            "secondary": color.get("secondary", ""),
            "placement": color.get("placement", "all_over"),
            "vibrancy": color.get("vibrancy", "natural"),
        }
    elif isinstance(appearance, dict) and appearance.get("color"):
        ontology["color"] = {"base": appearance["color"], "technique": "none", "secondary": "", "placement": "all_over", "vibrancy": "natural"}
    else:
        ontology["color"] = {"base": "", "technique": "none", "secondary": "", "placement": "all_over", "vibrancy": "natural"}

    arrangement = raw.get("arrangement", {})
    if isinstance(arrangement, str):
        ontology["arrangement"] = {
            "primary": {"type": arrangement, "position": "", "subtype": "", "length": structure.get("length", ""), "thickness": ""},
            "secondary": "",
            "accessories": [],
        }
    elif isinstance(arrangement, dict):
        primary = arrangement.get("primary", arrangement)
        if isinstance(primary, str):
            primary = {"type": primary, "position": "", "subtype": "", "length": "", "thickness": ""}
        ontology["arrangement"] = {
            "primary": {
                "type": primary.get("type", "loose"),
                "position": primary.get("position", ""),
                "subtype": primary.get("subtype", ""),
                "length": primary.get("length", "") or structure.get("length", ""),
                "thickness": primary.get("thickness", ""),
            },
            "secondary": arrangement.get("secondary", ""),
            "accessories": arrangement.get("accessories", []),
        }
    else:
        ontology["arrangement"] = {
            "primary": {"type": "loose", "position": "", "subtype": "", "length": structure.get("length", ""), "thickness": ""},
            "secondary": "",
            "accessories": [],
        }

    if isinstance(appearance, dict):
        ontology["appearance"] = {
            "sheen": appearance.get("sheen", "") or appearance.get("texture", ""),
            "condition": appearance.get("condition", ""),
        }
    else:
        ontology["appearance"] = {"sheen": "", "condition": ""}

    state = raw.get("state", [])
    if isinstance(state, str):
        state = [state]
    ontology["state"] = state

    cultural = raw.get("cultural", {})
    if isinstance(cultural, dict):
        ontology["cultural"] = {
            "style_type": cultural.get("style_type", ""),
            "subtype": cultural.get("subtype", ""),
            "stage": cultural.get("stage", ""),
            "treatment": cultural.get("treatment", ""),
        }
    else:
        ontology["cultural"] = {"style_type": "", "subtype": "", "stage": "", "treatment": ""}

    _backfill_from_legacy(ontology, raw)

    return ontology


def _normalize_old_format(raw: dict) -> dict:
    style = raw.get("style", "")

    if _is_arrangement_type(style):
        arr_type = style
        curl_pattern = ""
    elif style.lower() in CURL_PATTERNS:
        arr_type = "loose"
        curl_pattern = style
    else:
        arr_type = "loose"
        curl_pattern = style

    ontology = {
        "texture": {
            "curl_pattern": curl_pattern,
            "density": raw.get("density", ""),
            "strand": raw.get("strand", raw.get("strand_thickness", "")),
            "porosity": raw.get("porosity", ""),
        },
        "color": {
            "base": raw.get("color", ""),
            "technique": raw.get("technique", "none"),
            "secondary": raw.get("secondary_color", ""),
            "placement": raw.get("placement", "all_over"),
            "vibrancy": raw.get("vibrancy", "natural"),
        },
        "arrangement": {
            "primary": {
                "type": arr_type,
                "position": raw.get("position", ""),
                "subtype": raw.get("subtype", ""),
                "length": raw.get("length", ""),
                "thickness": raw.get("thickness", ""),
            },
            "secondary": raw.get("half_up", ""),
            "accessories": raw.get("accessories", []),
        },
        "appearance": {
            "sheen": raw.get("sheen", raw.get("texture", "")),
            "condition": raw.get("condition", ""),
        },
        "state": raw.get("state", []),
        "cultural": {
            "style_type": raw.get("style_type", ""),
            "subtype": raw.get("cultural_subtype", ""),
            "stage": raw.get("stage", ""),
            "treatment": raw.get("treatment", ""),
        },
        "regions": {r: True for r in HAIR_REGIONS},
    }

    return ontology


def _backfill_from_legacy(ontology: dict, raw: dict) -> None:
    tex = ontology["texture"]
    if not tex["curl_pattern"] and "style" in raw:
        if raw["style"].lower() in CURL_PATTERNS:
            tex["curl_pattern"] = raw["style"]
    if not tex["density"] and "density" in raw:
        tex["density"] = raw["density"]
    if not tex["strand"] and "strand" in raw:
        tex["strand"] = raw["strand"]
    if not tex["strand"] and "strand_thickness" in raw:
        tex["strand"] = raw["strand_thickness"]

    col = ontology["color"]
    if not col["base"] and "color" in raw:
        col["base"] = raw["color"] if isinstance(raw["color"], str) else ""
    if col["technique"] == "none" and "technique" in raw:
        col["technique"] = raw["technique"]
    if not col["secondary"] and "secondary_color" in raw:
        col["secondary"] = raw["secondary_color"]

    arr = ontology["arrangement"]["primary"]
    if arr["type"] == "loose" and "style" in raw:
        if _is_arrangement_type(raw["style"]):
            arr["type"] = raw["style"]
    if not arr["length"] and "length" in raw:
        arr["length"] = raw["length"]
    if not arr["position"] and "position" in raw:
        arr["position"] = raw["position"]

    app = ontology["appearance"]
    if not app["sheen"]:
        if "texture" in raw and isinstance(raw["texture"], str):
            app["sheen"] = raw["texture"]
        elif "sheen" in raw:
            app["sheen"] = raw["sheen"]


def render_hair(ontology: dict) -> str:
    parts = []

    state = ontology.get("state", [])
    if isinstance(state, str):
        state = [state]
    parts.extend(state)

    arrangement = ontology.get("arrangement", {})
    if isinstance(arrangement, dict):
        primary = arrangement.get("primary", {})
        if isinstance(primary, dict):
            length = primary.get("length", "")
            if length:
                parts.append(length)

    texture = ontology.get("texture", {})
    if isinstance(texture, dict):
        curl = texture.get("curl_pattern", "")
        if curl and curl not in parts:
            parts.append(curl)

    color = ontology.get("color", {})
    if isinstance(color, dict):
        color_str = _render_color(color)
        if color_str:
            parts.append(color_str)

    appearance = ontology.get("appearance", {})
    if isinstance(appearance, dict):
        sheen = appearance.get("sheen", "")
        if sheen and sheen not in ("natural", ""):
            parts.append(sheen)

    base = " ".join(p for p in parts if p) + " hair" if parts else "hair"

    if isinstance(arrangement, dict):
        primary = arrangement.get("primary", {})
        if isinstance(primary, dict):
            arr_type = primary.get("type", "loose")
            if arr_type and arr_type not in ("loose", "down"):
                base = f"{arr_type.replace('_', ' ')} of {base}"

            accessories = arrangement.get("accessories", [])
            if accessories:
                acc_str = " with " + ", ".join(accessories)
                base = base + acc_str

    return base


def _render_color(color: dict) -> str:
    base = color.get("base", "")
    technique = color.get("technique", "none")
    secondary = color.get("secondary", "")
    vibrancy = color.get("vibrancy", "natural")

    prefix = ""
    if vibrancy in ("fashion", "pastel", "neon"):
        prefix = f"{vibrancy} " if vibrancy != "fashion" else ""

    if technique == "none" or not technique:
        return f"{prefix}{base}".strip() if base else ""

    if technique in ("balayage", "ombre", "sombre") and secondary:
        return f"{prefix}{base} {technique} with {secondary}".strip()
    elif technique in ("highlights", "lowlights", "babylights") and secondary:
        return f"{prefix}{secondary} {technique} on {base}".strip()
    elif technique == "money_piece" and secondary:
        return f"{prefix}{base} with {secondary} money piece".strip()
    elif technique == "peekaboo" and secondary:
        return f"{prefix}{base} with {secondary} peekaboo".strip()
    elif technique == "color_melt" and secondary:
        return f"{prefix}{base} to {secondary} color melt".strip()
    else:
        return f"{prefix}{base}".strip() if base else ""
