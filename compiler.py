"""
prompt-engine/compiler.py
Object-Oriented Prompt Composition System — Stages 1-6 + Architecture Polish
"""
import os
import json
import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Shared utility
# ---------------------------------------------------------------------------

def safe_format(template_str, context: dict) -> str:
    """Format a template string or slot descriptor, replacing missing keys with empty string
    and collapsing any resulting multi-spaces."""
    # Resolve tone from context only (no global state)
    tone = context.get("_tone", "default")

    def resolve_tone_value(val):
        if isinstance(val, dict):
            # Check if this is a tone map or singular/plural verb map
            if "singular" in val or "plural" in val:
                return val
            if any(k in val for k in ("default", "poetic", "vivid", "concise", "technical")):
                return val.get(tone) or val.get("default") or ""
        return val

    def adjust_articles(text: str) -> str:
        # Convert 'a' to 'an' before vowels
        text = re.sub(r"\b([aA])\s+([aeiouAEIOU][a-zA-Z]*)", lambda m: m.group(1) + "n " + m.group(2), text)
        # Convert 'an' to 'a' before consonants
        text = re.sub(r"\b([aA])n\s+([^aeiouAEIOU\s][a-zA-Z]*)", lambda m: m.group(1) + " " + m.group(2), text)
        return text

    STANDARD_RANKS = {
        "quantity": 1,
        "opinion": 2,
        "expression": 2,
        "fit": 3,
        "length": 3,
        "size": 3,
        "shape": 4,
        "style": 4,
        "species": 4,
        "age": 5,
        "color": 6,
        "origin": 7,
        "pattern": 8,
        "material": 8
    }

    # Resolve tone on the template itself if it's a tone map string
    template_str = resolve_tone_value(template_str)

    if isinstance(template_str, dict):
        head = template_str.get("head", "")
        head = resolve_tone_value(head)
        
        # Resolve head if it's a dict containing singular/plural
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
            # Apply noun pluralization rules if _plural_self is true
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
                # Resolve context placeholders in suffix (e.g. {_possessive})
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
# Core data structures
# ---------------------------------------------------------------------------

@dataclass
class CandidateFragment:
    zone: str
    frag_type: str          # "native" | "owned_item" | "relationship" | "environment" | "lighting" | "weather" | "composition" | "body_surface"
    tags: list
    priority: int
    text: str
    clause_text: str = ""
    actor_id: str = ""
    chain_order: int = 99


@dataclass
class ValidationError:
    severity: str           # "error" | "warning"
    message: str


class SceneObject:
    def __init__(self, obj_id: str, obj_type: str, data: dict):
        self.id = obj_id
        self.type = obj_type
        self.components: dict = {k: v for k, v in data.items() if k not in ("type", "id")}

    def get_component(self, name: str, default=None):
        return self.components.get(name, default)


# ---------------------------------------------------------------------------
# System: WardrobeSystem
# ---------------------------------------------------------------------------

class WardrobeSystem:
    """Resolves attire bundles on human SceneObjects."""

    def __init__(self, attires_db: dict):
        self.attires = attires_db

    def resolve(self, human_obj: SceneObject, scene_objects: dict) -> None:
        attire_name = human_obj.get_component("attire")
        if not attire_name or attire_name not in self.attires:
            return

        attire_data = self.attires[attire_name]
        for slot, slot_data in attire_data.items():
            existing_slot = human_obj.get_component(slot)
            if existing_slot is None:
                existing_slot = {}
                human_obj.components[slot] = existing_slot
            elif not isinstance(existing_slot, dict):
                continue

            # Explicit attire always overrides existing clothing references
            existing_slot["owned_item_id"] = slot_data.get("owned_item_id")

            owned_item_id = existing_slot.get("owned_item_id")
            if owned_item_id:
                base = owned_item_id
                if "_" in base:
                    parts = base.split("_")
                    if parts[-1].isdigit():
                        parts = parts[:-1]
                    base = "_".join(parts)
                template_key = "".join(word.capitalize() for word in base.split("_"))

                if owned_item_id not in scene_objects:
                    default_data = {
                        "type": "clothing",
                        "template_key": template_key
                    }
                    scene_objects[owned_item_id] = SceneObject(owned_item_id, "clothing", default_data)
                else:
                    existing_obj = scene_objects[owned_item_id]
                    if not existing_obj.type:
                        existing_obj.type = "clothing"
                    if "template_key" not in existing_obj.components:
                        existing_obj.components["template_key"] = template_key


# ---------------------------------------------------------------------------
# System: SubjectSystem
# ---------------------------------------------------------------------------

class SubjectSystem:
    """Merges subject defaults into a human SceneObject."""

    def __init__(self, subjects_db: dict):
        self.subjects = subjects_db

    def resolve(self, human_obj: SceneObject) -> SceneObject:
        subject_name = human_obj.get_component("subject")
        if not subject_name or subject_name not in self.subjects:
            return human_obj

        subject_data = self.subjects[subject_name]
        for comp_key, comp_val in subject_data.items():
            if comp_key in ("type",):
                continue
            existing = human_obj.get_component(comp_key)
            if isinstance(existing, dict) and isinstance(comp_val, dict):
                merged = dict(comp_val)       # subject defaults first
                merged.update(existing)       # scene overrides win
                human_obj.components[comp_key] = merged
            elif existing is None:
                human_obj.components[comp_key] = comp_val

        if "gender" not in human_obj.components and "gender" in subject_data:
            human_obj.components["gender"] = subject_data["gender"]

        return human_obj


# ---------------------------------------------------------------------------
# System: VisibilitySystem
# ---------------------------------------------------------------------------

class VisibilitySystem:
    """Resolves active body zones from camera framing + pose occlusion.
    
    Supports two modes:
    1. Legacy: hardcoded CAMERA_ZONES dict (backward compatible)
    2. Data-driven: components declare visibility_tags (new morphology support)
    """

    # Default tags when component doesn't specify visibility_tags
    DEFAULT_VISIBILITY_TAGS = ["close_up", "medium", "full_body"]

    # Legacy CAMERA_ZONES kept as fallback for backward compatibility
    CAMERA_ZONES = {
        "close_up":  ["Face", "Hair", "Eyes", "Headwear"],
        "medium":    ["Face", "Hair", "Eyes", "Headwear", "UpperBody", "Hands"],
        "full_body": ["Face", "Hair", "Eyes", "Headwear", "UpperBody", "Hands", "LowerBody", "Feet"],
    }

    def __init__(self, poses_db: dict):
        self.poses = poses_db

    def compute_visible_zones(self, camera_framing: str, pose_name: Optional[str],
                               scene_objects: dict = None) -> list:
        """Compute visible zones from camera framing + component visibility_tags.
        
        Args:
            camera_framing: Camera framing string (close_up, medium, full_body)
            pose_name: Optional pose name for occlusion
            scene_objects: Optional dict of scene objects for data-driven visibility
        """
        if scene_objects:
            # Data-driven visibility from components
            zones = self._compute_zones_from_components(camera_framing, scene_objects)
        else:
            # Legacy: use hardcoded CAMERA_ZONES
            zones = list(self.CAMERA_ZONES.get(camera_framing, self.CAMERA_ZONES["full_body"]))

        # Apply pose occlusion
        if pose_name and pose_name in self.poses:
            for hz in self.poses[pose_name].get("hidden_zones", []):
                if hz in zones:
                    zones.remove(hz)
        return zones

    def _compute_zones_from_components(self, camera_framing: str,
                                        scene_objects: dict) -> list:
        """Compute zones from component visibility_tags."""
        # Start with legacy CAMERA_ZONES for backward compatibility
        legacy_zones = set(self.CAMERA_ZONES.get(camera_framing, self.CAMERA_ZONES["full_body"]))
        
        # Add any new zones from components with explicit visibility_tags
        for obj in scene_objects.values():
            if not self._is_physical(obj):
                continue
            for zone_name, zone_data in obj.components.items():
                if not isinstance(zone_data, dict):
                    continue
                # Only process components with explicit visibility_tags
                if "visibility_tags" in zone_data:
                    tags = zone_data["visibility_tags"]
                    if camera_framing in tags:
                        legacy_zones.add(zone_name)
        
        return list(legacy_zones)

    def _is_physical(self, obj: 'SceneObject') -> bool:
        """Check if object has physical form (subject, morphology, or human type)."""
        return bool(
            obj.get_component("subject") or 
            obj.get_component("morphology") or
            obj.type == "human"
        )


# ---------------------------------------------------------------------------
# System: AttributeCollectorSystem
# ---------------------------------------------------------------------------

