import os
import json
import re

class SceneObject:
    """
    A generic entity container holding components instead of subclassing.
    Components can represent body zones, item templates, parameters, etc.
    """
    def __init__(self, obj_id, obj_type, data):
        self.id = obj_id
        self.type = obj_type
        self.components = {}
        for k, v in data.items():
            if k not in ["type", "id"]:
                self.components[k] = v

    def get_component(self, name, default=None):
        return self.components.get(name, default)


class VisibilitySystem:
    """
    VisibilitySystem computes visible zones based on camera framing and pose occlusions.
    """
    def __init__(self, camera_zones, poses):
        self.camera_zones = camera_zones
        self.poses = poses

    def compute_visible_zones(self, camera_framing, pose_name):
        visible_zones = list(self.camera_zones.get(camera_framing, self.camera_zones.get("full_body", [])))
        if pose_name and pose_name in self.poses:
            hidden_zones = self.poses[pose_name].get("hidden_zones", [])
            for hz in hidden_zones:
                if hz in visible_zones:
                    visible_zones.remove(hz)
        return visible_zones


class RelationshipSystem:
    """
    RelationshipSystem validates allowed roles, resolves targets, evaluates template variants,
    verifies visibility requirements, and produces render-ready relationship fragments.
    """
    def __init__(self, actions_db, spatial_db, templates_db):
        self.actions = actions_db
        self.spatial = spatial_db
        self.templates = templates_db

    def get_noun_phrase(self, obj_id, scene_objects, placements, templates):
        obj = scene_objects.get(obj_id)
        if not obj:
            return obj_id

        phrase = ""
        if obj.type == "human":
            # Baseline descriptor
            phrase = obj.get_component("gender", "person")
        else:
            template_key = obj.get_component("template_key")
            template = templates.get(template_key)
            if template:
                # Safe format helper inlined/passed
                phrase = self.safe_format(template, obj.components)
            else:
                color = obj.get_component("color", "")
                material = obj.get_component("material", "")
                phrase = f"{material} {color} {obj.type}".replace("  ", " ").strip()

        placement = placements.get(obj_id)
        if placement:
            phrase = f"{phrase} in {placement}"

        return phrase

    def safe_format(self, template_str, context):
        placeholders = re.findall(r"\{([a-zA-Z0-9_]+)\}", template_str)
        kwargs = {}
        for p in placeholders:
            val = context.get(p, "")
            kwargs[p] = str(val) if val is not None else ""
        rendered = template_str.format(**kwargs)
        return re.sub(r'\s+', ' ', rendered).strip()

    def process_relationships(self, relationships_data, scene_objects, placements, visible_zones, anchors_map):
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

            # Validate role constraints
            valid_roles = True
            related_ids = []
            for role_name, constraint in rel_def.get("roles", {}).items():
                target_id = rel.get(role_name)
                target_obj = scene_objects.get(target_id)
                if not target_obj:
                    valid_roles = False
                    break
                related_ids.append(target_id)
                allowed_types = constraint.get("allowed", [])
                if target_obj.type not in allowed_types:
                    valid_roles = False
                    break

            if not valid_roles:
                continue

            # Check visibility requirements
            visible = True
            for role_name, req_zone in rel_def.get("required_zones", {}).items():
                participant_id = rel.get(role_name)
                participant_obj = scene_objects.get(participant_id)
                if participant_obj and participant_obj.type == "human":
                    if req_zone not in visible_zones:
                        visible = False
                        break

            if not visible:
                continue

            # Determine variant templates
            template = rel_def.get("template", "")
            for variant in rel_def.get("variants", []):
                when = variant.get("when", {})
                match = True
                for when_key, when_val in when.items():
                    if when_key.endswith("_type"):
                        role_name = when_key[:-5]
                        target_id = rel.get(role_name)
                        target_obj = scene_objects.get(target_id)
                        if not target_obj or target_obj.type != when_val:
                            match = False
                            break
                if match:
                    template = variant.get("template", template)
                    break

            # Resolve phrases
            role_phrases = {}
            for role_name in rel_def.get("roles", {}).keys():
                target_id = rel.get(role_name)
                role_phrases[role_name] = self.get_noun_phrase(target_id, scene_objects, placements, self.templates)

            rendered_relationship = template.format(**role_phrases)

            # Compute priority with anchor offsets
            base_priority = rel_def.get("priority", 50)
            priority = base_priority
            for r_id in related_ids:
                if anchors_map.get("primary") == r_id:
                    priority += 15
                elif anchors_map.get("secondary") == r_id:
                    priority += 5
                if placements.get(r_id) == "background":
                    priority -= 10

            candidates.append({
                "zone": "relationship",
                "type": "relationship",
                "tags": rel_def.get("tags", ["spatial" if is_spatial else "action"]),
                "priority": priority,
                "text": rendered_relationship
            })

        return candidates


