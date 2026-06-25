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
    frag_type: str          # "native" | "owned_item" | "relationship" | "environment" | "lighting" | "weather" | "composition"
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

            if not existing_slot.get("owned_item_id"):
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
# System: PersonaSystem
# ---------------------------------------------------------------------------

class PersonaSystem:
    """Merges persona defaults into a human SceneObject."""

    def __init__(self, personas_db: dict):
        self.personas = personas_db

    def resolve(self, human_obj: SceneObject) -> SceneObject:
        persona_name = human_obj.get_component("persona")
        if not persona_name or persona_name not in self.personas:
            return human_obj

        persona_data = self.personas[persona_name]
        for comp_key, comp_val in persona_data.items():
            if comp_key in ("type",):
                continue
            existing = human_obj.get_component(comp_key)
            if isinstance(existing, dict) and isinstance(comp_val, dict):
                merged = dict(comp_val)       # persona defaults first
                merged.update(existing)       # scene overrides win
                human_obj.components[comp_key] = merged
            elif existing is None:
                human_obj.components[comp_key] = comp_val

        if "gender" not in human_obj.components and "gender" in persona_data:
            human_obj.components["gender"] = persona_data["gender"]

        return human_obj


# ---------------------------------------------------------------------------
# System: VisibilitySystem
# ---------------------------------------------------------------------------

class VisibilitySystem:
    """Resolves active body zones from camera framing + pose occlusion."""

    CAMERA_ZONES = {
        "close_up":  ["Face", "Hair", "Eyes", "Headwear"],
        "medium":    ["Face", "Hair", "Eyes", "Headwear", "UpperBody", "Hands"],
        "full_body": ["Face", "Hair", "Eyes", "Headwear", "UpperBody", "Hands", "LowerBody", "Feet"],
    }

    def __init__(self, poses_db: dict):
        self.poses = poses_db

    def compute_visible_zones(self, camera_framing: str, pose_name: Optional[str]) -> list:
        zones = list(self.CAMERA_ZONES.get(camera_framing, self.CAMERA_ZONES["full_body"]))
        if pose_name and pose_name in self.poses:
            for hz in self.poses[pose_name].get("hidden_zones", []):
                if hz in zones:
                    zones.remove(hz)
        return zones


# ---------------------------------------------------------------------------
# System: AttributeCollectorSystem
# ---------------------------------------------------------------------------

class AttributeCollectorSystem:
    """Walks visible zones of a human object and emits CandidateFragments."""

    def __init__(self, metadata_db: dict, templates_db: dict):
        self.metadata = metadata_db
        self.templates = templates_db

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

            owned_item_id = zone_data.get("owned_item_id")
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
                        actor_id=human_id,          # ← owner tag
                    ))
            else:
                meta_key = "expression" if zone == "Face" else "hair" if zone == "Hair" else zone.lower()
                meta = self.metadata.get(meta_key, {"tags": [], "priority": 50})
                template = self.templates.get(zone)
                if template:
                    ctx = {**zone_data, "gender": gender, "_tone": active_tone}
                    text = safe_format(template, ctx)
                    if text:
                        candidates.append(CandidateFragment(
                            zone=zone,
                            frag_type="native",
                            tags=meta.get("tags", []),
                            priority=priority_fn(meta.get("priority", 50), [human_id]),
                            text=text,
                            actor_id=human_id,      # ← owner tag
                        ))

        return candidates


# ---------------------------------------------------------------------------
# System: RelationshipSystem
# ---------------------------------------------------------------------------

def with_article(phrase: str) -> str:
    """Prepends 'a' or 'an' to a noun phrase if it doesn't already start with an article."""
    if not phrase:
        return phrase
    words = phrase.split()
    if words and words[0].lower() in ("a", "an", "the"):
        return phrase
    first_char = phrase[0].lower()
    art = "an" if first_char in "aeiou" else "a"
    return f"{art} {phrase}"