class AttributeCollectorSystem:
    """Walks visible zones of a physical object and emits CandidateFragments."""

    def __init__(self, metadata_db: dict, templates_db: dict):
        self.metadata = metadata_db
        self.templates = templates_db
        self.hair_ontology = HairOntologySystem()

    def collect(
        self,
        human_obj: SceneObject,
        scene_objects: dict,
        visible_zones: list,
        priority_fn,
        active_tone: str = "default",
    ) -> list:
        candidates = []
        human_id = human_obj.id
        gender = human_obj.get_component("gender", "person")

        for zone in visible_zones:
            zone_data = human_obj.get_component(zone)
            if not zone_data:
                continue

            owned_item_id = zone_data.get("owned_item_id") if isinstance(zone_data, dict) else None
            if owned_item_id:
                owned_item = scene_objects.get(owned_item_id)
                if not owned_item:
                    continue
                meta = self.metadata.get(owned_item.type, {"tags": [], "priority": 50})
                template = self.templates.get(owned_item.get_component("template_key"))
                if template:
                    candidates.append(CandidateFragment(
                        zone=zone,
                        frag_type="owned_item",
                        tags=meta.get("tags", []),
                        priority=priority_fn(meta.get("priority", 50), [human_id, owned_item_id]),
                        text=safe_format(template, {**owned_item.components, "_tone": active_tone}),
                        actor_id=human_id,
                    ))
            else:
                # Get metadata key from zone_data or derive from zone name
                meta_key = self._get_metadata_key(zone, zone_data)
                meta = self.metadata.get(meta_key, {"tags": [], "priority": 50})

                # Get render priority from zone_data or use default
                render_priority = self._get_render_priority(zone, zone_data)

                # Hair zone uses ontology renderer instead of flat template
                if zone == "Hair":
                    ontology = self.hair_ontology.normalize(zone_data)
                    text = self.hair_ontology.render(ontology)
                    if text:
                        candidates.append(CandidateFragment(
                            zone=zone,
                            frag_type="native",
                            tags=meta.get("tags", []),
                            priority=priority_fn(render_priority, [human_id]),
                            text=text,
                            actor_id=human_id,
                        ))
                else:
                    # Try template first, then generic fallback
                    template = self.templates.get(zone)
                    if template:
                        ctx = {**zone_data, "gender": gender, "_tone": active_tone}
                        text = safe_format(template, ctx)
                    else:
                        # Generic fallback rendering
                        text = self._render_generic_zone(zone, zone_data)
                    
                    if text:
                        candidates.append(CandidateFragment(
                            zone=zone,
                            frag_type="native",
                            tags=meta.get("tags", []),
                            priority=priority_fn(render_priority, [human_id]),
                            text=text,
                            actor_id=human_id,
                        ))

        # Body surface features (tattoos, scars, freckles, etc.)
        # Determine which zones are covered by clothing that suppresses body surface
        covered_zones = set()
        for zone in visible_zones:
            zone_data = human_obj.get_component(zone)
            if zone_data and isinstance(zone_data, dict) and zone_data.get("owned_item_id"):
                # Check zone metadata for coverage flag
                zone_meta = self.metadata.get(zone.lower(), {})
                if zone_meta.get("covers_body_surface"):
                    covered_zones.add(zone)

        bsf = human_obj.get_component("body_surface_features") or []
        for feature in bsf:
            loc = feature.get("location", "")
            if loc not in visible_zones:
                continue
            if loc in covered_zones:
                continue
            bs_meta = self.metadata.get("body_surface", {"tags": [], "priority": 50})
            template = self.templates.get("BodySurface")
            if template:
                text = safe_format(template, {**feature, "_tone": active_tone})
                candidates.append(CandidateFragment(
                    zone=loc,
                    frag_type="body_surface",
                    tags=bs_meta.get("tags", []),
                    priority=priority_fn(bs_meta.get("priority", 50), [human_id]),
                    text=text,
                    actor_id=human_id,
                ))

        return candidates

    def _get_metadata_key(self, zone: str, zone_data) -> str:
        """Derive metadata key from zone name and data."""
        # Check if zone_data specifies a metadata_key
        if isinstance(zone_data, dict) and "metadata_key" in zone_data:
            return zone_data["metadata_key"]
        
        # Legacy mapping for backward compatibility
        LEGACY_META_KEYS = {
            "Face": "expression",
            "Hair": "hair",
        }
        if zone in LEGACY_META_KEYS:
            return LEGACY_META_KEYS[zone]
        
        # Fallback: use zone name lowercased
        return zone.lower()

    def _get_render_priority(self, zone: str, zone_data) -> int:
        """Get render priority from zone data or default."""
        if isinstance(zone_data, dict) and "render_priority" in zone_data:
            return zone_data["render_priority"]
        
        # Default priorities
        DEFAULT_PRIORITIES = {
            "Face": 100, "Hair": 90, "Eyes": 85, "Headwear": 80,
            "UpperBody": 70, "LowerBody": 65, "Feet": 60, "Hands": 55,
        }
        return DEFAULT_PRIORITIES.get(zone, 50)

    def _render_generic_zone(self, zone: str, zone_data) -> str:
        """Generic fallback: render zone as key-value pairs."""
        if not isinstance(zone_data, dict):
            return ""
        
        # Skip meta keys
        META_KEYS = {"visibility_tags", "render_priority", "render_group", "metadata_key", "renderer"}
        
        parts = []
        for key, value in zone_data.items():
            if key in META_KEYS:
                continue
            if isinstance(value, dict):
                # Nested dict: render each key-value
                for k, v in value.items():
                    parts.append(f"{v} {k}")
            else:
                # Simple value: render as "value zone" or just "value"
                if zone.lower() in key.lower():
                    parts.append(str(value))
                else:
                    parts.append(f"{value} {key.lower()}")
        
        return " ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# System: HairOntologySystem
# ---------------------------------------------------------------------------

# --- Texture: physical hair properties ---
CURL_PATTERNS = {"straight", "wavy", "curly", "coily", "kinky"}
DENSITY_VALUES = {"thin", "medium", "thick"}
STRAND_VALUES = {"fine", "medium", "coarse"}
POROSITY_VALUES = {"low", "normal", "high"}

# --- Color: technique-aware structure ---
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

# --- Arrangement: typed hierarchy ---
ARRANGEMENT_TYPES = {
    # Loose / simple
    "loose", "down", "tousled",
    # Tied
    "ponytail", "half_up_half_down",
    # Buns
    "bun", "top_knot", "chignon", "ballerina_bun", "messy_bun", "donut_bun",
    "space_buns", "double_buns",
    # Braids
    "braid", "three_strand_braid", "french_braid", "dutch_braid",
    "fishtail_braid", "boxer_braids", "crown_braid",
    "double_dutch_braids", "triple_braid",
    # Cultural / textured
    "locs", "starter_locs", "traditional_locs", "freeform_locs", "sisterlocks",
    "twists", "two_strand_twists", "flat_twists", "senegalese_twists", "marley_twists",
    "box_braids", "knotless_braids", "cornrows", "faux_locs",
    "protective_style",
}

ARRANGEMENT_POSITIONS = {"high", "mid", "low", "side", "nape", "top", "crown"}

# --- Appearance: visual qualities ---
SHEEN_VALUES = {"matte", "natural", "silky", "glossy"}
CONDITION_VALUES = {"healthy", "dry", "damaged", "chemically_treated", "freshly_cut"}

# --- State: temporary conditions ---
HAIR_STATES = {
    "wet", "dry", "frizzy", "flat", "static", "humidity_affected",
    "freshly_washed", "second_day", "heat_styled", "air_dried",
    "windblown", "tousled", "messy", "freshly_done", "bed_head",
}

# --- Cultural specificity ---
CULTURAL_STYLE_TYPES = {"locs", "twists", "protective_style", "natural", "treated"}
CULTURAL_SUBTYPES = {
    # Locs
    "starter", "traditional", "freeform", "sisterlocks", "comb_coils",
    # Twists
    "two_strand", "flat", "senegalese", "marley",
    # Protective
    "box_braids", "knotless_braids", "cornrows", "faux_locs", "goddess_locs",
    # Natural
    "wash_and_go", "twist_out", "braid_out", "bantu_knots", "puff",
}
CULTURAL_STAGES = {"new", "mature", "growing"}
CULTURAL_TREATMENTS = {"rebonded", "permed", "straightened", "relaxed", "texturized"}

# Hair regions scaffold
HAIR_REGIONS = {"front", "back", "sides", "bangs"}


def _is_arrangement_type(val: str) -> bool:
    """Check if a value is a known arrangement type."""
    return val.lower().replace(" ", "_").replace("-", "_") in ARRANGEMENT_TYPES


def normalize_hair(raw: dict) -> dict:
    """Normalize old flat format or new structured format to ontology schema.

    Old format: {"color": "brown", "length": "long", "style": "wavy"}
    Previous new format: {"structure": {...}, "appearance": {...}}
    Current new format: {"texture": {...}, "color": {...}, "arrangement": {...}, ...}
    """
    # Check if already in new format (any new key present)
    has_new_keys = any(k in raw for k in ("texture", "arrangement", "appearance", "cultural"))
    has_prev_new_keys = any(k in raw for k in ("structure",))

    if has_new_keys or has_prev_new_keys:
        ontology = _normalize_new_format(raw)
    else:
        ontology = _normalize_old_format(raw)

    # Ensure regions scaffold
    if "regions" not in ontology:
        ontology["regions"] = {r: True for r in HAIR_REGIONS}

    return ontology


