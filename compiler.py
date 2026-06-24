import os
import json
import re

class SceneObject:
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
            phrase = obj.get_component("gender", "person")
        else:
            template_key = obj.get_component("template_key")
            template = templates.get(template_key)
            if template:
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

            # Determine variant templates / clauses
            template = rel_def.get("template", "")
            clause_template = rel_def.get("clause", template)
            
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
                    clause_template = variant.get("clause", template)
                    break

            # Resolve phrases
            role_phrases = {}
            for role_name in rel_def.get("roles", {}).keys():
                target_id = rel.get(role_name)
                role_phrases[role_name] = self.get_noun_phrase(target_id, scene_objects, placements, self.templates)

            rendered_relationship = template.format(**role_phrases)
            rendered_clause = clause_template.format(**role_phrases)

            # Compute priority
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
                "text": rendered_relationship,
                "clause_text": rendered_clause,
                "actor_id": rel.get("actor") or rel.get("subject") or rel.get("subject1")
            })

        return candidates


class RenderSystem:
    def __init__(self, profiles_db, templates_db):
        self.profiles = profiles_db
        self.templates = templates_db

    def compose_prompt(self, candidates, profile_name, human_obj, scene_objects, placements):
        profile = self.profiles.get(profile_name, self.profiles.get("character_sheet", {}))
        include_tags = set(profile.get("include_tags", []))
        max_fragments = profile.get("max_fragments", 99)

        # Filter and sort candidates
        filtered = [c for c in candidates if any(t in include_tags for t in c["tags"])]
        filtered.sort(key=lambda x: x["priority"], reverse=True)
        budgeted = filtered[:max_fragments]

        # Partition components into native body parts, clothing items, relationships, and atmospheres
        face_text = ""
        hair_text = ""
        clothing_texts = []
        relationship_clauses = []
        atmospheric_texts = []
        env_text = ""

        # Identify items attached to the subject
        for c in budgeted:
            if c["type"] == "native":
                if c["zone"] == "Face":
                    # Extract expression, e.g. "smiling"
                    face_text = c["text"]
                elif c["zone"] == "Hair":
                    hair_text = c["text"]
            elif c["type"] == "owned_item":
                clothing_texts.append(c["text"])
            elif c["type"] == "relationship":
                relationship_clauses.append(c["clause_text"])
            elif c["type"] == "environment":
                env_text = c["text"]
            elif c["type"] in ["lighting", "weather", "composition"]:
                atmospheric_texts.append(c["text"])

        # 1. Subject description attachment
        gender = human_obj.get_component("gender", "person") if human_obj else "person"
        
        # Format Face + Subject Identity
        if face_text:
            # Drop the trailing gender if template already has it to avoid duplicates
            face_clean = face_text.replace(f" {gender}", "").strip()
            subject_phrase = f"{face_clean} {gender}"
        else:
            subject_phrase = gender

        # Format Hair Attachment
        if hair_text:
            subject_phrase = f"{subject_phrase} with {hair_text}"

        # Format Clothing Aggregation
        if clothing_texts:
            # Aggregation: "wearing oversized black cotton hoodie, baggy olive cargo pants"
            aggregated_clothing = ", ".join(clothing_texts)
            # Add "a" or "an" where applicable or join naturally
            subject_phrase = f"{subject_phrase} wearing {aggregated_clothing}"

        # 2. Relationship Chaining (Actions + Spatial layout)
        narrative_segments = [subject_phrase]
        
        # Chain action clauses with "while" or "and"
        if relationship_clauses:
            if len(relationship_clauses) > 1:
                action_chain = " while ".join(relationship_clauses)
            else:
                action_chain = relationship_clauses[0]
            narrative_segments.append(action_chain)

        # 3. Environment Integration
        if env_text:
            # Format: "in a rain-soaked neon-lit alley" or "inside a warm soft-lit cafe"
            prep = "inside" if "inside" in env_text or "cafe" in env_text or "office" in env_text else "in"
            # simple helper to add article
            vowels = "aeiou"
            article = "an" if env_text[0].lower() in vowels else "a"
            narrative_segments.append(f"{prep} {article} {env_text}")

        # Combine main narrative chain
        # E.g. "smiling woman with long wavy brown hair wearing oversized black cotton hoodie, standing next to red car in background while holding a cup of white coffee cup, in a rain-soaked neon-lit alley"
        final_narrative = ", ".join([ns for ns in narrative_segments if ns])

        # Append overall atmosphere (lighting, composition, weather standalone modifiers)
        all_segments = [final_narrative]
        for atm in atmospheric_texts:
            # Skip if lighting or weather is already fused into environment
            if env_text and atm in env_text:
                continue
            all_segments.append(atm)

        return ", ".join([s for s in all_segments if s])


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
        return self.render_system.compose_prompt(candidates, profile_name, human_obj, scene_objects, placements)