class RenderSystem:
    """
    RenderSystem manages filtering by tag, sorting by priority, budgeting,
    and combining sections into the final natural language representation.
    """
    def __init__(self, profiles_db, templates_db):
        self.profiles = profiles_db
        self.templates = templates_db

    def compose_prompt(self, candidates, profile_name, human_obj):
        profile = self.profiles.get(profile_name, self.profiles.get("character_sheet", {}))
        include_tags = set(profile.get("include_tags", []))
        max_fragments = profile.get("max_fragments", 99)

        # Filter and sort
        filtered = [c for c in candidates if any(t in include_tags for t in c["tags"])]
        filtered.sort(key=lambda x: x["priority"], reverse=True)
        budgeted = filtered[:max_fragments]

        # Extract segments
        rendered_parts = {}
        other_texts = []
        for c in budgeted:
            if c["type"] in ["relationship", "environment", "lighting", "weather", "composition"]:
                other_texts.append(c["text"])
            else:
                rendered_parts[c["zone"]] = c["text"]

        prompt_segments = []
        face_str = rendered_parts.get("Face")
        hair_str = rendered_parts.get("Hair")
        
        if face_str and hair_str:
            base_prompt = f"{face_str} with {hair_str}"
        elif face_str:
            base_prompt = face_str
        elif hair_str:
            gender = human_obj.get_component("gender", "person") if human_obj else "person"
            base_prompt = f"{gender} with {hair_str}"
        else:
            base_prompt = human_obj.get_component("gender", "person") if human_obj else ""

        if base_prompt:
            prompt_segments.append(base_prompt)

        for ot in other_texts:
            prompt_segments.append(ot)

        order = ["UpperBody", "LowerBody", "Feet"]
        for zone in order:
            if zone in rendered_parts:
                prompt_segments.append(rendered_parts[zone])

        return ", ".join([ps for ps in prompt_segments if ps])