def _normalize_new_format(raw: dict) -> dict:
    """Handle partial new-format input, merging with old keys for compatibility.

    Supports both:
    - Previous new format: {"structure": {length, shape}, "appearance": {color, texture}}
    - Current new format: {"texture": {curl_pattern, ...}, "color": {base, ...}, ...}
    """
    ontology = {}

    # Texture (physical properties)
    # Support old "structure" format as well
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

    # Color (technique-aware structure)
    # Support old "appearance.color" format
    color = raw.get("color", {})
    appearance = raw.get("appearance", {})
    if isinstance(color, str):
        ontology["color"] = {"base": color, "technique": "none", "secondary": "", "placement": "all_over", "vibrancy": "natural"}
    elif isinstance(color, dict) and color.get("base"):
        # New format with structured color
        ontology["color"] = {
            "base": color.get("base", ""),
            "technique": color.get("technique", "none"),
            "secondary": color.get("secondary", ""),
            "placement": color.get("placement", "all_over"),
            "vibrancy": color.get("vibrancy", "natural"),
        }
    elif isinstance(appearance, dict) and appearance.get("color"):
        # Old format: appearance.color
        ontology["color"] = {"base": appearance["color"], "technique": "none", "secondary": "", "placement": "all_over", "vibrancy": "natural"}
    else:
        ontology["color"] = {"base": "", "technique": "none", "secondary": "", "placement": "all_over", "vibrancy": "natural"}

    # Arrangement (typed hierarchy)
    # Support old "structure.length" for length
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

    # Appearance (visual qualities)
    # Support old "appearance.texture" -> sheen
    if isinstance(appearance, dict):
        ontology["appearance"] = {
            "sheen": appearance.get("sheen", "") or appearance.get("texture", ""),
            "condition": appearance.get("condition", ""),
        }
    else:
        ontology["appearance"] = {"sheen": "", "condition": ""}

    # State (temporary conditions)
    state = raw.get("state", [])
    if isinstance(state, str):
        state = [state]
    ontology["state"] = state

    # Cultural specificity
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

    # Fill in from old-format keys for backward compat
    _backfill_from_legacy(ontology, raw)

    return ontology


def _normalize_old_format(raw: dict) -> dict:
    """Convert old flat {color, length, style, texture} to new ontology."""
    style = raw.get("style", "")

    # Classify style: is it an arrangement or a curl pattern?
    if _is_arrangement_type(style):
        arr_type = style
        curl_pattern = ""
    elif style.lower() in CURL_PATTERNS:
        arr_type = "loose"
        curl_pattern = style
    else:
        arr_type = "loose"
        curl_pattern = style  # preserve unknown values

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
            "sheen": raw.get("sheen", raw.get("texture", "")),  # old "texture" -> sheen
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
    """Fill in new-format fields from old-format keys for partial new input."""
    # If texture is empty but old keys exist
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

    # Color backfill
    col = ontology["color"]
    if not col["base"] and "color" in raw:
        col["base"] = raw["color"] if isinstance(raw["color"], str) else ""
    if col["technique"] == "none" and "technique" in raw:
        col["technique"] = raw["technique"]
    if not col["secondary"] and "secondary_color" in raw:
        col["secondary"] = raw["secondary_color"]

    # Arrangement backfill
    arr = ontology["arrangement"]["primary"]
    if arr["type"] == "loose" and "style" in raw:
        if _is_arrangement_type(raw["style"]):
            arr["type"] = raw["style"]
    if not arr["length"] and "length" in raw:
        arr["length"] = raw["length"]
    if not arr["position"] and "position" in raw:
        arr["position"] = raw["position"]

    # Appearance backfill
    app = ontology["appearance"]
    if not app["sheen"]:
        if "texture" in raw and isinstance(raw["texture"], str):
            app["sheen"] = raw["texture"]
        elif "sheen" in raw:
            app["sheen"] = raw["sheen"]


def render_hair(ontology: dict) -> str:
    """Render structured hair ontology to a natural language phrase.

    Rendering order: state + length + curl_pattern + color + sheen + hair
    Arrangement modifies: "ponytail of ... hair"
    """
    parts = []

    # --- State words first (wet, windblown, frizzy, etc.) ---
    state = ontology.get("state", [])
    if isinstance(state, str):
        state = [state]
    parts.extend(state)

    # --- Length (from arrangement.primary.length) ---
    arrangement = ontology.get("arrangement", {})
    if isinstance(arrangement, dict):
        primary = arrangement.get("primary", {})
        if isinstance(primary, dict):
            length = primary.get("length", "")
            if length:
                parts.append(length)

    # --- Texture (curl pattern only for rendering) ---
    texture = ontology.get("texture", {})
    if isinstance(texture, dict):
        curl = texture.get("curl_pattern", "")
        if curl and curl not in parts:
            parts.append(curl)

    # --- Color ---
    color = ontology.get("color", {})
    if isinstance(color, dict):
        color_str = _render_color(color)
        if color_str:
            parts.append(color_str)

    # --- Appearance (sheen only; condition is structural detail) ---
    appearance = ontology.get("appearance", {})
    if isinstance(appearance, dict):
        sheen = appearance.get("sheen", "")
        if sheen and sheen not in ("natural", ""):
            parts.append(sheen)

    # --- Build base phrase ---
    base = " ".join(p for p in parts if p) + " hair" if parts else "hair"

    # --- Arrangement modifies construction ---
    if isinstance(arrangement, dict):
        primary = arrangement.get("primary", {})
        if isinstance(primary, dict):
            arr_type = primary.get("type", "loose")
            if arr_type and arr_type not in ("loose", "down"):
                base = f"{arr_type} of {base}"

            # Accessories append
            accessories = arrangement.get("accessories", [])
            if accessories:
                acc_str = " with " + ", ".join(accessories)
                base = base + acc_str

    return base


def _render_color(color: dict) -> str:
    """Render color structure to a natural language phrase."""
    base = color.get("base", "")
    technique = color.get("technique", "none")
    secondary = color.get("secondary", "")
    vibrancy = color.get("vibrancy", "natural")

    # Fashion/pastel/neon prefix
    prefix = ""
    if vibrancy in ("fashion", "pastel", "neon"):
        prefix = f"{vibrancy} " if vibrancy != "fashion" else ""

    if technique == "none" or not technique:
        return f"{prefix}{base}".strip() if base else ""

    # Technique-based rendering
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


class HairOntologySystem:
    """Normalizes hair data from any format and renders structured hair description."""

    CURL_PATTERNS = CURL_PATTERNS
    DENSITY_VALUES = DENSITY_VALUES
    STRAND_VALUES = STRAND_VALUES
    POROSITY_VALUES = POROSITY_VALUES
    COLOR_TECHNIQUES = COLOR_TECHNIQUES
    COLOR_VIBRANCY = COLOR_VIBRANCY
    COLOR_PLACEMENT = COLOR_PLACEMENT
    ARRANGEMENT_TYPES = ARRANGEMENT_TYPES
    ARRANGEMENT_POSITIONS = ARRANGEMENT_POSITIONS
    SHEEN_VALUES = SHEEN_VALUES
    CONDITION_VALUES = CONDITION_VALUES
    HAIR_STATES = HAIR_STATES
    CULTURAL_STYLE_TYPES = CULTURAL_STYLE_TYPES
    CULTURAL_SUBTYPES = CULTURAL_SUBTYPES
    CULTURAL_STAGES = CULTURAL_STAGES
    CULTURAL_TREATMENTS = CULTURAL_TREATMENTS
    HAIR_REGIONS = HAIR_REGIONS

    def normalize(self, raw: dict) -> dict:
        """Normalize hair data to ontology schema."""
        return normalize_hair(raw)

    def render(self, ontology: dict) -> str:
        """Render normalized hair ontology to text."""
        return render_hair(ontology)
        """Normalize hair data to ontology schema."""
        return normalize_hair(raw)

    def render(self, ontology: dict) -> str:
        """Render normalized hair ontology to text."""
        return render_hair(ontology)


# ---------------------------------------------------------------------------
# System: PoseSystem
# ---------------------------------------------------------------------------

class PoseSystem:
    """Generates a CandidateFragment for the scene pose (body configuration)."""

    def __init__(self, poses_db: dict, templates_db: dict):
        self.poses = poses_db
        self.templates = templates_db

    def process(self, pose_name: Optional[str]) -> Optional[CandidateFragment]:
        if not pose_name or pose_name not in self.poses:
            return None
        pose_def = self.poses[pose_name]
        pose_text = pose_def.get("pose_text", "")
        if not pose_text:
            return None
        return CandidateFragment(
            zone="pose",
            frag_type="pose",
            tags=["pose"],
            priority=70,
            text=pose_text,
        )


# ---------------------------------------------------------------------------
# System: BodyConfigSystem
# ---------------------------------------------------------------------------

# --- BodyConfig Schema Constants ---
HEAD_TILTS = {"forward", "back", "left", "right", "slightly_left", "slightly_right", "upright"}
HEAD_TURNS = {"toward_camera", "away_from_camera", "profile_left", "profile_right"}
GAZE_DIRECTIONS = {"up", "down", "left", "right", "away", "toward_camera", "toward_target"}
GAZE_ENGAGEMENTS = {"direct", "averted", "fleeting", "side_glance"}
ARM_POSITIONS = {"at_side", "crossed", "raised", "behind_back", "resting_on_object"}
HAND_STATES = {"relaxed", "clenched", "in_pockets", "gripping", "pointing"}
LEG_POSITIONS = {"standing", "bent", "crossed", "apart", "kneeling", "dangling"}
LEG_WEIGHTS = {"left", "right", "even"}
TORSO_LEANS = {"forward", "back", "left", "right", "upright"}
TORSO_ANGLES = {"slight", "pronounced"}