class RelationshipSystem:
    """Validates, resolves, and renders action/interaction/spatial relationships."""

    def __init__(self, actions_db: dict, spatial_db: dict, templates_db: dict):
        self.actions = actions_db
        self.spatial = spatial_db
        self.templates = templates_db

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
        humans: list,            # list of resolved SceneObject (supports multi-character)
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
            elif c.frag_type in ("lighting", "weather", "style"):
                atmospheric.append(c)

        # Build per-subject narrative
        # For multi-character scenes each human gets their own clause chain
        subject_phrases = []
        for human_obj in humans:
            human_id = human_obj.id
            gender = human_obj.get_component("gender", "person")

            # Partition natives and clothing that belong to this human
            my_natives = {zone: c for (aid, zone), c in natives.items() if aid == human_id}
            my_clothing = [c for c in clothing if c.actor_id == human_id]

            face_frag = my_natives.get("Face")
            hair_frag = my_natives.get("Hair")
            eyes_frag = my_natives.get("Eyes")

            if face_frag:
                face_clean = face_frag.text.replace(f" {gender}", "").strip()
                subject = f"{face_clean} {gender}"
            else:
                subject = gender

            with_parts = []
            if hair_frag:
                with_parts.append(hair_frag.text)
            if eyes_frag:
                with_parts.append(eyes_frag.text)

            if with_parts:
                if len(with_parts) == 1:
                    subject = f"{subject} with {with_parts[0]}"
                else:
                    subject = f"{subject} with {with_parts[0]} and {with_parts[1]}"

            # Clothing aggregation ("wearing X, Y and Z")
            headwear_frag = my_natives.get("Headwear")
            if headwear_frag:
                my_clothing.append(headwear_frag)

            if my_clothing:
                items = [c.text for c in my_clothing]
                if len(items) == 1:
                    aggregated = items[0]
                elif len(items) == 2:
                    aggregated = f"{items[0]} and {items[1]}"
                else:
                    aggregated = ", ".join(items[:-1]) + f", and {items[-1]}"
                subject = f"{subject} wearing {aggregated}"

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
        personas   = self._load("personas.json", {})
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

        self.persona_system      = PersonaSystem(personas)
        self.visibility_system   = VisibilitySystem(poses)
        self.wardrobe_system     = WardrobeSystem(attires)
        self.attribute_system    = AttributeCollectorSystem(metadata, templates)
        self.relationship_system = RelationshipSystem(actions, spatial, templates)
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

        # 3. Resolve personas and attires for all human objects
        humans = []
        for obj in list(scene_objects.values()):
            if obj.type == "human":
                self.persona_system.resolve(obj)
                self.wardrobe_system.resolve(obj, scene_objects)
                humans.append(obj)

        if not humans:
            return ""

        # 4. Visibility
        camera_framing = scene.get("camera", {}).get("framing", "full_body")
        pose_name = scene.get("pose")
        visible_zones = self.visibility_system.compute_visible_zones(camera_framing, pose_name)

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
        mentioned_ids = {h.id for h in humans}
        active_tone = PromptCompiler.active_tone
        candidates = []
        for human_obj in humans:
            candidates += self.attribute_system.collect(human_obj, scene_objects, visible_zones, priority_fn, active_tone)

        candidates += self.relationship_system.process(
            scene.get("relationships", []), scene_objects, placements, visible_zones, priority_fn, mentioned_ids, active_tone
        )

        # Identify occupied objects to exclude from ambient environment listing
        owned_item_ids = set()
        for human_obj in humans:
            for zone in visible_zones:
                zone_data = human_obj.get_component(zone)
                if zone_data and zone_data.get("owned_item_id"):
                    owned_item_ids.add(zone_data["owned_item_id"])

        relationship_targets = set()
        for rel in scene.get("relationships", []):
            for role_name, val in rel.items():
                if role_name not in ("type", "actor", "subject", "subject1"):
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
        return self.render_system.compose(candidates, profile_name, humans)