class PromptCompiler:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.templates = self.load_json("templates.json", {})
        self.personas = self.load_json("personas.json", {})
        self.poses = self.load_json("poses.json", {})
        self.metadata = self.load_json("attribute_metadata.json", {})
        self.profiles = self.load_json("render_profiles.json", {})
        self.actions = self.load_json("actions.json", {})
        
        self.spatial = self.load_json("spatial_relationships.json", {})
        self.environments = self.load_json("environments.json", {})
        self.lighting = self.load_json("lighting.json", {})
        self.weather = self.load_json("weather.json", {})
        self.composition = self.load_json("composition.json", {})
        
        camera_zones = {
            "close_up": ["Face", "Hair"],
            "medium": ["Face", "Hair", "UpperBody", "Hands"],
            "full_body": ["Face", "Hair", "UpperBody", "Hands", "LowerBody", "Feet"]
        }

        # Initialize Systems
        self.visibility_system = VisibilitySystem(camera_zones, self.poses)
        self.relationship_system = RelationshipSystem(self.actions, self.spatial, self.templates)
        self.render_system = RenderSystem(self.profiles, self.templates)

    def load_json(self, filename, default):
        filepath = os.path.join(self.data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return default

    def safe_format(self, template_str, context):
        placeholders = re.findall(r"\{([a-zA-Z0-9_]+)\}", template_str)
        kwargs = {}
        for p in placeholders:
            val = context.get(p, "")
            kwargs[p] = str(val) if val is not None else ""
        rendered = template_str.format(**kwargs)
        return re.sub(r'\s+', ' ', rendered).strip()

    def compile_scene(self, scene):
        # Wrap objects inside the generic SceneObject model
        scene_objects = {}
        human_id = None
        human_obj = None

        for obj_id, obj_data in scene.get("objects", {}).items():
            wrapped = SceneObject(obj_id, obj_data.get("type"), obj_data)
            scene_objects[obj_id] = wrapped
            if wrapped.type == "human":
                human_id = obj_id
                human_obj = wrapped

        # Resolve Persona defaults and merge components
        if human_obj:
            persona_name = human_obj.get_component("persona")
            if persona_name and persona_name in self.personas:
                persona_data = self.personas[persona_name]
                for comp_key, comp_val in persona_data.items():
                    if comp_key not in ["type", "gender"]:
                        # Merge dict components or set defaults
                        existing = human_obj.get_component(comp_key)
                        if isinstance(existing, dict) and isinstance(comp_val, dict):
                            merged = dict(comp_val)
                            merged.update(existing)
                            human_obj.components[comp_key] = merged
                        elif existing is None:
                            human_obj.components[comp_key] = comp_val
                # Set gender if absent
                if "gender" not in human_obj.components and "gender" in persona_data:
                    human_obj.components["gender"] = persona_data["gender"]

        # 1. Run VisibilitySystem
        camera_framing = scene.get("camera", {}).get("framing", "full_body")
        pose_name = scene.get("pose")
        visible_zones = self.visibility_system.compute_visible_zones(camera_framing, pose_name)

        anchors_map = scene.get("anchors", {})
        placements = scene.get("placements", {})

        def get_priority(base_priority, related_obj_ids):
            pri = base_priority
            for r_id in related_obj_ids:
                if anchors_map.get("primary") == r_id:
                    pri += 15
                elif anchors_map.get("secondary") == r_id:
                    pri += 5
                if placements.get(r_id) == "background":
                    pri -= 10
            return pri

        # 2. Collect Candidate Fragments
        candidates = []

        if human_obj:
            for zone in visible_zones:
                zone_data = human_obj.get_component(zone)
                if not zone_data:
                    continue

                owned_item_id = zone_data.get("owned_item_id")
                if owned_item_id:
                    owned_item = scene_objects.get(owned_item_id)
                    if owned_item:
                        meta = self.metadata.get(owned_item.type, {"tags": [], "priority": 50})
                        template_key = owned_item.get_component("template_key")
                        template = self.templates.get(template_key)
                        if template:
                            candidates.append({
                                "zone": zone,
                                "type": "owned_item",
                                "tags": meta.get("tags", []),
                                "priority": get_priority(meta.get("priority", 50), [human_id, owned_item_id]),
                                "text": self.safe_format(template, owned_item.components)
                            })
                else:
                    meta_key = "expression" if zone == "Face" else "hair" if zone == "Hair" else zone.lower()
                    meta = self.metadata.get(meta_key, {"tags": [], "priority": 50})
                    template = self.templates.get(zone)
                    if template:
                        ctx = {**zone_data, "gender": human_obj.get_component("gender", "person")}
                        text = self.safe_format(template, ctx)
                        if text:
                            candidates.append({
                                "zone": zone,
                                "type": "native",
                                "tags": meta.get("tags", []),
                                "priority": get_priority(meta.get("priority", 50), [human_id]),
                                "text": text
                            })

        # 3. Run RelationshipSystem
        rel_candidates = self.relationship_system.process_relationships(
            scene.get("relationships", []),
            scene_objects,
            placements,
            visible_zones,
            anchors_map
        )
        candidates.extend(rel_candidates)

        # 4. Environment, Lighting, Weather, and Composition
        env_config = scene.get("environment", {})
        env_type = env_config.get("type")
        if env_type and env_type in self.environments:
            env_def = self.environments[env_type]
            
            lighting_val = env_config.get("lighting", env_def.get("default_lighting"))
            lighting_str = self.lighting[lighting_val].get("template", lighting_val) if lighting_val in self.lighting else lighting_val
                
            weather_val = env_config.get("weather", env_def.get("default_weather"))
            weather_str = self.weather[weather_val].get("template", weather_val) if weather_val in self.weather else weather_val
                
            env_template = env_def.get("template", "{weather} {lighting} {type}")
            env_text = env_template.format(weather=weather_str, lighting=lighting_str, type=env_type)
            env_text = re.sub(r'\s+', ' ', env_text).strip()
            
            candidates.append({
                "zone": "environment",
                "type": "environment",
                "tags": ["environment"],
                "priority": 65,
                "text": env_text
            })
            
            if lighting_str:
                candidates.append({
                    "zone": "lighting",
                    "type": "lighting",
                    "tags": ["lighting"],
                    "priority": 55,
                    "text": lighting_str
                })
                
            if weather_str:
                candidates.append({
                    "zone": "weather",
                    "type": "weather",
                    "tags": ["weather"],
                    "priority": 50,
                    "text": weather_str
                })

        comp_config = scene.get("composition", {})
        comp_type = comp_config.get("type")
        if comp_type and comp_type in self.composition:
            comp_text = self.composition[comp_type].get("template", comp_type)
            candidates.append({
                "zone": "composition",
                "type": "composition",
                "tags": ["composition"],
                "priority": 88,
                "text": comp_text
            })

        # 5. Run RenderSystem
        profile_name = scene.get("render_profile", "character_sheet")
        return self.render_system.compose_prompt(candidates, profile_name, human_obj)