# --- Pose-to-BodyConfig Mapping (backward compat) ---
POSE_TO_BODYCONFIG = {
    "standing":    {"legs": {"position": "standing"}, "torso": {"lean": "upright"}},
    "sitting":     {"legs": {"position": "bent"}, "torso": {"lean": "upright"}},
    "leaning":     {"legs": {"position": "standing"}, "torso": {"lean": "forward"}},
    "kneeling":    {"legs": {"position": "kneeling"}, "torso": {"lean": "upright"}},
    "arms_crossed": {"arms": {"left": "crossed", "right": "crossed"}},
    "hands_behind_back": {"arms": {"left": "behind_back", "right": "behind_back"}},
    "reaching":    {"arms": {"left": "raised", "right": "raised"}},
    "lying_down":  {"legs": {"position": "standing"}, "torso": {"lean": "back"}},  # approx
}

# --- Relationship-to-BodyConfig Mapping (physical implications) ---
REL_TO_BODYCONFIG = {
    "sitting":       {"legs": {"position": "bent"}, "torso": {"lean": "upright"}},
    "sitting_on":    {"legs": {"position": "bent"}, "torso": {"lean": "upright"}},
    "leaning_on":    {"torso": {"lean": "forward"}},
    "rest_arms_on":  {"arms": {"left": "resting_on_object", "right": "resting_on_object"}},
    "dangling_feet": {"legs": {"position": "dangling"}},
    "kneeling":      {"legs": {"position": "kneeling"}, "torso": {"lean": "upright"}},
    "hugging":       {"arms": {"left": "at_side", "right": "at_side"}},
    "looking_at":    {"gaze": {"direction": "toward_target"}},
    "looking_over":  {"gaze": {"direction": "away"}},
    "looking_into":  {"gaze": {"direction": "toward_target"}},
    "looking_out_of": {"gaze": {"direction": "away"}},
}

# --- Head turn hides face sub-zones ---
HEAD_TURN_FACE_HIDDEN = {
    "profile_left": ["Eyes"],   # eyes not visible in profile
    "profile_right": ["Eyes"],
    "away_from_camera": [],     # face still visible, just turned
}

# --- Arms positions that hide Hands zone ---
ARMS_HANDS_HIDDEN = {"behind_back"}


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Override wins on conflicts."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def normalize_body_config(raw: dict, pose_fallback: Optional[str] = None) -> dict:
    """Normalize body config from raw input + pose fallback.

    Priority: raw body_config > pose fallback > defaults.
    """
    # Start with defaults
    config = {
        "head": {"tilt": "upright", "turn": ""},
        "gaze": {"direction": "", "target": "", "engagement": ""},
        "arms": {"left": "", "right": "", "hands": ""},
        "legs": {"position": "", "weight": ""},
        "torso": {"lean": "", "angle": ""},
    }

    # Apply pose fallback if provided
    if pose_fallback and pose_fallback in POSE_TO_BODYCONFIG:
        config = _deep_merge(config, POSE_TO_BODYCONFIG[pose_fallback])

    # Apply raw body_config (highest priority)
    if raw:
        for section in ("head", "gaze", "arms", "legs", "torso"):
            if section in raw and isinstance(raw[section], dict):
                config[section] = _deep_merge(config[section], raw[section])

    return config


def render_body_config_part(part_name: str, part_data: dict) -> str:
    """Render a body config sub-component to a natural language phrase."""
    if part_name == "head":
        return _render_head(part_data)
    elif part_name == "gaze":
        return _render_gaze(part_data)
    elif part_name == "arms":
        return _render_arms(part_data)
    elif part_name == "legs":
        return _render_legs(part_data)
    elif part_name == "torso":
        return _render_torso(part_data)
    return ""


def _render_head(head: dict) -> str:
    """Render head configuration."""
    parts = []
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
        parts.append(tilt_words.get(tilt, f"tilted {tilt}"))

    if turn and turn != "toward_camera":
        turn_words = {
            "away_from_camera": "turned away from the camera",
            "profile_left": "turned to the left",
            "profile_right": "turned to the right",
        }
        parts.append(turn_words.get(turn, f"turned {turn}"))

    return " ".join(parts) if parts else ""


def _render_gaze(gaze: dict) -> str:
    """Render gaze configuration."""
    parts = []
    direction = gaze.get("direction", "")
    target = gaze.get("target", "")
    engagement = gaze.get("engagement", "")

    if not direction:
        return ""

    if direction == "toward_target" and target:
        parts.append(f"looking at {target}")
    elif direction == "toward_camera":
        if engagement == "direct":
            parts.append("looking directly at the camera")
        elif engagement == "averted":
            parts.append("gaze averted from the camera")
        else:
            parts.append("looking toward the camera")
    elif direction:
        dir_words = {
            "up": "looking upward",
            "down": "looking downward",
            "left": "looking to the left",
            "right": "looking to the right",
            "away": "looking away",
        }
        parts.append(dir_words.get(direction, f"looking {direction}"))

    if engagement and engagement not in ("direct", "") and direction != "toward_target":
        eng_words = {
            "averted": "with averted gaze",
            "fleeting": "with a fleeting glance",
            "side_glance": "with a side glance",
        }
        eng_part = eng_words.get(engagement, f"with {engagement} gaze")
        parts.append(eng_part)

    return " ".join(parts) if parts else ""


def _render_arms(arms: dict) -> str:
    """Render arm configuration."""
    left = arms.get("left", "")
    right = arms.get("right", "")
    hands = arms.get("hands", "")

    # Both empty
    if not left and not right and not hands:
        return ""

    # Default to at_side if only one is set
    if not left:
        left = "at_side"
    if not right:
        right = "at_side"

    # Symmetric positions
    if left == right:
        pos_words = {
            "crossed": "arms crossed",
            "raised": "arms raised",
            "behind_back": "hands clasped behind their back",
            "resting_on_object": "resting arms on",
            "at_side": "",
        }
        phrase = pos_words.get(left, f"arms {left}")
        if hands == "in_pockets" and left == "at_side":
            phrase = "hands in pockets"
        return phrase

    # Asymmetric positions
    parts = []
    if left != "at_side":
        parts.append(f"left arm {left}" if left != "resting_on_object" else "left arm resting on")
    if right != "at_side":
        parts.append(f"right arm {right}" if right != "resting_on_object" else "right arm resting on")
    if hands == "in_pockets":
        parts.append("hands in pockets")
    return " and ".join(parts) if parts else ""


def _render_legs(legs: dict) -> str:
    """Render leg configuration."""
    position = legs.get("position", "")
    weight = legs.get("weight", "")

    if not position:
        return ""

    pos_words = {
        "standing": "",
        "bent": "legs bent",
        "crossed": "legs crossed",
        "apart": "legs apart",
        "kneeling": "kneeling",
        "dangling": "legs dangling",
    }
    phrase = pos_words.get(position, f"legs {position}")

    if weight and weight != "even" and position == "standing":
        phrase = f"weight on {weight} foot" if not phrase else f"{phrase}, weight on {weight} foot"

    return phrase


def _render_torso(torso: dict) -> str:
    """Render torso configuration."""
    lean = torso.get("lean", "")
    angle = torso.get("angle", "")

    if not lean or lean == "upright":
        return ""

    lean_words = {
        "forward": "leaning forward",
        "back": "leaning back",
        "left": "leaning to the left",
        "right": "leaning to the right",
    }
    phrase = lean_words.get(lean, f"leaning {lean}")

    if angle == "pronounced":
        phrase = phrase.replace("leaning", "leaning noticeably")

    return phrase


class BodyConfigSystem:
    """Normalizes body config and generates CandidateFragments for each sub-component."""

    HEAD_TILTS = HEAD_TILTS
    HEAD_TURNS = HEAD_TURNS
    GAZE_DIRECTIONS = GAZE_DIRECTIONS
    GAZE_ENGAGEMENTS = GAZE_ENGAGEMENTS
    ARM_POSITIONS = ARM_POSITIONS
    HAND_STATES = HAND_STATES
    LEG_POSITIONS = LEG_POSITIONS
    LEG_WEIGHTS = LEG_WEIGHTS
    TORSO_LEANS = TORSO_LEANS
    TORSO_ANGLES = TORSO_ANGLES
    POSE_TO_BODYCONFIG = POSE_TO_BODYCONFIG
    REL_TO_BODYCONFIG = REL_TO_BODYCONFIG

    def normalize(self, raw: dict, pose_fallback: Optional[str] = None) -> dict:
        """Normalize body config data."""
        return normalize_body_config(raw, pose_fallback)

    def apply_relationship_implications(self, config: dict, rel_type: str) -> dict:
        """Apply relationship physical implications to body config."""
        if rel_type in REL_TO_BODYCONFIG:
            return _deep_merge(config, REL_TO_BODYCONFIG[rel_type])
        return config

    def apply_fixture_affordance(
        self, config: dict, rel_type: str, target_obj, environments_db: dict, env_type: str
    ) -> dict:
        """If a looking_* relationship targets a fixture, infer gaze direction from its affordance."""
        if not target_obj or target_obj.type != "fixture":
            return config
        if not rel_type.startswith("looking_"):
            return config
        anchor = target_obj.get_component("anchor", "")
        if not anchor:
            return config
        env_def = environments_db.get(env_type, {})
        affordances = env_def.get("affordances", {})
        anchor_affordances = affordances.get(anchor, [])
        affordance_to_gaze = {
            "look_into": "toward_target",
            "look_out_of": "away",
            "look_over": "away",
            "look_at": "toward_target",
        }
        for aff in anchor_affordances:
            if aff in affordance_to_gaze:
                return _deep_merge(config, {"gaze": {"direction": affordance_to_gaze[aff]}})
        return config

    def render_fragments(self, config: dict, human_id: str, priority_fn) -> list:
        """Generate CandidateFragments for each body config sub-component."""
        fragments = []
        part_tags = {
            "head": ["body_config", "pose"],
            "gaze": ["body_config", "gaze"],
            "arms": ["body_config", "pose"],
            "legs": ["body_config", "pose"],
            "torso": ["body_config", "pose"],
        }
        part_priorities = {
            "head": 72,
            "gaze": 71,
            "arms": 70,
            "legs": 69,
            "torso": 68,
        }

        for part in ("head", "gaze", "arms", "legs", "torso"):
            part_data = config.get(part, {})
            text = render_body_config_part(part, part_data)
            if text:
                fragments.append(CandidateFragment(
                    zone=part,
                    frag_type="body_config",
                    tags=part_tags.get(part, ["body_config"]),
                    priority=priority_fn(part_priorities.get(part, 70), [human_id]),
                    text=text,
                    actor_id=human_id,
                ))

        return fragments

    def get_hidden_zones(self, config: dict) -> list:
        """Determine which body zones are hidden by body config."""
        hidden = []

        # Head turn hides eyes in profile
        turn = config.get("head", {}).get("turn", "")
        if turn in HEAD_TURN_FACE_HIDDEN:
            hidden.extend(HEAD_TURN_FACE_HIDDEN[turn])

        # Arms behind back hides hands
        left_arm = config.get("arms", {}).get("left", "")
        right_arm = config.get("arms", {}).get("right", "")
        if left_arm in ARMS_HANDS_HIDDEN or right_arm in ARMS_HANDS_HIDDEN:
            hidden.append("Hands")

        # Legs position hides feet
        leg_pos = config.get("legs", {}).get("position", "")
        if leg_pos in ("bent", "kneeling", "dangling"):
            hidden.append("Feet")

        return hidden


# ---------------------------------------------------------------------------
# System: RelationshipSystem
# ---------------------------------------------------------------------------

_UNCOUNTABLE = {"water", "sand", "music", "light", "darkness", "rain", "snow", "fog", "air", "love", "anger", "joy"}

def with_article(phrase: str) -> str:
    """Prepends 'a' or 'an' to a noun phrase if it doesn't already start with an article."""
    if not phrase:
        return phrase
    words = phrase.split()
    if words and words[0].lower() in ("a", "an", "the"):
        return phrase
    if phrase.lower() in _UNCOUNTABLE:
        return phrase
    first_char = phrase[0].lower()
    art = "an" if first_char in "aeiou" else "a"
    return f"{art} {phrase}"


class RelationshipSystem:
    """Validates, resolves, and renders action/interaction/spatial relationships."""

    def __init__(self, actions_db: dict, spatial_db: dict, templates_db: dict, environments_db: dict = None):
        self.actions = actions_db
        self.spatial = spatial_db
        self.templates = templates_db
        self.environments = environments_db or {}

    def resolve_anchor(self, dotref: str, env_type: str, scene_objects: dict) -> Optional[str]:
        """Resolve 'env.anchor' dot-notation to a SceneObject ID.

        Creates a fixture SceneObject for the anchor if it doesn't exist yet.
        Returns the object ID or None if resolution fails.
        """
        if "." not in dotref:
            return None
        env_id, anchor_name = dotref.split(".", 1)
        env_def = self.environments.get(env_type, {})
        affordances = env_def.get("affordances", {})
        if anchor_name not in affordances:
            return None
        anchor_obj_id = f"anchor_{env_type}_{anchor_name}"
        if anchor_obj_id not in scene_objects:
            scene_objects[anchor_obj_id] = SceneObject(
                anchor_obj_id, "fixture",
                {"template_key": "Fixture", "anchor": anchor_name, "env_type": env_type}
            )
        return anchor_obj_id

    def resolve_anchor_targets(
        self, relationships_data: list, scene_objects: dict, env_type: str
    ) -> list:
        """Resolve dot-notation targets/actors in relationships to SceneObject IDs."""
        resolved = []
        for rel in relationships_data:
            rel = dict(rel)
            for field in ("target", "actor", "subject", "container"):
                val = rel.get(field)
                if isinstance(val, str) and "." in val:
                    resolved_id = self.resolve_anchor(val, env_type, scene_objects)
                    if resolved_id:
                        rel[field] = resolved_id
                    else:
                        rel[field] = None
            resolved.append(rel)
        return resolved

    def get_noun_phrase(self, obj_id, scene_objects: dict, placements: dict, mentioned_ids: set, role: str = None) -> str:
        if isinstance(obj_id, list):
            phrases = [self.get_noun_phrase(oid, scene_objects, placements, mentioned_ids, role) for oid in obj_id]
            if len(phrases) == 1:
                return phrases[0]
            elif len(phrases) == 2:
                return f"{phrases[0]} and {phrases[1]}"
            else:
                return ", ".join(phrases[:-1]) + f", and {phrases[-1]}"

        obj = scene_objects.get(obj_id)
        if not obj:
            return str(obj_id)

        is_plural = False
        if obj.get_component("count", 1) > 1 or obj.get_component("plural", False):
            is_plural = True

        if obj_id in mentioned_ids:
            if obj.type == "human":
                gender = obj.get_component("gender", "person")
                if role in ("actor", "subject", "subject1"):
                    return "they" if is_plural else "she" if gender == "woman" else "he" if gender == "man" else "they"
                else:
                    return "them" if is_plural else "her" if gender == "woman" else "him" if gender == "man" else "them"
            else:
                return "them" if is_plural else "the " + obj.type
        else:
            mentioned_ids.add(obj_id)

        if obj.type == "human":
            phrase = obj.get_component("gender", "person")
        else:
            template = self.templates.get(obj.get_component("template_key"))
            ctx = {**obj.components}
            holding_item_id = obj.get_component("holding_item_id")
            if holding_item_id:
                ctx["held_item"] = self.get_noun_phrase(holding_item_id, scene_objects, placements, mentioned_ids, "object")
            if is_plural:
                ctx["_plural_self"] = True
            if template:
                phrase = safe_format(template, ctx)
            else:
                parts = [obj.get_component("material", ""), obj.get_component("color", ""), obj.type]
                phrase = " ".join(p for p in parts if p).strip()
            
            if phrase:
                if not is_plural:
                    phrase = with_article(phrase)
                else:
                    if not template:
                        phrase = phrase + "s"

        placement = placements.get(obj_id)
        if placement:
            phrase = f"{phrase} in {placement}"
        return phrase

    def process(
        self,
        relationships_data: list,
        scene_objects: dict,
        placements: dict,
        visible_zones: list,
        priority_fn,
        mentioned_ids: set,
        active_tone: str = "default",
    ) -> list:
        candidates = []

        for rel in relationships_data:
            rel_type = rel.get("type")
            rel_def = self.actions.get(rel_type)
            is_spatial = False
            if not rel_def:
                rel_def = self.spatial.get(rel_type)
                is_spatial = True
            if not rel_def:
                continue

            # Role type validation (handles lists of participants)
            valid = True
            related_ids = []
            for role_name, constraint in rel_def.get("roles", {}).items():
                target_val = rel.get(role_name)
                target_ids = target_val if isinstance(target_val, list) else [target_val] if target_val else []
                for tid in target_ids:
                    target_obj = scene_objects.get(tid)
                    if not target_obj or target_obj.type not in constraint.get("allowed", []):
                        valid = False
                        break
                    related_ids.append(tid)
                if not valid:
                    break
            if not valid:
                continue

            # Visibility check on required zones (handles lists)
            visible = True
            for role_name, req_zone in rel_def.get("required_zones", {}).items():
                pid = rel.get(role_name)
                pids = pid if isinstance(pid, list) else [pid] if pid else []
                for p in pids:
                    pobj = scene_objects.get(p)
                    if pobj and pobj.type == "human" and req_zone not in visible_zones:
                        visible = False
                        break
                if not visible:
                    break
            if not visible:
                continue

            # Variant resolution
            template = rel_def.get("template", "")
            clause_template = rel_def.get("clause", template)
            for variant in rel_def.get("variants", []):
                when = variant.get("when", {})
                match = all(
                    scene_objects.get(rel.get(k[:-5])) and
                    scene_objects[rel[k[:-5]]].type == v
                    for k, v in when.items() if k.endswith("_type")
                )
                if match:
                    template = variant.get("template", template)
                    clause_template = variant.get("clause", template)
                    break

            # Resolve role noun phrases
            role_phrases = {}
            for role in rel_def.get("roles", {}):
                val = rel.get(role)
                role_phrases[role] = self.get_noun_phrase(val, scene_objects, placements, mentioned_ids, role)
                # If plural, set the _plural_role helper in context for safe_format agreement
                is_role_plural = False
                if isinstance(val, list) and len(val) > 1:
                    is_role_plural = True
                elif isinstance(val, str):
                    tobj = scene_objects.get(val)
                    if tobj and (tobj.get_component("count", 1) > 1 or tobj.get_component("plural", False)):
                        is_role_plural = True
                if is_role_plural:
                    role_phrases[f"_plural_{role}"] = True

            actor_id = rel.get("actor") or rel.get("subject") or rel.get("subject1")
            # If actor_id is a list, take the first one for native fragment tracking
            if isinstance(actor_id, list) and actor_id:
                track_actor_id = actor_id[0]
            else:
                track_actor_id = actor_id or ""

            # Resolve actor possessive pronoun for gender-aware suffixes
            _possessive = "her"
            if track_actor_id:
                _actor_obj = scene_objects.get(track_actor_id)
                if _actor_obj:
                    _actor_gender = _actor_obj.get_component("gender", "person")
                    _possessive = "their" if _actor_gender == "person" else "his" if _actor_gender == "man" else "her"
            role_phrases["_possessive"] = _possessive

            candidates.append(CandidateFragment(
                zone="relationship",
                frag_type="relationship",
                tags=rel_def.get("tags", ["spatial" if is_spatial else "action"]),
                priority=priority_fn(rel_def.get("priority", 50), related_ids),
                text=safe_format(template, {**role_phrases, "_tone": active_tone}),
                clause_text=safe_format(clause_template, {**role_phrases, "_tone": active_tone}),
                actor_id=track_actor_id,
                chain_order=rel_def.get("chain_order", 99),
            ))

        return candidates


# ---------------------------------------------------------------------------
# System: EnvironmentSystem
# ---------------------------------------------------------------------------

class EnvironmentSystem:
    """Resolves environment, lighting, weather and composition into fragments."""

    def __init__(self, environments_db: dict, lighting_db: dict, weather_db: dict, composition_db: dict, templates_db: dict):
        self.environments = environments_db
        self.lighting = lighting_db
        self.weather = weather_db
        self.composition = composition_db
        self.templates = templates_db

    def process(
        self,
        env_obj: Optional[SceneObject],
        comp_obj: Optional[SceneObject],
        scene_objects: dict,
        owned_item_ids: set,
        relationship_targets: set,
    ) -> list:
        candidates = []

        if env_obj:
            env_type = env_obj.get_component("template_key") or env_obj.get_component("type")
            env_def = self.environments.get(env_type, {})
            if not env_def and env_obj.get_component("type") in self.environments:
                env_def = self.environments[env_obj.get_component("type")]

            lighting_val = env_obj.get_component("lighting", env_def.get("default_lighting", ""))
            lighting_str = self.lighting.get(lighting_val, {}).get("template", lighting_val)

            weather_val = env_obj.get_component("weather", env_def.get("default_weather", ""))
            weather_str = self.weather.get(weather_val, {}).get("template", weather_val)

            env_tpl = self.templates.get(env_obj.get_component("template_key")) or env_def.get("template", "{weather} {lighting} {type}")

            ctx = {
                **env_obj.components,
                "weather": weather_str,
                "lighting": lighting_str,
                "type": env_obj.get_component("type")
            }
            env_text = safe_format(env_tpl, ctx)

            # ECS query: find ambient fixtures and furniture
            ambient_fixtures = []
            for obj in scene_objects.values():
                if obj.type in ("fixture", "furniture") and obj.id not in owned_item_ids and obj.id not in relationship_targets:
                    tkey = obj.get_component("template_key")
                    template = self.templates.get(tkey)
                    if template:
                        phrase = safe_format(template, obj.components)
                    else:
                        parts = [obj.get_component("material", ""), obj.get_component("color", ""), obj.type]
                        phrase = " ".join(p for p in parts if p).strip()
                    if phrase:
                        ambient_fixtures.append(with_article(phrase))

            if ambient_fixtures:
                if len(ambient_fixtures) == 1:
                    fixtures_str = ambient_fixtures[0]
                elif len(ambient_fixtures) == 2:
                    fixtures_str = f"{ambient_fixtures[0]} and {ambient_fixtures[1]}"
                else:
                    fixtures_str = ", ".join(ambient_fixtures[:-1]) + f", and {ambient_fixtures[-1]}"
                env_text = f"{env_text} featuring {fixtures_str}"

            candidates.append(CandidateFragment(
                zone="environment", frag_type="environment",
                tags=["environment"], priority=65, text=env_text,
            ))
            if lighting_str:
                candidates.append(CandidateFragment(
                    zone="lighting", frag_type="lighting",
                    tags=["lighting"], priority=55, text=lighting_str,
                ))
            if weather_str:
                candidates.append(CandidateFragment(
                    zone="weather", frag_type="weather",
                    tags=["weather"], priority=50, text=weather_str,
                ))

        if comp_obj:
            comp_type = comp_obj.get_component("template_key") or comp_obj.get_component("type")
            comp_def = self.composition.get(comp_type, {})
            text = comp_def.get("template", comp_type)
            tpl = self.templates.get(comp_type)
            if tpl:
                text = safe_format(tpl, comp_obj.components)

            candidates.append(CandidateFragment(
                zone="composition", frag_type="composition",
                tags=["composition"], priority=88,
                text=text,
            ))

        return candidates


# ---------------------------------------------------------------------------
# System: ValidationSystem
# ---------------------------------------------------------------------------

class ValidationSystem:
    """Pre-flight validation of scene structure. Returns a list of ValidationErrors."""

    def __init__(self, actions_db: dict, spatial_db: dict, templates_db: dict):
        self.actions = actions_db
        self.spatial = spatial_db
        self.templates = templates_db

    def validate(self, scene: dict, scene_objects: dict) -> list:
        errors = []
        errors += self._check_missing_references(scene, scene_objects)
        errors += self._check_relationship_roles(scene, scene_objects)
        errors += self._check_unknown_templates(scene_objects)
        return errors

    def _check_missing_references(self, scene: dict, scene_objects: dict) -> list:
        errors = []
        # anchors
        for role, obj_id in scene.get("anchors", {}).items():
            if obj_id not in scene_objects:
                errors.append(ValidationError("error", f"Anchor '{role}' references unknown object '{obj_id}'"))
        # placements
        for obj_id in scene.get("placements", {}):
            if obj_id not in scene_objects:
                errors.append(ValidationError("warning", f"Placement references unknown object '{obj_id}'"))
        # relationship participants
        for rel in scene.get("relationships", []):
            rel_type = rel.get("type")
            rel_def = self.actions.get(rel_type) or self.spatial.get(rel_type)
            if not rel_def:
                errors.append(ValidationError("error", f"Unknown relationship type '{rel_type}'"))
                continue
            for role_name in rel_def.get("roles", {}):
                target_id = rel.get(role_name)
                if target_id and target_id not in scene_objects:
                    errors.append(ValidationError("error",
                        f"Relationship '{rel_type}' role '{role_name}' references unknown object '{target_id}'"))
        return errors

    def _check_relationship_roles(self, scene: dict, scene_objects: dict) -> list:
        errors = []
        for rel in scene.get("relationships", []):
            rel_type = rel.get("type")
            rel_def = self.actions.get(rel_type) or self.spatial.get(rel_type)
            if not rel_def:
                continue
            for role_name, constraint in rel_def.get("roles", {}).items():
                target_id = rel.get(role_name)
                target_obj = scene_objects.get(target_id)
                if not target_obj:
                    continue
                allowed = constraint.get("allowed", [])
                if allowed and target_obj.type not in allowed:
                    errors.append(ValidationError("warning",
                        f"Relationship '{rel_type}': role '{role_name}' expected types {allowed}, "
                        f"got '{target_obj.type}' (object '{target_id}') — will be skipped"))
        return errors

    def _check_unknown_templates(self, scene_objects: dict) -> list:
        errors = []
        for obj_id, obj in scene_objects.items():
            tkey = obj.get_component("template_key")
            if tkey and tkey not in self.templates:
                errors.append(ValidationError("warning",
                    f"Object '{obj_id}' references unknown template_key '{tkey}'"))
        return errors


# ---------------------------------------------------------------------------
# System: RenderSystem
# ---------------------------------------------------------------------------

class RenderSystem:
    """Filters, budgets, and composes fragments into the final prompt string.

    Supports two narrative modes (set per render profile):
      - "fact_chain"  (default): comma-separated clause list
      - "scene_description": grammatically unified sentence
    """

    def __init__(self, profiles_db: dict):
        self.profiles = profiles_db

    # Finite verb conversion for scene_description mode
    _PARTICIPLE_TO_FINITE = {
        "holding":           "holds",
        "sitting":           "sits",
        "hugging":           "hugs",
        "standing next to":  "stands next to",
        "sitting inside":    "sits inside",
        "soaking in":        "soaks in",
    }

    def _to_finite(self, clause: str) -> str:
        for participle, finite in self._PARTICIPLE_TO_FINITE.items():
            if clause.startswith(participle):
                return finite + clause[len(participle):]
        return clause

    def compose(
        self,
        candidates: list,
        profile_name: str,
        physical_entities: list,            # list of resolved SceneObject (supports multi-character)
    ) -> str:
        profile = self.profiles.get(profile_name, self.profiles.get("character_sheet", {}))
        include_tags = set(profile.get("include_tags", []))
        max_fragments = profile.get("max_fragments", 99)
        narrative_mode = profile.get("narrative_mode", "fact_chain")

        # Filter + sort + budget
        filtered = [c for c in candidates if any(t in include_tags for t in c.tags)]
        filtered.sort(key=lambda c: c.priority, reverse=True)
        budgeted = filtered[:max_fragments]

        # Partition
        natives: dict = {}          # (actor_id, zone) -> CandidateFragment
        clothing: list = []
        relationships: list = []
        env_frag: Optional[CandidateFragment] = None
        atmospheric: list = []
        composition_frags: list = []
        body_surface_frags: list = []
        pose_frag: Optional[CandidateFragment] = None
        body_config_frags: list = []

        for c in budgeted:
            if c.frag_type == "native":
                natives[(c.actor_id, c.zone)] = c
            elif c.frag_type == "owned_item":
                clothing.append(c)
            elif c.frag_type == "relationship":
                relationships.append(c)
            elif c.frag_type == "environment":
                env_frag = c
            elif c.frag_type == "composition":
                composition_frags.append(c)
            elif c.frag_type == "body_surface":
                body_surface_frags.append(c)
            elif c.frag_type == "pose":
                pose_frag = c
            elif c.frag_type == "body_config":
                body_config_frags.append(c)
            elif c.frag_type in ("lighting", "weather", "style"):
                atmospheric.append(c)

        # Build per-subject narrative
        # For multi-character scenes each human gets their own clause chain
        subject_phrases = []
        for human_obj in physical_entities:
            human_id = human_obj.id
            gender = human_obj.get_component("gender", "person")

            # Partition natives and clothing that belong to this human
            my_natives = {zone: c for (aid, zone), c in natives.items() if aid == human_id}
            my_clothing = [c for c in clothing if c.actor_id == human_id]

            face_frag = my_natives.get("Face")
            hair_frag = my_natives.get("Hair")
            eyes_frag = my_natives.get("Eyes")

            _has_multiword_expr = False
            if face_frag:
                face_clean = face_frag.text.replace(f" {gender}", "").strip()
                if " " in face_clean:
                    _has_multiword_expr = True
                    _first_word = face_clean.split()[0].lower()
                    if _first_word.endswith("ing"):
                        subject = f"{gender} with {face_clean}"
                    else:
                        _expr_article = with_article(face_clean)
                        subject = f"{gender} with {_expr_article}"
                else:
                    subject = f"{face_clean} {gender}"
            else:
                subject = gender

            with_parts = []
            if hair_frag:
                with_parts.append(hair_frag.text)
            if eyes_frag:
                with_parts.append(eyes_frag.text)

            if with_parts:
                if _has_multiword_expr:
                    with_parts_str = ", ".join(with_parts[:-1]) + f" and {with_parts[-1]}" if len(with_parts) > 1 else with_parts[0]
                    subject = f"{subject} and {with_parts_str}"
                elif len(with_parts) == 1:
                    subject = f"{subject} with {with_parts[0]}"
                else:
                    subject = f"{subject} with {with_parts[0]} and {with_parts[1]}"

            # Clothing aggregation ("wearing X, Y and Z")
            headwear_frag = my_natives.get("Headwear")
            if headwear_frag:
                my_clothing.append(headwear_frag)

            if my_clothing:
                items = [with_article(c.text) if len(my_clothing) == 1 else c.text for c in my_clothing]
                if len(items) == 1:
                    aggregated = items[0]
                elif len(items) == 2:
                    aggregated = f"{items[0]} and {items[1]}"
                else:
                    aggregated = ", ".join(items[:-1]) + f", and {items[-1]}"
                subject = f"{subject} wearing {aggregated}"

            # Body surface features (tattoos, scars, etc.) for this human
            my_bsf = [c for c in body_surface_frags if c.actor_id == human_id]
            if my_bsf:
                bsf_texts = [c.text for c in my_bsf]
                if len(bsf_texts) == 1:
                    subject = f"{subject} {bsf_texts[0]}"
                else:
                    subject = f"{subject} {' and '.join(bsf_texts)}"

            # Body config (per-human composable body configuration)
            my_body_config = [c for c in body_config_frags if c.actor_id == human_id]
            if my_body_config:
                # Render body config parts in priority order
                bc_texts = [c.text for c in sorted(my_body_config, key=lambda x: x.priority, reverse=True)]
                subject = f"{subject} {', '.join(bc_texts)}"
            elif pose_frag:
                # Fallback: use legacy scene-level pose if no body config
                # Skip if a relationship already implies body configuration
                # (relationship implications now always produce body_config fragments,
                #  so presence of any fragments means the relationship covered it)
                subject = f"{subject} {pose_frag.text}"

            # Relationships whose actor is this human
            my_rels = [r for r in relationships if r.actor_id == human_id or not r.actor_id]

            if narrative_mode == "scene_description":
                # Produce a grammatically unified sentence
                if my_rels:
                    my_rels.sort(key=lambda r: r.chain_order)
                    main_verb = self._to_finite(my_rels[0].clause_text)
                    extra_clauses = [r.clause_text for r in my_rels[1:]]
                    rel_part = main_verb
                    if extra_clauses:
                        rel_part += " " + " ".join(extra_clauses)
                else:
                    rel_part = ""

                article = "An" if subject[0].lower() in "aeiou" else "A"
                env_part = ""
                if env_frag and env_frag.text:
                    vowels = "aeiou"
                    env_art = "an" if env_frag.text[0].lower() in vowels else "a"
                    if any(k in env_frag.text for k in ("cafe", "office", "room", "restaurant", "tunnel")):
                        prep = "inside"
                    elif "beach" in env_frag.text or "court" in env_frag.text:
                        prep = "on"
                    elif "poolside" in env_frag.text:
                        prep = "at"
                    else:
                        prep = "in"
                    env_part = f"{prep} {env_art} {env_frag.text}"

                parts = [f"{article} {subject}"]
                if rel_part:
                    parts.append(rel_part)
                if env_part:
                    parts.append(env_part)
                subject_phrases.append(" ".join(parts) + ".")

            else:
                # fact_chain mode (original behaviour)
                parts = [subject]
                if my_rels:
                    my_rels.sort(key=lambda r: r.chain_order)
                    chain = " ".join(r.clause_text for r in my_rels)
                    parts.append(chain)
                if env_frag and env_frag.text:
                    if any(k in env_frag.text for k in ("cafe", "office", "room", "restaurant", "tunnel")):
                        prep = "inside"
                    elif "beach" in env_frag.text or "court" in env_frag.text:
                        prep = "on"
                    elif "poolside" in env_frag.text:
                        prep = "at"
                    else:
                        prep = "in"
                    vowels = "aeiou"
                    art = "an" if env_frag.text[0].lower() in vowels else "a"
                    parts.append(f"{prep} {art} {env_frag.text}")
                subject_phrases.append(", ".join(p for p in parts if p))

        # Integrated composition for scene_description
        if narrative_mode == "scene_description":
            if composition_frags and subject_phrases:
                comp_text = composition_frags[0].text
                if "cinematic" in comp_text:
                    suffix = ", shot in cinematic style"
                elif "over-the-shoulder" in comp_text:
                    suffix = ", shot in an over-the-shoulder style"
                else:
                    suffix = f", shot in {comp_text} style"
                
                # strip period from the last subject phrase
                if subject_phrases[-1].endswith("."):
                    subject_phrases[-1] = subject_phrases[-1][:-1] + suffix + "."
                else:
                    subject_phrases[-1] = subject_phrases[-1] + suffix + "."
        else:
            # In fact_chain mode, composition acts as normal atmospheric suffix
            for c in composition_frags:
                atmospheric.append(c)

        # Atmospheric suffixes (composition, standalone lighting, etc.)
        atm_parts = []
        for a in atmospheric:
            if env_frag and a.text in env_frag.text:
                continue
            atm_parts.append(a.text)

        all_parts = subject_phrases + atm_parts
        separator = " " if narrative_mode == "scene_description" else ", "
        return separator.join(p for p in all_parts if p)


class StyleSystem:
    """Resolves photographic style directives into fragments."""

    def __init__(self, styles_db: dict):
        self.styles = styles_db

    def process(self, scene: dict) -> list:
        candidates = []
        style_config = scene.get("style", {})
        style_type = style_config.get("type") if isinstance(style_config, dict) else style_config
        if style_type and style_type in self.styles:
            style_def = self.styles[style_type]
            candidates.append(CandidateFragment(
                zone="style", frag_type="style",
                tags=["style"], priority=90,
                text=style_def.get("template", style_type),
            ))
        return candidates


# ---------------------------------------------------------------------------
# PromptCompiler — thin orchestrator
# ---------------------------------------------------------------------------

class PromptCompiler:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir

        templates  = self._load("templates.json", {})
        subjects   = self._load("subjects.json", {})
        poses      = self._load("poses.json", {})
        metadata   = self._load("attribute_metadata.json", {})
        profiles   = self._load("render_profiles.json", {})
        actions    = self._load("actions.json", {})
        spatial    = self._load("spatial_relationships.json", {})
        envs       = self._load("environments.json", {})
        lighting   = self._load("lighting.json", {})
        weather    = self._load("weather.json", {})
        composition = self._load("composition.json", {})
        styles     = self._load("styles.json", {})
        attires    = self._load("attires.json", {})

        self.subject_system      = SubjectSystem(subjects)
        self.visibility_system   = VisibilitySystem(poses)
        self.wardrobe_system     = WardrobeSystem(attires)
        self.attribute_system    = AttributeCollectorSystem(metadata, templates)
        self.pose_system         = PoseSystem(poses, templates)
        self.body_config_system  = BodyConfigSystem()
        self.relationship_system = RelationshipSystem(actions, spatial, templates, envs)
        self.environment_system  = EnvironmentSystem(envs, lighting, weather, composition, templates)
        self.validation_system   = ValidationSystem(actions, spatial, templates)
        self.style_system        = StyleSystem(styles)
        self.render_system       = RenderSystem(profiles)

        # Expose safe_format as instance method for backwards-compat with tests
        self.safe_format = staticmethod(safe_format)

    def _load(self, filename: str, default):
        path = os.path.join(self.data_dir, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON in '{filename}': {e}") from e
        return default

    def _is_physical(self, obj: SceneObject) -> bool:
        """Check if object has physical form (subject, morphology, or human type)."""
        return bool(
            obj.get_component("subject") or 
            obj.get_component("morphology") or
            obj.type == "human"
        )

    def compile_scene(self, scene: dict, strict: bool = False) -> str:
        # Resolve active tone globally for safe_format
        render_profile = scene.get("render_profile", "character_sheet")
        profile = self.render_system.profiles.get(render_profile, {})
        PromptCompiler.active_tone = scene.get("tone") or profile.get("tone") or "default"

        # 1. Wrap raw dicts into SceneObjects
        scene_objects: dict = {
            obj_id: SceneObject(obj_id, obj_data.get("type"), obj_data)
            for obj_id, obj_data in scene.get("objects", {}).items()
        }

        # 2. Validation (pre-flight)
        errors = self.validation_system.validate(scene, scene_objects)
        hard_errors = [e for e in errors if e.severity == "error"]
        if strict and hard_errors:
            raise ValueError("\n".join(e.message for e in hard_errors))

        # 3. Resolve subjects and attires for all physical objects
        physical_entities = []
        for obj in list(scene_objects.values()):
            if self._is_physical(obj):
                self.subject_system.resolve(obj)
                self.wardrobe_system.resolve(obj, scene_objects)
                # Auto-create clothing SceneObjects for any owned_item_id refs
                for zone in ("UpperBody", "LowerBody", "Feet", "Hands", "Head", "Headwear"):
                    zone_data = obj.get_component(zone)
                    if zone_data and isinstance(zone_data, dict):
                        oid = zone_data.get("owned_item_id")
                        if oid and oid not in scene_objects:
                            base = oid
                            if "_" in base:
                                parts = base.split("_")
                                if parts[-1].isdigit():
                                    parts = parts[:-1]
                                base = "_".join(parts)
                            template_key = "".join(w.capitalize() for w in base.split("_"))
                            scene_objects[oid] = SceneObject(oid, "clothing", {
                                "type": "clothing", "template_key": template_key
                            })
                physical_entities.append(obj)

        if not physical_entities:
            return ""

        # 4. Visibility
        camera_framing = scene.get("camera", {}).get("framing", "full_body")
        pose_name = scene.get("pose")
        visible_zones = self.visibility_system.compute_visible_zones(
            camera_framing, pose_name, scene_objects=scene_objects
        )

        # 5. Priority helper (shared by attribute + relationship systems)
        anchors = scene.get("anchors", {})
        placements = scene.get("placements", {})

        def priority_fn(base: int, obj_ids: list) -> int:
            p = base
            for oid in obj_ids:
                if anchors.get("primary") == oid:   p += 15
                elif anchors.get("secondary") == oid: p += 5
                if placements.get(oid) == "background": p -= 10
            return p

        # 6. Collect candidates from each system
        # For multi-character we use the primary human for attribute collection
        # (each human's attributes are collected separately and tagged by actor_id)
        mentioned_ids = {h.id for h in physical_entities}
        active_tone = PromptCompiler.active_tone
        candidates = []

        # 6a. Pose (body configuration)
        pose_frag = self.pose_system.process(scene.get("pose"))
        if pose_frag:
            candidates.append(pose_frag)

        for human_obj in physical_entities:
            candidates += self.attribute_system.collect(human_obj, scene_objects, visible_zones, priority_fn, active_tone)

        # 6b. Resolve environment anchor targets (e.g. "balcony.railing" -> SceneObject)
        env_type = None
        if "environment" in scene:
            env_type = scene["environment"].get("type")
        # Also check scene_objects for environment type
        if not env_type:
            for obj in scene_objects.values():
                if obj.type == "environment":
                    env_type = obj.get_component("template_key") or obj.get_component("type")
                    break

        relationships = scene.get("relationships", [])
        if env_type:
            relationships = self.relationship_system.resolve_anchor_targets(
                relationships, scene_objects, env_type
            )

        candidates += self.relationship_system.process(
            relationships, scene_objects, placements, visible_zones, priority_fn, mentioned_ids, active_tone
        )

        # 6c. Body Config (per-human, composable body configuration)
        scene_body_config = scene.get("body_config", {})
        pose_name = scene.get("pose")
        body_config_frags = []
        has_explicit_body_config = bool(scene_body_config)

        for human_obj in physical_entities:
            # Get per-human body config: scene-level > subject preset > defaults
            human_body_config = scene_body_config.get(human_obj.id, scene_body_config) if has_explicit_body_config else {}
            # Subject preset body_config as fallback
            if not human_body_config:
                human_body_config = human_obj.get_component("body_config") or {}

            # Always normalize body config (explicit + pose fallback + defaults)
            config = self.body_config_system.normalize(human_body_config, pose_name)

            # Always apply relationship implications (kills the hardcoded verb list)
            for rel in relationships:
                if rel.get("actor") == human_obj.id or rel.get("subject") == human_obj.id:
                    rel_type = rel.get("type", "")
                    config = self.body_config_system.apply_relationship_implications(config, rel_type)
                    # Fixture affordance gaze override (look_out_of -> gaze away, etc.)
                    target_id = rel.get("target")
                    if target_id and env_type:
                        target_obj = scene_objects.get(target_id)
                        config = self.body_config_system.apply_fixture_affordance(
                            config, rel_type, target_obj, self.relationship_system.environments, env_type
                        )

            # Generate fragments if body config has any non-default values
            has_body_values = any(
                config.get(part, {}).get(k)
                for part in ("head", "gaze", "arms", "legs", "torso")
                for k in config.get(part, {})
            )
            if has_body_values:
                body_config_frags += self.body_config_system.render_fragments(config, human_obj.id, priority_fn)

            # Update visibility based on body config
            bc_hidden = self.body_config_system.get_hidden_zones(config)
            for hz in bc_hidden:
                if hz in visible_zones:
                    visible_zones.remove(hz)

            # Store config on human for RenderSystem access
            human_obj.components["_body_config"] = config

        candidates += body_config_frags

        # Identify occupied objects to exclude from ambient environment listing
        owned_item_ids = set()
        for human_obj in physical_entities:
            for zone in visible_zones:
                zone_data = human_obj.get_component(zone)
                if zone_data and zone_data.get("owned_item_id"):
                    owned_item_ids.add(zone_data["owned_item_id"])

        relationship_targets = set()
        for rel in relationships:
            for role_name, val in rel.items():
                if role_name not in ("type", "actor", "subject", "subject1"):
                    if val is not None:
                        relationship_targets.add(val)

        # Resolve environment and composition objects
        env_obj = None
        for obj in scene_objects.values():
            if obj.type == "environment":
                env_obj = obj
                break
        if not env_obj and "environment" in scene:
            env_data = dict(scene["environment"])
            env_data["template_key"] = env_data.get("type")
            env_obj = SceneObject("env_legacy", "environment", env_data)
            env_obj.components["type"] = env_data["template_key"]
            scene_objects["env_legacy"] = env_obj

        comp_obj = None
        for obj in scene_objects.values():
            if obj.type == "composition":
                comp_obj = obj
                break
        if not comp_obj and "composition" in scene:
            comp_data = dict(scene["composition"])
            comp_data["template_key"] = comp_data.get("type")
            comp_obj = SceneObject("comp_legacy", "composition", comp_data)
            comp_obj.components["type"] = comp_data["template_key"]
            scene_objects["comp_legacy"] = comp_obj

        candidates += self.environment_system.process(
            env_obj, comp_obj, scene_objects, owned_item_ids, relationship_targets
        )
        candidates += self.style_system.process(scene)

        # 7. Render
        profile_name = scene.get("render_profile", "character_sheet")
        return self.render_system.compose(candidates, profile_name, physical_entities)
